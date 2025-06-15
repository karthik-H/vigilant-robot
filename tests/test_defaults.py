"""
Tests for the provided defaults regarding HTTP method, and --json vs. --form.

"""
from utils import TestEnvironment, http, HTTP_OK, no_content_type
from fixtures import FILE_PATH


class TestImplicitHTTPMethod:
    def test_implicit_GET(self, httpbin):
        r = http(httpbin.url + '/get')
        assert HTTP_OK in r

    def test_implicit_GET_with_headers(self, httpbin):
        """
        Sends a GET request with a custom header and verifies the header is present in the response.
        
        Confirms that the server receives and returns the custom header as expected.
        """
        r = http(httpbin.url + '/headers', 'Foo:bar')
        assert HTTP_OK in r
        assert r.json['headers']['Foo'] == 'bar'

    def test_implicit_POST_json(self, httpbin):
        """
        Tests that sending data without the --form flag results in a POST request with a JSON payload.
        
        Verifies that the response contains the expected JSON data.
        """
        r = http(httpbin.url + '/post', 'hello=world')
        assert HTTP_OK in r
        assert r.json['json'] == {'hello': 'world'}

    def test_implicit_POST_form(self, httpbin):
        """
        Tests that sending data with the --form flag results in a POST request with form-encoded data.
        
        Verifies that the response contains the expected form data in the JSON body.
        """
        r = http('--form', httpbin.url + '/post', 'foo=bar')
        assert HTTP_OK in r
        assert r.json['form'] == {'foo': 'bar'}

    def test_implicit_POST_stdin(self, httpbin):
        """
        Tests that sending form data via stdin with --form results in a successful POST request.
        
        Reads form data from a file using non-interactive stdin, submits it to the /post endpoint with the --form flag, and verifies that the response indicates a successful HTTP 200 OK status.
        """
        with open(FILE_PATH) as f:
            env = TestEnvironment(stdin_isatty=False, stdin=f)
            r = http('--form', httpbin.url + '/post', env=env)
        assert HTTP_OK in r


class TestAutoContentTypeAndAcceptHeaders:
    """
    Test that Accept and Content-Type correctly defaults to JSON,
    but can still be overridden. The same with Content-Type when --form
    -f is used.

    """

    def test_GET_no_data_no_auto_headers(self, httpbin):
        # https://github.com/jkbrzt/httpie/issues/62
        """
        Tests that a GET request without data does not automatically set JSON headers.
        
        Verifies that the 'Accept' header defaults to '*/*' and that no 'Content-Type' header is present in the request.
        """
        r = http('GET', httpbin.url + '/headers')
        assert HTTP_OK in r
        assert r.json['headers']['Accept'] == '*/*'
        assert no_content_type(r.json['headers'])

    def test_POST_no_data_no_auto_headers(self, httpbin):
        # JSON headers shouldn't be automatically set for POST with no data.
        """
        Verifies that a POST request without data does not automatically set JSON headers.
        
        Ensures that the `Accept` header defaults to `*/*` and that the `Content-Type: application/json` header is not present in the response.
        """
        r = http('POST', httpbin.url + '/post')
        assert HTTP_OK in r
        assert '"Accept": "*/*"' in r
        assert '"Content-Type": "application/json' not in r

    def test_POST_with_data_auto_JSON_headers(self, httpbin):
        """
        Tests that sending data in a POST request automatically sets the Accept and Content-Type headers to application/json.
        
        Verifies that when data is included in a POST request, the client sets both the Accept and Content-Type headers to application/json in the outgoing request.
        """
        r = http('POST', httpbin.url + '/post', 'a=b')
        assert HTTP_OK in r
        assert '"Accept": "application/json"' in r
        assert '"Content-Type": "application/json' in r

    def test_GET_with_data_auto_JSON_headers(self, httpbin):
        # JSON headers should automatically be set also for GET with data.
        """
        Tests that sending data with a GET request automatically sets JSON headers.
        
        Verifies that when data is included in a GET request, the client sets both the `Accept` and `Content-Type` headers to `application/json`.
        """
        r = http('POST', httpbin.url + '/post', 'a=b')
        assert HTTP_OK in r
        assert '"Accept": "application/json"' in r, r
        assert '"Content-Type": "application/json' in r

    def test_POST_explicit_JSON_auto_JSON_accept(self, httpbin):
        """
        Tests that using the --json flag with a POST request sets both Accept and Content-Type headers to application/json, even when no data is provided.
        """
        r = http('--json', 'POST', httpbin.url + '/post')
        assert HTTP_OK in r
        assert r.json['headers']['Accept'] == 'application/json'
        # Make sure Content-Type gets set even with no data.
        # https://github.com/jkbrzt/httpie/issues/137
        assert 'application/json' in r.json['headers']['Content-Type']

    def test_GET_explicit_JSON_explicit_headers(self, httpbin):
        """
        Tests that explicit Accept and Content-Type headers override defaults when using the --json flag in a GET request.
        
        Sends a GET request with the --json flag and explicit Accept and Content-Type headers set to 'application/xml', verifying that the response reflects these header values.
        """
        r = http('--json', 'GET', httpbin.url + '/headers',
                 'Accept:application/xml',
                 'Content-Type:application/xml')
        assert HTTP_OK in r
        assert '"Accept": "application/xml"' in r
        assert '"Content-Type": "application/xml"' in r

    def test_POST_form_auto_Content_Type(self, httpbin):
        """
        Verifies that a POST request with the --form flag automatically sets the Content-Type header to application/x-www-form-urlencoded.
        """
        r = http('--form', 'POST', httpbin.url + '/post')
        assert HTTP_OK in r
        assert '"Content-Type": "application/x-www-form-urlencoded' in r

    def test_POST_form_Content_Type_override(self, httpbin):
        """
        Tests that an explicit Content-Type header overrides the default when sending form data in a POST request.
        
        Verifies that specifying 'Content-Type:application/xml' with the --form flag results in the request using 'application/xml' as the Content-Type header.
        """
        r = http('--form', 'POST', httpbin.url + '/post',
                 'Content-Type:application/xml')
        assert HTTP_OK in r
        assert '"Content-Type": "application/xml"' in r

    def test_print_only_body_when_stdout_redirected_by_default(self, httpbin):
        """
        Verifies that only the response body is printed when stdout is redirected.
        
        Ensures that when standard output is not a TTY (e.g., redirected to a file), the HTTP status line is omitted from the output.
        """
        env = TestEnvironment(stdin_isatty=True, stdout_isatty=False)
        r = http('GET', httpbin.url + '/get', env=env)
        assert 'HTTP/' not in r

    def test_print_overridable_when_stdout_redirected(self, httpbin):
        """
        Verifies that HTTP headers are printed when stdout is redirected and the print option is set.
        
        Ensures that when standard output is not a TTY and the `--print=h` flag is used, the HTTP response headers are included in the output.
        """
        env = TestEnvironment(stdin_isatty=True, stdout_isatty=False)
        r = http('--print=h', 'GET', httpbin.url + '/get', env=env)
        assert HTTP_OK in r
