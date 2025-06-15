# coding=utf-8
"""
Various unicode handling related tests.

"""
from utils import http, HTTP_OK
from fixtures import UNICODE


class TestUnicode:

    def test_unicode_headers(self, httpbin):
        # httpbin doesn't interpret utf8 headers
        r = http(httpbin.url + '/headers', u'Test:%s' % UNICODE)
        assert HTTP_OK in r

    def test_unicode_headers_verbose(self, httpbin):
        # httpbin doesn't interpret utf8 headers
        r = http('--verbose', httpbin.url + '/headers', u'Test:%s' % UNICODE)
        assert HTTP_OK in r
        assert UNICODE in r

    def test_unicode_form_item(self, httpbin):
        """
        Tests that a POST request with a Unicode form field is correctly processed.
        
        Sends a form-encoded POST request containing a Unicode value and asserts that the response status is HTTP_OK and the returned form data matches the Unicode input.
        """
        r = http('--form', 'POST', httpbin.url + '/post', u'test=%s' % UNICODE)
        assert HTTP_OK in r
        assert r.json['form'] == {'test': UNICODE}

    def test_unicode_form_item_verbose(self, httpbin):
        """
        Tests sending a Unicode form field with verbose output in an HTTP POST request.
        
        Asserts that the response indicates success and that the Unicode string is present in the verbose output.
        """
        r = http('--verbose', '--form',
                 'POST', httpbin.url + '/post', u'test=%s' % UNICODE)
        assert HTTP_OK in r
        assert UNICODE in r

    def test_unicode_json_item(self, httpbin):
        """
        Tests sending a POST request with Unicode JSON data and verifies correct handling in the response.
        
        Sends a JSON payload containing a Unicode value to the /post endpoint and asserts that the response includes the expected Unicode data.
        """
        r = http('--json', 'POST', httpbin.url + '/post', u'test=%s' % UNICODE)
        assert HTTP_OK in r
        assert r.json['json'] == {'test': UNICODE}

    def test_unicode_json_item_verbose(self, httpbin):
        """
        Tests sending a POST request with Unicode JSON data and verbose output.
        
        Verifies that the response contains an HTTP OK status and the Unicode string is present in the verbose output.
        """
        r = http('--verbose', '--json',
                 'POST', httpbin.url + '/post', u'test=%s' % UNICODE)
        assert HTTP_OK in r
        assert UNICODE in r

    def test_unicode_raw_json_item(self, httpbin):
        """
        Tests sending a POST request with raw JSON containing Unicode keys and values.
        
        Verifies that the server correctly receives and returns a nested JSON structure with Unicode content.
        """
        r = http('--json', 'POST', httpbin.url + '/post',
                 u'test:={ "%s" : [ "%s" ] }' % (UNICODE, UNICODE))
        assert HTTP_OK in r
        assert r.json['json'] == {'test': {UNICODE: [UNICODE]}}

    def test_unicode_raw_json_item_verbose(self, httpbin):
        """
        Tests sending raw JSON with nested Unicode keys and values in verbose mode.
        
        Sends a POST request with a raw JSON payload containing Unicode data to the /post endpoint, then asserts that the response is successful and the nested Unicode structure is preserved in the returned JSON.
        """
        r = http('--json', 'POST', httpbin.url + '/post',
                 u'test:={ "%s" : [ "%s" ] }' % (UNICODE, UNICODE))
        assert HTTP_OK in r
        assert r.json['json'] == {'test': {UNICODE: [UNICODE]}}

    def test_unicode_url_query_arg_item(self, httpbin):
        """
        Tests sending a Unicode query parameter in a GET request.
        
        Asserts that the server correctly receives and returns the Unicode value in the query arguments of the JSON response.
        """
        r = http(httpbin.url + '/get', u'test==%s' % UNICODE)
        assert HTTP_OK in r
        assert r.json['args'] == {'test': UNICODE}, r

    def test_unicode_url_query_arg_item_verbose(self, httpbin):
        r = http('--verbose', httpbin.url + '/get', u'test==%s' % UNICODE)
        assert HTTP_OK in r
        assert UNICODE in r

    def test_unicode_url(self, httpbin):
        r = http(httpbin.url + u'/get?test=' + UNICODE)
        assert HTTP_OK in r
        assert r.json['args'] == {'test': UNICODE}

    # def test_unicode_url_verbose(self):
    #     r = http(httpbin.url + '--verbose', u'/get?test=' + UNICODE)
    #     assert HTTP_OK in r

    def test_unicode_basic_auth(self, httpbin):
        # it doesn't really authenticate us because httpbin
        # doesn't interpret the utf8-encoded auth
        http('--verbose', '--auth', u'test:%s' % UNICODE,
             httpbin.url + u'/basic-auth/test/' + UNICODE)

    def test_unicode_digest_auth(self, httpbin):
        # it doesn't really authenticate us because httpbin
        # doesn't interpret the utf8-encoded auth
        """
        Tests sending a request with Unicode credentials using digest authentication.
        
        This test verifies that a request with Unicode characters in the username or password
        can be sent using digest authentication. No assertions are made, as the test server
        does not interpret UTF-8 encoded authentication credentials.
        """
        http('--auth-type=digest',
             '--auth', u'test:%s' % UNICODE,
             httpbin.url + u'/digest-auth/auth/test/' + UNICODE)
