"""Miscellaneous regression tests"""
import pytest

from utils import http, HTTP_OK
from httpie.compat import is_windows


def test_Host_header_overwrite(httpbin):
    """
    Tests that the Host header can be explicitly set in an HTTP request.
    
    Sends a GET request to the httpbin service with a custom Host header and verifies that the response contains the HTTP OK status, the Host header appears exactly once, and its value matches the specified host.
    """
    host = 'httpbin.org'
    url = httpbin.url + '/get'
    r = http('--print=hH', url, 'host:{0}'.format(host))
    assert HTTP_OK in r
    assert r.lower().count('host:') == 1
    assert 'host: {0}'.format(host) in r


@pytest.mark.skipif(is_windows, reason='Unix-only')
def test_output_devnull(httpbin):
    """
    https://github.com/jkbrzt/httpie/issues/252

    """
    http('--output=/dev/null', httpbin + '/get')
