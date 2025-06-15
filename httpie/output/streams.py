from itertools import chain
from functools import partial

from httpie.compat import str
from httpie.context import Environment
from httpie.models import HTTPRequest, HTTPResponse
from httpie.input import (OUT_REQ_BODY, OUT_REQ_HEAD,
                          OUT_RESP_HEAD, OUT_RESP_BODY)
from httpie.output.processing import Formatting, Conversion


BINARY_SUPPRESSED_NOTICE = (
    b'\n'
    b'+-----------------------------------------+\n'
    b'| NOTE: binary data not shown in terminal |\n'
    b'+-----------------------------------------+'
)


class BinarySuppressedError(Exception):
    """An error indicating that the body is binary and won't be written,
     e.g., for terminal output)."""

    message = BINARY_SUPPRESSED_NOTICE


def write(stream, outfile, flush):
    """
    Writes byte chunks from the stream to the specified output file.
    
    If the output file supports a buffer interface, writes directly to the buffer; otherwise, writes to the file object itself. Flushes the output after each chunk if requested.
    """
    try:
        # Writing bytes so we use the buffer interface (Python 3).
        buf = outfile.buffer
    except AttributeError:
        buf = outfile

    for chunk in stream:
        buf.write(chunk)
        if flush:
            outfile.flush()


def write_with_colors_win_py3(stream, outfile, flush):
    """
    Writes output chunks to a stream, ensuring colorized text is processed by colorama on Windows with Python 3.
    
    Colorized chunks containing ANSI escape codes are decoded and written as text, while non-color chunks are written as bytes. Flushes the output if requested.
    """
    color = b'\x1b['
    encoding = outfile.encoding
    for chunk in stream:
        if color in chunk:
            outfile.write(chunk.decode(encoding))
        else:
            outfile.buffer.write(chunk)
        if flush:
            outfile.flush()


def build_output_stream(args, env, request, response):
    """
    Constructs an iterator chain that yields byte chunks representing the HTTP request and response exchange.
    
    The output includes headers and/or body for the request and response, as specified by output options. Separators and trailing newlines are inserted for terminal output to improve readability.
    """
    req_h = OUT_REQ_HEAD in args.output_options
    req_b = OUT_REQ_BODY in args.output_options
    resp_h = OUT_RESP_HEAD in args.output_options
    resp_b = OUT_RESP_BODY in args.output_options
    req = req_h or req_b
    resp = resp_h or resp_b

    output = []
    Stream = get_stream_type(env, args)

    if req:
        output.append(Stream(
            msg=HTTPRequest(request),
            with_headers=req_h,
            with_body=req_b))

    if req_b and resp:
        # Request/Response separator.
        output.append([b'\n\n'])

    if resp:
        output.append(Stream(
            msg=HTTPResponse(response),
            with_headers=resp_h,
            with_body=resp_b))

    if env.stdout_isatty and resp_b:
        # Ensure a blank line after the response body.
        # For terminal output only.
        output.append([b'\n\n'])

    return chain(*output)


def get_stream_type(env, args):
    """
    Selects and configures the appropriate HTTP output stream class based on environment and arguments.
    
    Returns a partial constructor for the chosen stream type, pre-filled with relevant parameters for raw, encoded, or prettified output.
    """
    if not env.stdout_isatty and not args.prettify:
        Stream = partial(
            RawStream,
            chunk_size=RawStream.CHUNK_SIZE_BY_LINE
            if args.stream
            else RawStream.CHUNK_SIZE
        )
    elif args.prettify:
        Stream = partial(
            PrettyStream if args.stream else BufferedPrettyStream,
            env=env,
            conversion=Conversion(),
            formatting=Formatting(env=env, groups=args.prettify,
                                  color_scheme=args.style),
        )
    else:
        Stream = partial(EncodedStream, env=env)

    return Stream


class BaseStream(object):
    """Base HTTP message output stream class."""

    def __init__(self, msg, with_headers=True, with_body=True,
                 on_body_chunk_downloaded=None):
        """
                 Initializes a stream for outputting an HTTP message.
                 
                 Args:
                     msg: An HTTPMessage instance representing the request or response.
                     with_headers: Whether to include headers in the output.
                     with_body: Whether to include the body in the output.
                     on_body_chunk_downloaded: Optional callback invoked when a body chunk is downloaded.
                 
                 At least one of headers or body must be included.
                 """
        assert with_headers or with_body
        self.msg = msg
        self.with_headers = with_headers
        self.with_body = with_body
        self.on_body_chunk_downloaded = on_body_chunk_downloaded

    def get_headers(self):
        """
        Returns the HTTP message headers as UTF-8 encoded bytes.
        """
        return self.msg.headers.encode('utf8')

    def iter_body(self):
        """
        Returns an iterator over the message body.
        
        This method must be implemented by subclasses to yield body content in chunks.
        """
        raise NotImplementedError()

    def __iter__(self):
        """
        Yields the headers and body of the HTTP message as byte chunks.
        
        If headers are enabled, yields the encoded headers followed by a separator. If the body is enabled, yields each body chunk, optionally invoking a callback after each chunk. If binary data is suppressed, yields a notice instead of the body.
        """
        if self.with_headers:
            yield self.get_headers()
            yield b'\r\n\r\n'

        if self.with_body:
            try:
                for chunk in self.iter_body():
                    yield chunk
                    if self.on_body_chunk_downloaded:
                        self.on_body_chunk_downloaded(chunk)
            except BinarySuppressedError as e:
                if self.with_headers:
                    yield b'\n'
                yield e.message


