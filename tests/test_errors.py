import mock
from pytest import raises
from requests import Request, Timeout
from requests.exceptions import ConnectionError

from httpie.core import main

error_msg = None


@mock.patch('httpie.core.get_response')
def test_error(get_response):
    """
    Tests that a ConnectionError during a GET request results in the correct exit code and error message.
    
    Simulates a ConnectionError raised by get_response and verifies that main returns exit code 1 and formats the error message as expected.
    """
    def error(msg, *args, **kwargs):
        global error_msg
        error_msg = msg % args

    exc = ConnectionError('Connection aborted')
    exc.request = Request(method='GET', url='http://www.google.com')
    get_response.side_effect = exc
    ret = main(['--ignore-stdin', 'www.google.com'], error=error)
    assert ret == 1
    assert error_msg == (
        'ConnectionError: '
        'Connection aborted while doing GET request to URL: '
        'http://www.google.com')


@mock.patch('httpie.core.get_response')
def test_error_traceback(get_response):
    """
    Tests that a ConnectionError raised by get_response is propagated when the --traceback flag is used.
    
    Verifies that main does not suppress the exception and allows it to be raised, enabling traceback output.
    """
    exc = ConnectionError('Connection aborted')
    exc.request = Request(method='GET', url='http://www.google.com')
    get_response.side_effect = exc
    with raises(ConnectionError):
        ret = main(['--ignore-stdin', '--traceback', 'www.google.com'])


@mock.patch('httpie.core.get_response')
def test_timeout(get_response):
    """
    Tests that a Timeout exception from get_response results in the correct exit code and error message.
    
    Simulates a timeout during an HTTP GET request and verifies that main returns exit code 2 and formats the timeout error message as expected.
    """
    def error(msg, *args, **kwargs):
        global error_msg
        error_msg = msg % args

    exc = Timeout('Request timed out')
    exc.request = Request(method='GET', url='http://www.google.com')
    get_response.side_effect = exc
    ret = main(['--ignore-stdin', 'www.google.com'], error=error)
    assert ret == 2
    assert error_msg == 'Request timed out (30s).'
