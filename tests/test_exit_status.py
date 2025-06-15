import requests
import pytest

from httpie import ExitStatus
from utils import TestEnvironment, http, HTTP_OK


class TestExitStatus:
    def test_ok_response_exits_0(self, httpbin):
        """
        Verifies that a successful HTTP 200 response results in an exit status of OK.
        
        Sends a GET request to an endpoint returning HTTP 200 and asserts that the response contains the HTTP OK indicator and the exit status is ExitStatus.OK.
        """
        r = http('GET', httpbin.url + '/status/200')
        assert HTTP_OK in r
        assert r.exit_status == ExitStatus.OK

    def test_error_response_exits_0_without_check_status(self, httpbin):
        """
        Verifies that a 500 Internal Server Error response results in an exit status of OK when the status check is not enforced.
        
        Sends a GET request to an endpoint returning HTTP 500 and asserts that the response contains the expected status, the exit status is OK, and there is no standard error output.
        """
        r = http('GET', httpbin.url + '/status/500')
        assert '500 INTERNAL SERVER ERRO' in r
        assert r.exit_status == ExitStatus.OK
        assert not r.stderr

    @pytest.mark.skipif(
        tuple(map(int, requests.__version__.split('.'))) < (2, 3, 0),
        reason='timeout broken in requests prior v2.3.0 (#185)'
    )
    def test_timeout_exit_status(self, httpbin):

        """
        Tests that a request exceeding the specified timeout returns the timeout exit status.
        
        Sends a GET request with a 0.5-second timeout to an endpoint that delays for 1 second, and asserts that the exit status is `ExitStatus.ERROR_TIMEOUT`.
        """
        r = http('--timeout=0.5', 'GET', httpbin.url + '/delay/1',
                 error_exit_ok=True)
        assert r.exit_status == ExitStatus.ERROR_TIMEOUT

    def test_3xx_check_status_exits_3_and_stderr_when_stdout_redirected(
            self, httpbin):
        """
            Tests that a 301 redirect with --check-status exits with the correct status and writes the error to stderr when stdout is redirected.
            
            Simulates a non-interactive environment by redirecting stdout, sends a GET request to a 301 endpoint with status checking enabled, and verifies that the exit status is ERROR_HTTP_3XX and the error message appears in standard error output.
            """
            env = TestEnvironment(stdout_isatty=False)
        r = http('--check-status', '--headers',
                 'GET', httpbin.url + '/status/301',
                 env=env, error_exit_ok=True)
        assert '301 MOVED PERMANENTLY' in r
        assert r.exit_status == ExitStatus.ERROR_HTTP_3XX
        assert '301 moved permanently' in r.stderr.lower()

    @pytest.mark.skipif(
        requests.__version__ == '0.13.6',
        reason='Redirects with prefetch=False are broken in Requests 0.13.6')
    def test_3xx_check_status_redirects_allowed_exits_0(self, httpbin):
        """
        Tests that following a 3xx redirect with '--check-status' and '--follow' results in a successful exit status.
        
        Sends a GET request to a 301 endpoint with redirect following enabled, and asserts that the final response is HTTP 200 and the exit status is OK.
        """
        r = http('--check-status', '--follow',
                 'GET', httpbin.url + '/status/301',
                 error_exit_ok=True)
        # The redirect will be followed so 200 is expected.
        assert HTTP_OK in r
        assert r.exit_status == ExitStatus.OK

    def test_4xx_check_status_exits_4(self, httpbin):
        """
        Tests that a 401 Unauthorized response with --check-status results in the correct 4xx exit status.
        
        Verifies that the exit status is set to ERROR_HTTP_4XX and that standard error output is empty when stdout is not redirected.
        """
        r = http('--check-status', 'GET', httpbin.url + '/status/401',
                 error_exit_ok=True)
        assert '401 UNAUTHORIZED' in r
        assert r.exit_status == ExitStatus.ERROR_HTTP_4XX
        # Also stderr should be empty since stdout isn't redirected.
        assert not r.stderr

    def test_5xx_check_status_exits_5(self, httpbin):
        """
        Tests that a GET request to a 500 status endpoint with --check-status exits with ERROR_HTTP_5XX.
        
        Sends a GET request to an endpoint returning HTTP 500 with the --check-status flag enabled, and asserts that the response contains the 500 status and the exit status is set to ERROR_HTTP_5XX.
        """
        r = http('--check-status', 'GET', httpbin.url + '/status/500',
                 error_exit_ok=True)
        assert '500 INTERNAL SERVER ERROR' in r
        assert r.exit_status == ExitStatus.ERROR_HTTP_5XX
