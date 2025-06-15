# coding=utf-8
"""
Download mode implementation.

"""
from __future__ import division
import os
import re
import sys
import mimetypes
import threading
from time import sleep, time
from mailbox import Message

from httpie.output.streams import RawStream
from httpie.models import HTTPResponse
from httpie.utils import humanize_bytes
from httpie.compat import urlsplit


PARTIAL_CONTENT = 206


CLEAR_LINE = '\r\033[K'
PROGRESS = (
    '{percentage: 6.2f} %'
    ' {downloaded: >10}'
    ' {speed: >10}/s'
    ' {eta: >8} ETA'
)
PROGRESS_NO_CONTENT_LENGTH = '{downloaded: >10} {speed: >10}/s'
SUMMARY = 'Done. {downloaded} in {time:0.5f}s ({speed}/s)\n'
SPINNER = '|/-\\'


class ContentRangeError(ValueError):
    pass


def parse_content_range(content_range, resumed_from):
    """
    Parses and validates a Content-Range HTTP header against the requested byte range.
    
    Args:
        content_range: The value of the Content-Range response header (e.g., "bytes 21010-47021/47022").
        resumed_from: The starting byte position requested for resuming the download.
    
    Returns:
        The total size of the response body when fully downloaded.
    
    Raises:
        ContentRangeError: If the Content-Range header is missing, malformed, or inconsistent with the requested range.
    """
    if content_range is None:
        raise ContentRangeError('Missing Content-Range')

    pattern = (
        '^bytes (?P<first_byte_pos>\d+)-(?P<last_byte_pos>\d+)'
        '/(\*|(?P<instance_length>\d+))$'
    )
    match = re.match(pattern, content_range)

    if not match:
        raise ContentRangeError(
            'Invalid Content-Range format %r' % content_range)

    content_range_dict = match.groupdict()
    first_byte_pos = int(content_range_dict['first_byte_pos'])
    last_byte_pos = int(content_range_dict['last_byte_pos'])
    instance_length = (
        int(content_range_dict['instance_length'])
        if content_range_dict['instance_length']
        else None
    )

    # "A byte-content-range-spec with a byte-range-resp-spec whose
    # last- byte-pos value is less than its first-byte-pos value,
    # or whose instance-length value is less than or equal to its
    # last-byte-pos value, is invalid. The recipient of an invalid
    # byte-content-range- spec MUST ignore it and any content
    # transferred along with it."
    if (first_byte_pos >= last_byte_pos
            or (instance_length is not None
                and instance_length <= last_byte_pos)):
        raise ContentRangeError(
            'Invalid Content-Range returned: %r' % content_range)

    if (first_byte_pos != resumed_from
        or (instance_length is not None
            and last_byte_pos + 1 != instance_length)):
        # Not what we asked for.
        raise ContentRangeError(
            'Unexpected Content-Range returned (%r)'
            ' for the requested Range ("bytes=%d-")'
            % (content_range, resumed_from)
        )

    return last_byte_pos + 1


def filename_from_content_disposition(content_disposition):
    """
    Extracts and sanitizes a filename from a Content-Disposition header.
    
    Returns the filename if present and valid; otherwise, returns None.
    """
    # attachment; filename=jkbrzt-httpie-0.4.1-20-g40bd8f6.tar.gz

    msg = Message('Content-Disposition: %s' % content_disposition)
    filename = msg.get_filename()
    if filename:
        # Basic sanitation.
        filename = os.path.basename(filename).lstrip('.').strip()
        if filename:
            return filename


def filename_from_url(url, content_type):
    """
    Generates a filename from a URL, appending an extension based on content type if needed.
    
    If the URL path does not specify a filename or extension, a default name is used and an extension is guessed from the provided content type.
    """
    fn = urlsplit(url).path.rstrip('/')
    fn = os.path.basename(fn) if fn else 'index'
    if '.' not in fn and content_type:
        content_type = content_type.split(';')[0]
        if content_type == 'text/plain':
            # mimetypes returns '.ksh'
            ext = '.txt'
        else:
            ext = mimetypes.guess_extension(content_type)

        if ext == '.htm':  # Python 3
            ext = '.html'

        if ext:
            fn += ext

    return fn


def get_unique_filename(filename, exists=os.path.exists):
    """
    Generates a unique filename by appending a numeric suffix if needed.
    
    If the specified filename already exists, appends an incrementing numeric suffix (e.g., '-1', '-2') until a non-existing filename is found.
    
    Args:
        filename: The desired base filename.
    
    Returns:
        A filename that does not exist according to the provided existence check.
    """
    attempt = 0
    while True:
        suffix = '-' + str(attempt) if attempt > 0 else ''
        if not exists(filename + suffix):
            return filename + suffix
        attempt += 1


