# coding=utf-8
import os
import shutil
import sys
from tempfile import gettempdir

import pytest

from httpie.plugins.builtin import HTTPBasicAuth
from utils import TestEnvironment, mk_config_dir, http, HTTP_OK, \
    no_content_type
from fixtures import UNICODE


class SessionTestBase(object):

    def start_session(self, httpbin):
        """
        Creates a unique configuration directory for the test session.
        
        Initializes a new config directory for session-related test isolation.
        """
        self.config_dir = mk_config_dir()

    def teardown_method(self, method):
        """
        Removes the temporary configuration directory after each test to ensure cleanup.
        """
        shutil.rmtree(self.config_dir)

    def env(self):
        """
        Creates a test environment configured to use the current test's config directory.
        
        Returns:
            TestEnvironment: An environment instance that enables session file reuse within the test.
        """
        return TestEnvironment(config_dir=self.config_dir)


class TestSessionFlow(SessionTestBase):
    """
    These tests start with an existing session created in `setup_method()`.

    """

    def start_session(self, httpbin):
        """
        Initializes a session with a custom header, HTTP Basic authentication, and a response cookie.
        
        Starts a session named "test" by sending a GET request that sets a cookie, includes a custom header, and uses HTTP Basic Auth credentials. Asserts that the response status is HTTP OK.
        """
        super(TestSessionFlow, self).start_session(httpbin)
        r1 = http('--follow', '--session=test', '--auth=username:password',
                  'GET', httpbin.url + '/cookies/set?hello=world',
                  'Hello:World',
                  env=self.env())
        assert HTTP_OK in r1

    def test_session_created_and_reused(self, httpbin):
        """
        Tests that a session is created and reused, preserving headers, cookies, and authorization.
        
        Starts a session, sends a request using the session, and verifies that the custom header, cookie, and authorization header are present in the response, confirming session persistence.
        """
        self.start_session(httpbin)
        # Verify that the session created in setup_method() has been used.
        r2 = http('--session=test',
                  'GET', httpbin.url + '/get', env=self.env())
        assert HTTP_OK in r2
        assert r2.json['headers']['Hello'] == 'World'
        assert r2.json['headers']['Cookie'] == 'hello=world'
        assert 'Basic ' in r2.json['headers']['Authorization']

    def test_session_update(self, httpbin):
        """
        Tests that session data is updated when making requests with modified headers, cookies, and authentication.
        
        Starts with an existing session, modifies its data via a request, and verifies that subsequent requests reflect the updated session state.
        """
        self.start_session(httpbin)
        # Get a response to a request from the original session.
        r2 = http('--session=test', 'GET', httpbin.url + '/get',
                  env=self.env())
        assert HTTP_OK in r2

        # Make a request modifying the session data.
        r3 = http('--follow', '--session=test', '--auth=username:password2',
                  'GET', httpbin.url + '/cookies/set?hello=world2',
                  'Hello:World2',
                  env=self.env())
        assert HTTP_OK in r3

        # Get a response to a request from the updated session.
        r4 = http('--session=test', 'GET', httpbin.url + '/get',
                  env=self.env())
        assert HTTP_OK in r4
        assert r4.json['headers']['Hello'] == 'World2'
        assert r4.json['headers']['Cookie'] == 'hello=world2'
        assert (r2.json['headers']['Authorization'] !=
                r4.json['headers']['Authorization'])

    def test_session_read_only(self, httpbin):
        """
        Verifies that session data remains unchanged when using the --session-read-only flag.
        
        This test ensures that making a request with --session-read-only does not update the session file, even if the request would otherwise modify session data such as cookies, headers, or authentication.
        """
        self.start_session(httpbin)
        # Get a response from the original session.
        r2 = http('--session=test', 'GET', httpbin.url + '/get',
                  env=self.env())
        assert HTTP_OK in r2

        # Make a request modifying the session data but
        # with --session-read-only.
        r3 = http('--follow', '--session-read-only=test',
                  '--auth=username:password2', 'GET',
                  httpbin.url + '/cookies/set?hello=world2', 'Hello:World2',
                  env=self.env())
        assert HTTP_OK in r3

        # Get a response from the updated session.
        r4 = http('--session=test', 'GET', httpbin.url + '/get',
                  env=self.env())
        assert HTTP_OK in r4

        # Origin can differ on Travis.
        del r2.json['origin'], r4.json['origin']
        # Different for each request.

        # Should be the same as before r3.
        assert r2.json == r4.json