class RawStream(BaseStream):
    """The message is streamed in chunks with no processing."""

    CHUNK_SIZE = 1024 * 100
    CHUNK_SIZE_BY_LINE = 1

    def __init__(self, chunk_size=CHUNK_SIZE, **kwargs):
        """
        Initializes a RawStream for streaming message bodies in raw byte chunks.
        
        Args:
            chunk_size: The size of each chunk to read from the message body, in bytes.
        """
        super(RawStream, self).__init__(**kwargs)
        self.chunk_size = chunk_size

    def iter_body(self):
        """
        Yields raw body chunks from the HTTP message using the specified chunk size.
        """
        return self.msg.iter_body(self.chunk_size)


class EncodedStream(BaseStream):
    """Encoded HTTP message stream.

    The message bytes are converted to an encoding suitable for
    `self.env.stdout`. Unicode errors are replaced and binary data
    is suppressed. The body is always streamed by line.

    """
    CHUNK_SIZE = 1

    def __init__(self, env=Environment(), **kwargs):

        """
        Initializes the EncodedStream with the appropriate output encoding.
        
        Selects the encoding for output based on whether the output is a terminal (TTY). If writing to a terminal, uses the terminal's encoding; otherwise, preserves the message's original encoding. Defaults to UTF-8 if no encoding is specified.
        """
        super(EncodedStream, self).__init__(**kwargs)

        if env.stdout_isatty:
            # Use the encoding supported by the terminal.
            output_encoding = env.stdout_encoding
        else:
            # Preserve the message encoding.
            output_encoding = self.msg.encoding

        # Default to utf8 when unsure.
        self.output_encoding = output_encoding or 'utf8'

    def iter_body(self):

        """
        Iterates over the message body, yielding each line re-encoded for terminal output.
        
        Raises:
            BinarySuppressedError: If binary data (null bytes) is detected in the body.
        """
        for line, lf in self.msg.iter_lines(self.CHUNK_SIZE):

            if b'\0' in line:
                raise BinarySuppressedError()

            yield line.decode(self.msg.encoding) \
                      .encode(self.output_encoding, 'replace') + lf


class PrettyStream(EncodedStream):
    """In addition to :class:`EncodedStream` behaviour, this stream applies
    content processing.

    Useful for long-lived HTTP responses that stream by lines
    such as the Twitter streaming API.

    """

    CHUNK_SIZE = 1

    def __init__(self, conversion, formatting, **kwargs):
        """
        Initializes a PrettyStream for processing and formatting HTTP message output.
        
        Args:
            conversion: The content converter to apply to the message body.
            formatting: The formatter used to prettify the output.
            **kwargs: Additional arguments passed to the BaseStream initializer.
        """
        super(PrettyStream, self).__init__(**kwargs)
        self.formatting = formatting
        self.conversion = conversion
        self.mime = self.msg.content_type.split(';')[0]

    def get_headers(self):
        """
        Returns the formatted and encoded HTTP headers for the message.
        
        The headers are formatted using the configured formatting object and encoded with the output encoding.
        """
        return self.formatting.format_headers(
            self.msg.headers).encode(self.output_encoding)

    def iter_body(self):
        """
        Iterates over the message body, applying formatting and conversion as needed.
        
        If binary data is detected in the first chunk and a suitable converter is available, the entire body is converted and processed before yielding. If no converter is found, binary data is suppressed by raising a BinarySuppressedError. Each line is processed and formatted before being yielded as encoded output.
        """
        first_chunk = True
        iter_lines = self.msg.iter_lines(self.CHUNK_SIZE)
        for line, lf in iter_lines:
            if b'\0' in line:
                if first_chunk:
                    converter = self.conversion.get_converter(self.mime)
                    if converter:
                        body = bytearray()
                        # noinspection PyAssignmentToLoopOrWithParameter
                        for line, lf in chain([(line, lf)], iter_lines):
                            body.extend(line)
                            body.extend(lf)
                        self.mime, body = converter.convert(body)
                        assert isinstance(body, str)
                        yield self.process_body(body)
                        return
                raise BinarySuppressedError()
            yield self.process_body(line) + lf
            first_chunk = False

    def process_body(self, chunk):
        """
        Processes a body chunk by formatting and encoding it for output.
        
        If the chunk is not a string, it is decoded using the message's encoding. The chunk is then formatted according to the specified MIME type and re-encoded using the output encoding.
        """
        if not isinstance(chunk, str):
            # Text when a converter has been used,
            # otherwise it will always be bytes.
            chunk = chunk.decode(self.msg.encoding, 'replace')
        chunk = self.formatting.format_body(content=chunk, mime=self.mime)
        return chunk.encode(self.output_encoding, 'replace')


class BufferedPrettyStream(PrettyStream):
    """The same as :class:`PrettyStream` except that the body is fully
    fetched before it's processed.

    Suitable regular HTTP responses.

    """

    CHUNK_SIZE = 1024 * 10

    def iter_body(self):
        # Read the whole body before prettifying it,
        # but bail out immediately if the body is binary.
        """
        Iterates over the entire message body, buffering it before processing and formatting.
        
        If binary data is detected and a suitable converter is unavailable, raises BinarySuppressedError. Otherwise, applies conversion and formatting to the complete body and yields the processed result as a single chunk.
        """
        converter = None
        body = bytearray()

        for chunk in self.msg.iter_body(self.CHUNK_SIZE):
            if not converter and b'\0' in chunk:
                converter = self.conversion.get_converter(self.mime)
                if not converter:
                    raise BinarySuppressedError()
            body.extend(chunk)

        if converter:
            self.mime, body = converter.convert(body)

        yield self.process_body(body)
