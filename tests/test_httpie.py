"""High-level tests."""
import pytest
from utils import TestEnvironment, http, HTTP_OK
from fixtures import FILE_PATH, FILE_CONTENT

import httpie
from httpie.compat import is_py26


class TestHTTPie:

    def test_debug(self):
        """
        Tests that running HTTPie with the --debug flag outputs version and debug information to stderr and exits successfully.
        """
        r = http('--debug')
        assert r.exit_status == httpie.ExitStatus.OK
        assert 'HTTPie %s' % httpie.__version__ in r.stderr
        assert 'HTTPie data:' in r.stderr

    def test_help(self):
        """
        Tests that the HTTPie help command executes successfully and includes the GitHub issues URL in its output.
        """
        r = http('--help', error_exit_ok=True)
        assert r.exit_status == httpie.ExitStatus.OK
        assert 'https://github.com/jkbrzt/httpie/issues' in r

    def test_version(self):
        """
        Tests that the HTTPie version command outputs the correct version string.
        
        Asserts that running HTTPie with the `--version` flag exits successfully and that the reported version matches the expected HTTPie version, accounting for differences in output streams between Python 2 and 3.
        """
        r = http('--version', error_exit_ok=True)
        assert r.exit_status == httpie.ExitStatus.OK
        # FIXME: py3 has version in stdout, py2 in stderr
        assert httpie.__version__ == r.stderr.strip() + r.strip()

    def test_GET(self, httpbin):
        """
        Tests that a GET request to the /get endpoint returns an HTTP OK response.
        """
        r = http('GET', httpbin.url + '/get')
        assert HTTP_OK in r

    def test_DELETE(self, httpbin):
        """
        Tests that sending a DELETE request to the /delete endpoint returns an HTTP OK response.
        """
        r = http('DELETE', httpbin.url + '/delete')
        assert HTTP_OK in r

    def test_PUT(self, httpbin):
        """
        Tests sending a PUT request with JSON data and verifies the response contains the sent data.
        
        Sends a PUT request to the /put endpoint with a JSON payload and asserts that the response status is HTTP OK and the returned JSON matches the sent data.
        """
        r = http('PUT', httpbin.url + '/put', 'foo=bar')
        assert HTTP_OK in r
        assert r.json['json']['foo'] == 'bar'

    def test_POST_JSON_data(self, httpbin):
        """
        Tests sending a POST request with JSON data using HTTPie.
        
        Sends a POST request with a JSON payload to the /post endpoint of the test server and verifies that the response status is HTTP OK and the returned JSON contains the sent data.
        """
        r = http('POST', httpbin.url + '/post', 'foo=bar')
        assert HTTP_OK in r
        assert r.json['json']['foo'] == 'bar'

    def test_POST_form(self, httpbin):
        """
        Tests submitting form data via POST using HTTPie and verifies the response contains the submitted data.
        """
        r = http('--form', 'POST', httpbin.url + '/post', 'foo=bar')
        assert HTTP_OK in r
        assert '"foo": "bar"' in r

    def test_POST_form_multiple_values(self, httpbin):
        """
        Tests that submitting multiple form values for the same key via POST results in all values being received as a list in the server's response.
        """
        r = http('--form', 'POST', httpbin.url + '/post', 'foo=bar', 'foo=baz')
        assert HTTP_OK in r
        assert r.json['form'] == {'foo': ['bar', 'baz']}

    def test_POST_stdin(self, httpbin):
        """
        Tests sending file content as form data via POST using standard input.
        
        Opens a file and submits its content as form data to the /post endpoint of the test server, simulating a non-interactive standard input environment. Asserts that the response is successful and contains the file content.
        """
        with open(FILE_PATH) as f:
            env = TestEnvironment(stdin=f, stdin_isatty=False)
            r = http('--form', 'POST', httpbin.url + '/post', env=env)
        assert HTTP_OK in r
        assert FILE_CONTENT in r

    def test_headers(self, httpbin):
        """
        Tests sending a GET request with a custom header and verifies response headers.
        
        Sends a GET request to the /headers endpoint with a custom 'Foo: bar' header and asserts that both the default 'User-Agent' and the custom header are present in the response.
        """
        r = http('GET', httpbin.url + '/headers', 'Foo:bar')
        assert HTTP_OK in r
        assert '"User-Agent": "HTTPie' in r, r
        assert '"Foo": "bar"' in r

    @pytest.mark.skipif(
        is_py26,
        reason='the `object_pairs_hook` arg for `json.loads()` is Py>2.6 only'
    )
    def test_json_input_preserve_order(self, httpbin):
        """
        Tests that JSON input preserves key order when sending a PATCH request.
        
        Sends a PATCH request with a nested JSON object to the /patch endpoint and asserts that the order of keys in the JSON data is maintained in the response.
        """
        r = http('PATCH', httpbin.url + '/patch',
                 'order:={"map":{"1":"first","2":"second"}}')
        assert HTTP_OK in r
        assert r.json['data'] == \
            '{"order": {"map": {"1": "first", "2": "second"}}}'