class Download(object):

    def __init__(self, output_file=None,
                 resume=False, progress_file=sys.stderr):
        """
                 Initializes a Download instance to manage HTTP file downloads.
                 
                 Args:
                     output_file: Optional file path to save the downloaded content. If not provided, the filename will be determined from the response.
                     resume: If True, attempts to resume an incomplete download if a partial file exists.
                     progress_file: Output stream for reporting download progress.
                 """
        self._output_file = output_file
        self._resume = resume
        self._resumed_from = 0
        self.finished = False

        self.status = Status()
        self._progress_reporter = ProgressReporterThread(
            status=self.status,
            output=progress_file
        )

    def pre_request(self, request_headers):
        """
        Prepares HTTP request headers for downloading, enabling resuming if applicable.
        
        Modifies the headers to disable content encoding and, if resuming is enabled, sets the `Range` header to continue downloading from where a previous download left off.
        """
        # Disable content encoding so that we can resume, etc.
        request_headers['Accept-Encoding'] = None
        if self._resume:
            bytes_have = os.path.getsize(self._output_file.name)
            if bytes_have:
                # Set ``Range`` header to resume the download
                # TODO: Use "If-Range: mtime" to make sure it's fresh?
                request_headers['Range'] = 'bytes=%d-' % bytes_have
                self._resumed_from = bytes_have

    def start(self, response):
        """
        Starts the download process for the given HTTP response, preparing the output file and progress reporting.
        
        Initializes the output file for writing, handles resuming if enabled, and sets up a stream with a progress callback. Returns the stream for reading the response body and the output file object.
        """
        assert not self.status.time_started

        try:
            total_size = int(response.headers['Content-Length'])
        except (KeyError, ValueError, TypeError):
            total_size = None

        if self._output_file:
            if self._resume and response.status_code == PARTIAL_CONTENT:
                total_size = parse_content_range(
                    response.headers.get('Content-Range'),
                    self._resumed_from
                )

            else:
                self._resumed_from = 0
                try:
                    self._output_file.seek(0)
                    self._output_file.truncate()
                except IOError:
                    pass  # stdout
        else:
            # TODO: Should the filename be taken from response.history[0].url?
            # Output file not specified. Pick a name that doesn't exist yet.
            filename = None
            if 'Content-Disposition' in response.headers:
                filename = filename_from_content_disposition(
                    response.headers['Content-Disposition'])
            if not filename:
                filename = filename_from_url(
                    url=response.url,
                    content_type=response.headers.get('Content-Type'),
                )
            self._output_file = open(get_unique_filename(filename), mode='a+b')

        self.status.started(
            resumed_from=self._resumed_from,
            total_size=total_size
        )

        stream = RawStream(
            msg=HTTPResponse(response),
            with_headers=False,
            with_body=True,
            on_body_chunk_downloaded=self.chunk_downloaded,
            chunk_size=1024 * 8
        )

        self._progress_reporter.output.write(
            'Downloading %sto "%s"\n' % (
                (humanize_bytes(total_size) + ' '
                 if total_size is not None
                 else ''),
                self._output_file.name
            )
        )
        self._progress_reporter.start()

        return stream, self._output_file

    def finish(self):
        """
        Marks the download as finished and updates the status to indicate completion.
        """
        assert not self.finished
        self.finished = True
        self.status.finished()

    def failed(self):
        """
        Stops the progress reporter thread when the download fails.
        """
        self._progress_reporter.stop()

    @property
    def interrupted(self):
        """
        Indicates whether the download was interrupted before completion.
        
        Returns:
            True if the download has finished but the total downloaded bytes do not match the expected total size; otherwise, False.
        """
        return (
            self.finished
            and self.status.total_size
            and self.status.total_size != self.status.downloaded
        )

    def chunk_downloaded(self, chunk):
        """
        Updates the download status with the size of a newly downloaded chunk.
        
        Args:
            chunk: The bytes object representing the downloaded data chunk.
        """
        self.status.chunk_downloaded(len(chunk))


