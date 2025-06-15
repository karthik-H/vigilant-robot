from httpie.compat import urlsplit, str


class HTTPMessage(object):
    """Abstract class for HTTP messages."""

    def __init__(self, orig):
        """
        Initializes the HTTPMessage with the original HTTP message object.
        
        Args:
            orig: The underlying HTTP request or response object to be wrapped.
        """
        self._orig = orig

    def iter_body(self, chunk_size):
        """
        Returns an iterator over the message body in chunks of the specified size.
        
        Args:
            chunk_size: The size of each chunk to yield from the body.
        """
        raise NotImplementedError()

    def iter_lines(self, chunk_size):
        """
        Returns an iterator over the message body, yielding tuples of (line, line_feed).
        
        Each iteration yields a line from the body and its corresponding line feed as a tuple.
        """
        raise NotImplementedError()

    @property
    def headers(self):
        """
        Returns the HTTP message headers as a string.
        
        This property should be implemented by subclasses to provide the formatted headers of the HTTP message.
        """
        raise NotImplementedError()

    @property
    def encoding(self):
        """
        Returns the encoding used for the HTTP message, if available.
        
        Raises:
            NotImplementedError: If the encoding is not implemented by the subclass.
        """
        raise NotImplementedError()

    @property
    def body(self):
        """
        Returns the message body as bytes.
        
        This property should be implemented by subclasses to provide the raw body content of the HTTP message.
        """
        raise NotImplementedError()

    @property
    def content_type(self):
        """
        Returns the Content-Type header value of the HTTP message.
        
        If the header value is in bytes, it is decoded as UTF-8.
        """
        ct = self._orig.headers.get('Content-Type', '')
        if not isinstance(ct, str):
            ct = ct.decode('utf8')
        return ct


class HTTPResponse(HTTPMessage):
    """A :class:`requests.models.Response` wrapper."""

    def iter_body(self, chunk_size=1):
        """
        Iterates over the response body in chunks of the specified size.
        
        Args:
            chunk_size: The number of bytes to read per chunk.
        
        Returns:
            An iterator yielding chunks of the response body as bytes.
        """
        return self._orig.iter_content(chunk_size=chunk_size)

    def iter_lines(self, chunk_size):
        """
        Iterates over the response body line by line, yielding each line with a line feed.
        
        Args:
            chunk_size: The size of each chunk to read from the response.
        
        Yields:
            Tuples containing a line from the response body and a line feed (b'\n').
        """
        return ((line, b'\n') for line in self._orig.iter_lines(chunk_size))

    #noinspection PyProtectedMember
    @property
    def headers(self):
        """
        Returns the HTTP response headers as a formatted string, including the status line.
        
        The headers are constructed from the underlying raw HTTP response object, with compatibility for both Python 2 and 3 HTTPMessage implementations. The status line includes the HTTP version, status code, and reason phrase, followed by all response headers, each separated by CRLF.
        """
        original = self._orig.raw._original_response

        version = {
            9: '0.9',
            10: '1.0',
            11: '1.1',
            20: '2',
        }[original.version]

        status_line = 'HTTP/{version} {status} {reason}'.format(
            version=version,
            status=original.status,
            reason=original.reason
        )
        headers = [status_line]
        try:
            # `original.msg` is a `http.client.HTTPMessage` on Python 3
            # `_headers` is a 2-tuple
            headers.extend(
                '%s: %s' % header for header in original.msg._headers)
        except AttributeError:
            # and a `httplib.HTTPMessage` on Python 2.x
            # `headers` is a list of `name: val<CRLF>`.
            headers.extend(h.strip() for h in original.msg.headers)

        return '\r\n'.join(headers)

    @property
    def encoding(self):
        """
        Returns the character encoding used for the HTTP response body.
        
        If the original response does not specify an encoding, defaults to 'utf8'.
        """
        return self._orig.encoding or 'utf8'

    @property
    def body(self):
        # Only now the response body is fetched.
        # Shouldn't be touched unless the body is actually needed.
        """
        Returns the full response body as bytes.
        
        The body is fetched from the underlying response object only when accessed.
        """
        return self._orig.content


class HTTPRequest(HTTPMessage):
    """A :class:`requests.models.Request` wrapper."""

    def iter_body(self, chunk_size):
        """
        Yields the entire HTTP request body as a single chunk.
        
        Args:
            chunk_size: Ignored. Present for interface compatibility.
        
        Yields:
            The full request body as bytes.
        """
        yield self.body

    def iter_lines(self, chunk_size):
        """
        Yields the entire request body as a single line.
        
        Args:
            chunk_size: Ignored in this implementation.
        
        Yields:
            A tuple containing the full request body and an empty byte string.
        """
        yield self.body, b''

    @property
    def headers(self):
        """
        Constructs and returns the full HTTP request headers as a formatted string.
        
        The returned string includes the request line (method, path, query, and HTTP version) followed by all headers, ensuring the 'Host' header is present. Header values are decoded to UTF-8 if necessary, and the result is formatted with CRLF line endings.
        """
        url = urlsplit(self._orig.url)

        request_line = '{method} {path}{query} HTTP/1.1'.format(
            method=self._orig.method,
            path=url.path or '/',
            query='?' + url.query if url.query else ''
        )

        headers = dict(self._orig.headers)
        if 'Host' not in self._orig.headers:
            headers['Host'] = url.netloc.split('@')[-1]

        headers = [
            '%s: %s' % (
                name,
                value if isinstance(value, str) else value.decode('utf8')
            )
            for name, value in headers.items()
        ]

        headers.insert(0, request_line)
        headers = '\r\n'.join(headers).strip()

        if isinstance(headers, bytes):
            # Python < 3
            headers = headers.decode('utf8')
        return headers

    @property
    def encoding(self):
        """
        Returns the encoding used for the HTTP request body, which is always 'utf8'.
        """
        return 'utf8'

    @property
    def body(self):
        """
        Returns the HTTP request body as bytes.
        
        If the original body is a string, it is encoded as UTF-8. Returns empty bytes if the body is None.
        """
        body = self._orig.body
        if isinstance(body, str):
            # Happens with JSON/form request data parsed from the command line.
            body = body.encode('utf8')
        return body or b''
