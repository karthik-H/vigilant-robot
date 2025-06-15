"""HTTP authentication-related tests."""
import requests
import pytest

from utils import http, add_auth, HTTP_OK, TestEnvironment
import httpie.input
import httpie.cli


class TestAuth:
    def test_basic_auth(self, httpbin):
        """
        Tests HTTP Basic Authentication using the httpie CLI.
        
        Sends a GET request with basic auth credentials to an endpoint requiring authentication and asserts that the response indicates successful authentication for the specified user.
        """
        r = http('--auth=user:password',
                 'GET', httpbin.url + '/basic-auth/user/password')
        assert HTTP_OK in r
        assert r.json == {'authenticated': True, 'user': 'user'}

    @pytest.mark.skipif(
        requests.__version__ == '0.13.6',
        reason='Redirects with prefetch=False are broken in Requests 0.13.6')
    def test_digest_auth(self, httpbin):
        """
        Tests HTTP Digest Authentication using the CLI with the --auth-type=digest flag.
        
        Sends a GET request to a digest-auth protected endpoint and asserts that authentication succeeds and the correct user is returned in the response.
        """
        r = http('--auth-type=digest', '--auth=user:password',
                 'GET', httpbin.url + '/digest-auth/auth/user/password')
        assert HTTP_OK in r
        assert r.json == {'authenticated': True, 'user': 'user'}

    def test_password_prompt(self, httpbin):
        """
        Tests that the password prompt is correctly handled when only a username is provided with the --auth flag.
        
        Simulates user input for the password prompt and verifies successful HTTP Basic Authentication.
        """
        httpie.input.AuthCredentials._getpass = lambda self, prompt: 'password'
        r = http('--auth', 'user',
                 'GET', httpbin.url + '/basic-auth/user/password')
        assert HTTP_OK in r
        assert r.json == {'authenticated': True, 'user': 'user'}

    def test_credentials_in_url(self, httpbin):
        """
        Tests that credentials embedded in the URL are used for HTTP Basic Authentication.
        
        Sends a GET request to a basic-auth endpoint with credentials included in the URL and asserts that authentication succeeds and the correct user is returned in the response.
        """
        url = add_auth(httpbin.url + '/basic-auth/user/password',
                       auth='user:password')
        r = http('GET', url)
        assert HTTP_OK in r
        assert r.json == {'authenticated': True, 'user': 'user'}

    def test_credentials_in_url_auth_flag_has_priority(self, httpbin):
        """
        Tests that credentials provided via the --auth flag take precedence over those in the URL.
        
        Sends a GET request to a basic-auth endpoint with incorrect credentials in the URL and correct credentials via the --auth flag, asserting successful authentication with the correct user.
        """
        url = add_auth(httpbin.url + '/basic-auth/user/password',
                       auth='user:wrong')
        r = http('--auth=user:password', 'GET', url)
        assert HTTP_OK in r
        assert r.json == {'authenticated': True, 'user': 'user'}

    @pytest.mark.parametrize('url', [
        'username@example.org',
        'username:@example.org',
    ])
    def test_only_username_in_url(self, url):
        """
        Tests that URLs containing only a username are parsed with the username set and an empty password.
        
        Verifies that when a URL includes only a username (with or without a trailing colon), the authentication object is created with the correct username and an empty password.
        """
        args = httpie.cli.parser.parse_args(args=[url], env=TestEnvironment())
        assert args.auth
        assert args.auth.key == 'username'
        assert args.auth.value == ''
