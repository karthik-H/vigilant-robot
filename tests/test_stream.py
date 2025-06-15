import pytest

from httpie.compat import is_windows
from httpie.output.streams import BINARY_SUPPRESSED_NOTICE
from utils import http, TestEnvironment
from fixtures import BIN_FILE_CONTENT, BIN_FILE_PATH


class TestStream:
    # GET because httpbin 500s with binary POST body.

    @pytest.mark.skipif(is_windows,
                        reason='Pretty redirect not supported under Windows')
    def test_pretty_redirected_stream(self, httpbin):
        """
        Tests that streaming a binary file with prettified output and redirected streams displays the binary suppressed notice.
        
        Simulates a non-interactive terminal environment and verifies that the binary content is not shown, but the suppression notice appears in the output when using `--stream` and `--pretty=all`.
        """
        with open(BIN_FILE_PATH, 'rb') as f:
            env = TestEnvironment(colors=256, stdin=f,
                                  stdin_isatty=False,
                                  stdout_isatty=False)
            r = http('--verbose', '--pretty=all', '--stream', 'GET',
                     httpbin.url + '/get', env=env)
        assert BINARY_SUPPRESSED_NOTICE.decode() in r

    def test_encoded_stream(self, httpbin):
        """
        Tests that streaming a binary file with non-prettified output correctly suppresses binary content in the redirected terminal output.
        
        Verifies that the binary suppression notice appears in the response when using the `--stream` and `--pretty=none` options.
        """
        with open(BIN_FILE_PATH, 'rb') as f:
            env = TestEnvironment(stdin=f, stdin_isatty=False)
            r = http('--pretty=none', '--stream', '--verbose', 'GET',
                     httpbin.url + '/get', env=env)
        assert BINARY_SUPPRESSED_NOTICE.decode() in r

    def test_redirected_stream(self, httpbin):
        """
        Tests that the --stream option outputs binary content correctly when both stdin and stdout are redirected and pretty-printing is disabled.
        
        Verifies that the actual binary file content appears in the response output under these terminal conditions.
        """
        with open(BIN_FILE_PATH, 'rb') as f:
            env = TestEnvironment(stdout_isatty=False,
                                  stdin_isatty=False,
                                  stdin=f)
            r = http('--pretty=none', '--stream', '--verbose', 'GET',
                     httpbin.url + '/get', env=env)
        assert BIN_FILE_CONTENT in r
