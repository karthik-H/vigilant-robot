import os

import pytest

from httpie.input import ParseError
from utils import TestEnvironment, http, HTTP_OK
from fixtures import FILE_PATH_ARG, FILE_PATH, FILE_CONTENT


class TestMultipartFormDataFileUpload:

    def test_non_existent_file_raises_parse_error(self, httpbin):
        """
        Tests that uploading a non-existent file as a form field raises a ParseError.
        """
        with pytest.raises(ParseError):
            http('--form',
                 'POST', httpbin.url + '/post', 'foo@/__does_not_exist__')

    def test_upload_ok(self, httpbin):
        """
        Tests successful multipart form-data file upload via HTTP POST.
        
        Sends a POST request with a file and a form field, then asserts that the response contains HTTP 200 OK, correct Content-Disposition headers for both the form field and file (including filename), the file content, the form field value, and the file's content type.
        """
        r = http('--form', '--verbose', 'POST', httpbin.url + '/post',
                 'test-file@%s' % FILE_PATH_ARG, 'foo=bar')
        assert HTTP_OK in r
        assert 'Content-Disposition: form-data; name="foo"' in r
        assert 'Content-Disposition: form-data; name="test-file";' \
               ' filename="%s"' % os.path.basename(FILE_PATH) in r
        assert FILE_CONTENT in r
        assert '"foo": "bar"' in r
        assert 'Content-Type: text/plain' in r

    def test_upload_multiple_fields_with_the_same_name(self, httpbin):
        """
        Tests uploading multiple files with the same form field name in a multipart form-data POST request.
        
        Asserts that the response contains two Content-Disposition headers for the repeated field name, the expected number of file content occurrences, and two Content-Type headers for the files.
        """
        r = http('--form', '--verbose', 'POST', httpbin.url + '/post',
                 'test-file@%s' % FILE_PATH_ARG,
                 'test-file@%s' % FILE_PATH_ARG)
        assert HTTP_OK in r
        assert r.count('Content-Disposition: form-data; name="test-file";'
                       ' filename="%s"' % os.path.basename(FILE_PATH)) == 2
        # Should be 4, but is 3 because httpbin
        # doesn't seem to support filed field lists
        assert r.count(FILE_CONTENT) in [3, 4]
        assert r.count('Content-Type: text/plain') == 2


class TestRequestBodyFromFilePath:
    """
    `http URL @file'

    """

    def test_request_body_from_file_by_path(self, httpbin):
        """
        Tests posting a file's contents as the HTTP request body using the @file syntax.
        
        Asserts that the response is HTTP 200 OK, contains the file content, and includes the correct Content-Type header.
        """
        r = http('--verbose',
                 'POST', httpbin.url + '/post', '@' + FILE_PATH_ARG)
        assert HTTP_OK in r
        assert FILE_CONTENT in r, r
        assert '"Content-Type": "text/plain"' in r

    def test_request_body_from_file_by_path_with_explicit_content_type(
            self, httpbin):
        """
            Tests posting a file as the HTTP request body with an explicit Content-Type header.
            
            Verifies that the response is HTTP 200 OK, the file content is present in the response, and the specified Content-Type header is correctly set.
            """
            r = http('--verbose',
                 'POST', httpbin.url + '/post', '@' + FILE_PATH_ARG,
                 'Content-Type:text/plain; charset=utf8')
        assert HTTP_OK in r
        assert FILE_CONTENT in r
        assert 'Content-Type: text/plain; charset=utf8' in r

    def test_request_body_from_file_by_path_no_field_name_allowed(
            self, httpbin):
        """
            Tests that specifying a field name when sending a file as the request body results in an error.
            
            Asserts that the error message suggests using the --form option instead.
            """
            env = TestEnvironment(stdin_isatty=True)
        r = http('POST', httpbin.url + '/post', 'field-name@' + FILE_PATH_ARG,
                 env=env, error_exit_ok=True)
        assert 'perhaps you meant --form?' in r.stderr

    def test_request_body_from_file_by_path_no_data_items_allowed(
            self, httpbin):
        """
            Verifies that sending a file as the request body while also including form data results in an error.
            
            Asserts that the error message indicates mixing file body input with additional data items is not allowed.
            """
            env = TestEnvironment(stdin_isatty=False)
        r = http('POST', httpbin.url + '/post', '@' + FILE_PATH_ARG, 'foo=bar',
                 env=env, error_exit_ok=True)
        assert 'cannot be mixed' in r.stderr