class Status(object):
    """Holds details about the downland status."""

    def __init__(self):
        """
        Initializes the Status object to track download progress and timing.
        
        Sets counters for downloaded bytes, total size, resumed offset, and timestamps for start and finish.
        """
        self.downloaded = 0
        self.total_size = None
        self.resumed_from = 0
        self.time_started = None
        self.time_finished = None

    def started(self, resumed_from=0, total_size=None):
        """
        Marks the start of the download, recording the start time, resumed offset, and total size if provided.
        
        Args:
            resumed_from: The byte offset from which the download is resumed.
            total_size: The total size of the file being downloaded, if known.
        """
        assert self.time_started is None
        if total_size is not None:
            self.total_size = total_size
        self.downloaded = self.resumed_from = resumed_from
        self.time_started = time()

    def chunk_downloaded(self, size):
        """
        Updates the downloaded byte count by adding the size of the latest chunk.
        
        Args:
            size: The number of bytes in the downloaded chunk.
        """
        assert self.time_finished is None
        self.downloaded += size

    @property
    def has_finished(self):
        """
        Indicates whether the download has finished.
        
        Returns:
            True if the finish time has been recorded, otherwise False.
        """
        return self.time_finished is not None

    def finished(self):
        """
        Marks the download as finished by recording the finish timestamp.
        """
        assert self.time_started is not None
        assert self.time_finished is None
        self.time_finished = time()


class ProgressReporterThread(threading.Thread):
    """
    Reports download progress based on its status.

    Uses threading to periodically update the status (speed, ETA, etc.).

    """
    def __init__(self, status, output, tick=.1, update_interval=1):
        """
        Initializes a thread for periodically reporting download progress.
        
        Args:
            status: The Status object tracking download progress.
            output: The output stream to which progress updates are written.
            tick: Time interval in seconds between progress updates.
            update_interval: Time interval in seconds for recalculating download speed.
        """
        super(ProgressReporterThread, self).__init__()
        self.status = status
        self.output = output
        self._tick = tick
        self._update_interval = update_interval
        self._spinner_pos = 0
        self._status_line = ''
        self._prev_bytes = 0
        self._prev_time = time()
        self._should_stop = threading.Event()

    def stop(self):
        """
        Signals the progress reporter thread to stop at the next update interval.
        """
        self._should_stop.set()

    def run(self):
        """
        Runs the progress reporting loop until the download finishes or is stopped.
        
        Periodically updates the progress display and, upon completion, outputs a summary line.
        """
        while not self._should_stop.is_set():
            if self.status.has_finished:
                self.sum_up()
                break

            self.report_speed()
            sleep(self._tick)

    def report_speed(self):

        """
        Calculates and displays the current download progress, speed, and ETA.
        
        Updates the progress line based on the amount of data downloaded and the elapsed time.
        Displays a spinner animation and writes the formatted progress information to the output stream.
        """
        now = time()

        if now - self._prev_time >= self._update_interval:
            downloaded = self.status.downloaded
            try:
                speed = ((downloaded - self._prev_bytes)
                         / (now - self._prev_time))
            except ZeroDivisionError:
                speed = 0

            if not self.status.total_size:
                self._status_line = PROGRESS_NO_CONTENT_LENGTH.format(
                    downloaded=humanize_bytes(downloaded),
                    speed=humanize_bytes(speed),
                )
            else:
                try:
                    percentage = downloaded / self.status.total_size * 100
                except ZeroDivisionError:
                    percentage = 0

                if not speed:
                    eta = '-:--:--'
                else:
                    s = int((self.status.total_size - downloaded) / speed)
                    h, s = divmod(s, 60 * 60)
                    m, s = divmod(s, 60)
                    eta = '{0}:{1:0>2}:{2:0>2}'.format(h, m, s)

                self._status_line = PROGRESS.format(
                    percentage=percentage,
                    downloaded=humanize_bytes(downloaded),
                    speed=humanize_bytes(speed),
                    eta=eta,
                )

            self._prev_time = now
            self._prev_bytes = downloaded

        self.output.write(
            CLEAR_LINE
            + ' '
            + SPINNER[self._spinner_pos]
            + ' '
            + self._status_line
        )
        self.output.flush()

        self._spinner_pos = (self._spinner_pos + 1
                             if self._spinner_pos + 1 != len(SPINNER)
                             else 0)

    def sum_up(self):
        """
        Writes a summary of the completed download, including total bytes, duration, and average speed.
        """
        actually_downloaded = (self.status.downloaded
                               - self.status.resumed_from)
        time_taken = self.status.time_finished - self.status.time_started

        self.output.write(CLEAR_LINE)

        try:
            speed = actually_downloaded / time_taken
        except ZeroDivisionError:
            # Either time is 0 (not all systems provide `time.time`
            # with a better precision than 1 second), and/or nothing
            # has been downloaded.
            speed = actually_downloaded

        self.output.write(SUMMARY.format(
            downloaded=humanize_bytes(actually_downloaded),
            total=(self.status.total_size
                   and humanize_bytes(self.status.total_size)),
            speed=humanize_bytes(speed),
            time=time_taken,
        ))
        self.output.flush()