class TestSession(SessionTestBase):
    """Stand-alone session tests."""

    def test_session_ignored_header_prefixes(self, httpbin):
        """
        Verifies that headers with ignored prefixes are not persisted in session files.
        
        Starts a session and sends a request with `Content-Type` and `If-Unmodified-Since` headers, then checks that these headers are not present in subsequent requests using the same session.
        """
        self.start_session(httpbin)
        r1 = http('--session=test', 'GET', httpbin.url + '/get',
                  'Content-Type: text/plain',
                  'If-Unmodified-Since: Sat, 29 Oct 1994 19:43:31 GMT',
                  env=self.env())
        assert HTTP_OK in r1
        r2 = http('--session=test', 'GET', httpbin.url + '/get',
                  env=self.env())
        assert HTTP_OK in r2
        assert no_content_type(r2.json['headers'])
        assert 'If-Unmodified-Since' not in r2.json['headers']

    def test_session_by_path(self, httpbin):
        """
        Verifies that a session file specified by path preserves custom headers across requests.
        
        Starts a session using an explicit session file path, sends a request with a custom header, and checks that the header is retained in subsequent requests using the same session file.
        """
        self.start_session(httpbin)
        session_path = os.path.join(self.config_dir, 'session-by-path.json')
        r1 = http('--session=' + session_path, 'GET', httpbin.url + '/get',
                  'Foo:Bar', env=self.env())
        assert HTTP_OK in r1

        r2 = http('--session=' + session_path, 'GET', httpbin.url + '/get',
                  env=self.env())
        assert HTTP_OK in r2
        assert r2.json['headers']['Foo'] == 'Bar'

    @pytest.mark.skipif(
        sys.version_info >= (3,),
        reason="This test fails intermittently on Python 3 - "
               "see https://github.com/jkbrzt/httpie/issues/282")
    def test_session_unicode(self, httpbin):
        """
        Tests that sessions correctly handle Unicode credentials and headers.
        
        Starts a session with Unicode values in the Authorization header and a custom header, then verifies that these Unicode values are preserved and correctly represented in subsequent session requests.
        """
        self.start_session(httpbin)

        r1 = http('--session=test', u'--auth=test:' + UNICODE,
                  'GET', httpbin.url + '/get', u'Test:%s' % UNICODE,
                  env=self.env())
        assert HTTP_OK in r1

        r2 = http('--session=test', '--verbose', 'GET',
                  httpbin.url + '/get', env=self.env())
        assert HTTP_OK in r2

        # FIXME: Authorization *sometimes* is not present on Python3
        assert (r2.json['headers']['Authorization']
                == HTTPBasicAuth.make_header(u'test', UNICODE))
        # httpbin doesn't interpret utf8 headers
        assert UNICODE in r2

    def test_session_default_header_value_overwritten(self, httpbin):
        """
        Verifies that a custom User-Agent header set in a session persists across subsequent requests.
        
        Ensures that when a session is created with a custom User-Agent header, this value overwrites the default and remains unchanged in future requests using the same session.
        """
        self.start_session(httpbin)
        # https://github.com/jkbrzt/httpie/issues/180
        r1 = http('--session=test',
                  httpbin.url + '/headers', 'User-Agent:custom',
                  env=self.env())
        assert HTTP_OK in r1
        assert r1.json['headers']['User-Agent'] == 'custom'

        r2 = http('--session=test', httpbin.url + '/headers', env=self.env())
        assert HTTP_OK in r2
        assert r2.json['headers']['User-Agent'] == 'custom'

    def test_download_in_session(self, httpbin):
        # https://github.com/jkbrzt/httpie/issues/412
        """
        Verifies that file downloads can be performed within an HTTP session context.
        
        This test ensures that using the `--download` flag with an active session does not cause errors, confirming compatibility between session management and file download functionality.
        """
        self.start_session(httpbin)
        cwd = os.getcwd()
        try:
            os.chdir(gettempdir())
            http('--session=test', '--download',
                 httpbin.url + '/get', env=self.env())
        finally:
            os.chdir(cwd)
