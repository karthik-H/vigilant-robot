"""Tests for dealing with binary request and response data."""
from httpie.compat import urlopen
from httpie.output.streams import BINARY_SUPPRESSED_NOTICE
from utils import TestEnvironment, http
from fixtures import BIN_FILE_PATH, BIN_FILE_CONTENT, BIN_FILE_PATH_ARG


class TestBinaryRequestData:
    def test_binary_stdin(self, httpbin):
        """
        Tests sending binary data from standard input in a POST request.
        
        Opens a binary file as stdin, sends its contents to the specified endpoint, and asserts that the response matches the original binary data.
        """
        with open(BIN_FILE_PATH, 'rb') as stdin:
            env = TestEnvironment(
                stdin=stdin,
                stdin_isatty=False,
                stdout_isatty=False
            )
            r = http('--print=B', 'POST', httpbin.url + '/post', env=env)
            assert r == BIN_FILE_CONTENT

    def test_binary_file_path(self, httpbin):
        """
        Tests sending binary data from a file path in a POST request.
        
        Sends a POST request with binary data read from a specified file path and verifies that the response matches the expected binary file content.
        """
        env = TestEnvironment(stdin_isatty=True, stdout_isatty=False)
        r = http('--print=B', 'POST', httpbin.url + '/post',
                 '@' + BIN_FILE_PATH_ARG, env=env, )
        assert r == BIN_FILE_CONTENT

    def test_binary_file_form(self, httpbin):
        """
        Tests sending binary data as a form field in a POST request.
        
        Verifies that the binary file content is included in the response when submitted as form data.
        """
        env = TestEnvironment(stdin_isatty=True, stdout_isatty=False)
        r = http('--print=B', '--form', 'POST', httpbin.url + '/post',
                 'test@' + BIN_FILE_PATH_ARG, env=env)
        assert bytes(BIN_FILE_CONTENT) in bytes(r)


class TestBinaryResponseData:
    url = 'http://www.google.com/favicon.ico'

    @property
    def bindata(self):
        """
        Fetches and caches the binary content from the specified URL on first access.
        
        Returns:
            The binary data retrieved from the URL.
        """
        if not hasattr(self, '_bindata'):
            self._bindata = urlopen(self.url).read()
        return self._bindata

    def test_binary_suppresses_when_terminal(self):
        """
        Tests that a binary suppression notice is present in the response when output is directed to a terminal.
        """
        r = http('GET', self.url)
        assert BINARY_SUPPRESSED_NOTICE.decode() in r

    def test_binary_suppresses_when_not_terminal_but_pretty(self):
        """
        Tests that the binary suppression notice appears when pretty-printing is enabled and stdout is not a terminal.
        """
        env = TestEnvironment(stdin_isatty=True, stdout_isatty=False)
        r = http('--pretty=all', 'GET', self.url,
                 env=env)
        assert BINARY_SUPPRESSED_NOTICE.decode() in r

    def test_binary_included_and_correct_when_suitable(self):
        """
        Tests that the binary response data is included and matches the expected content when output is not directed to a terminal.
        """
        env = TestEnvironment(stdin_isatty=True, stdout_isatty=False)
        r = http('GET', self.url, env=env)
        assert r == self.bindata
