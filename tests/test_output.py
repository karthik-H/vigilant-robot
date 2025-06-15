import pytest

from utils import TestEnvironment, http, HTTP_OK, COLOR, CRLF
from httpie import ExitStatus
from httpie.output.formatters.colors import get_lexer


class TestVerboseFlag:
    def test_verbose(self, httpbin):
        """
        Tests that the --verbose flag displays both request and response headers.
        
        Sends a GET request with a custom header and asserts that the header appears twice in the output, indicating it is shown in both the request and response sections.
        """
        r = http('--verbose',
                 'GET', httpbin.url + '/get', 'test-header:__test__')
        assert HTTP_OK in r
        assert r.count('__test__') == 2

    def test_verbose_form(self, httpbin):
        # https://github.com/jkbrzt/httpie/issues/53
        """
        Tests that the --verbose flag with --form on a POST request displays form data in the output.
        
        Sends a POST request with form data using --verbose and --form, then asserts that the response is HTTP 200 OK and the form data appears in the output.
        """
        r = http('--verbose', '--form', 'POST', httpbin.url + '/post',
                 'A=B', 'C=D')
        assert HTTP_OK in r
        assert 'A=B&C=D' in r

    def test_verbose_json(self, httpbin):
        """
        Tests that the --verbose flag displays JSON request and response details for a POST request.
        
        Sends a POST request with JSON data using the --verbose flag and asserts that the response is HTTP 200 OK and that the JSON key-value pair appears in the output.
        """
        r = http('--verbose',
                 'POST', httpbin.url + '/post', 'foo=bar', 'baz=bar')
        assert HTTP_OK in r
        assert '"baz": "bar"' in r


class TestColors:

    @pytest.mark.parametrize('mime', [
        'application/json',
        'application/json+foo',
        'application/foo+json',
        'application/json-foo',
        'application/x-json',
        'foo/json',
        'foo/json+bar',
        'foo/bar+json',
        'foo/json-foo',
        'foo/x-json',
    ])
    def test_get_lexer(self, mime):
        """
        Tests that the get_lexer function returns a JSON lexer for the given MIME type.
        
        Asserts that the returned lexer is not None and its name is 'JSON'.
        """
        lexer = get_lexer(mime)
        assert lexer is not None
        assert lexer.name == 'JSON'

    def test_get_lexer_not_found(self):
        """
        Tests that get_lexer returns None for an unknown MIME type.
        """
        assert get_lexer('xxx/yyy') is None


class TestPrettyOptions:
    """Test the --pretty flag handling."""

    def test_pretty_enabled_by_default(self, httpbin):
        """
        Tests that pretty (colored) output is enabled by default when the environment supports colors.
        """
        env = TestEnvironment(colors=256)
        r = http('GET', httpbin.url + '/get', env=env)
        assert COLOR in r

    def test_pretty_enabled_by_default_unless_stdout_redirected(self, httpbin):
        """
        Verifies that pretty output with colors is disabled by default when stdout is redirected.
        
        Sends a GET request and asserts that color codes are not present in the output when the output is not a TTY.
        """
        r = http('GET', httpbin.url + '/get')
        assert COLOR not in r

    def test_force_pretty(self, httpbin):
        """
        Tests that pretty output with colors is forced when using '--pretty=all', even if stdout is not a TTY.
        """
        env = TestEnvironment(stdout_isatty=False, colors=256)
        r = http('--pretty=all', 'GET', httpbin.url + '/get', env=env, )
        assert COLOR in r

    def test_force_ugly(self, httpbin):
        """
        Tests that disabling pretty output with '--pretty=none' results in no color codes in the response.
        """
        r = http('--pretty=none', 'GET', httpbin.url + '/get')
        assert COLOR not in r

    def test_subtype_based_pygments_lexer_match(self, httpbin):
        """
        Tests that the media subtype is used to select a syntax highlighter when the main MIME type does not match any known lexer.
        
        Sends a POST request with a custom Content-Type using a subtype (e.g., foo+json) and asserts that colored output is produced, indicating the correct lexer is applied.
        """
        env = TestEnvironment(colors=256)
        r = http('--print=B', '--pretty=all', httpbin.url + '/post',
                 'Content-Type:text/foo+json', 'a=b', env=env)
        assert COLOR in r

    def test_colors_option(self, httpbin):
        """
        Tests that using '--pretty=colors' with '--print=B' produces colored output without multiline formatting.
        
        Asserts that the output contains color codes but is not formatted across multiple lines.
        """
        env = TestEnvironment(colors=256)
        r = http('--print=B', '--pretty=colors',
                 'GET', httpbin.url + '/get', 'a=b',
                 env=env)
        # Tests that the JSON data isn't formatted.
        assert not r.strip().count('\n')
        assert COLOR in r

    def test_format_option(self, httpbin):
        """
        Tests that the '--pretty=format' option formats JSON output with multiline formatting but without color codes.
        """
        env = TestEnvironment(colors=256)
        r = http('--print=B', '--pretty=format',
                 'GET', httpbin.url + '/get', 'a=b',
                 env=env)
        # Tests that the JSON data is formatted.
        assert r.strip().count('\n') == 2
        assert COLOR not in r


class TestLineEndings:
    """
    Test that CRLF is properly used in headers
    and as the headers/body separator.

    """
    def _validate_crlf(self, msg):
        """
        Validates that HTTP headers in the message end with CRLF and that the separator between headers and body is present.
        
        Checks each header line for CRLF line endings, ensures a CRLF-only line separates headers from the body, and asserts that the body does not contain CRLF. Returns the body content.
        """
        lines = iter(msg.splitlines(True))
        for header in lines:
            if header == CRLF:
                break
            assert header.endswith(CRLF), repr(header)
        else:
            assert 0, 'CRLF between headers and body not found in %r' % msg
        body = ''.join(lines)
        assert CRLF not in body
        return body

    def test_CRLF_headers_only(self, httpbin):
        """
        Tests that CRLF line endings are used in headers when only headers are requested.
        
        Sends a GET request for headers only and asserts that all header lines end with CRLF, the separator is present, and no body content is returned.
        """
        r = http('--headers', 'GET', httpbin.url + '/get')
        body = self._validate_crlf(r)
        assert not body, 'Garbage after headers: %r' % r

    def test_CRLF_ugly_response(self, httpbin):
        """
        Tests that CRLF line endings are used in the response headers when pretty formatting is disabled.
        """
        r = http('--pretty=none', 'GET', httpbin.url + '/get')
        self._validate_crlf(r)

    def test_CRLF_formatted_response(self, httpbin):
        """
        Tests that a formatted HTTP response uses CRLF line endings in headers and between headers and body.
        
        Asserts that the response has a successful exit status and validates correct CRLF usage.
        """
        r = http('--pretty=format', 'GET', httpbin.url + '/get')
        assert r.exit_status == ExitStatus.OK
        self._validate_crlf(r)

    def test_CRLF_ugly_request(self, httpbin):
        """
        Tests that CRLF line endings are correctly used in both headers and body when making a request with no pretty formatting and printing both headers and body.
        """
        r = http('--pretty=none', '--print=HB', 'GET', httpbin.url + '/get')
        self._validate_crlf(r)

    def test_CRLF_formatted_request(self, httpbin):
        """
        Tests that formatted HTTP requests use CRLF line endings in headers and between headers and body.
        
        Sends a GET request with formatted output and verifies correct CRLF usage in the request output.
        """
        r = http('--pretty=format', '--print=HB', 'GET', httpbin.url + '/get')
        self._validate_crlf(r)
