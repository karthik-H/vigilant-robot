import os

import pytest
import pytest_httpbin.certs
from requests.exceptions import SSLError

from httpie import ExitStatus
from utils import http, HTTP_OK, TESTS_ROOT


CLIENT_CERT = os.path.join(TESTS_ROOT, 'client_certs', 'client.crt')
CLIENT_KEY = os.path.join(TESTS_ROOT, 'client_certs', 'client.key')
CLIENT_PEM = os.path.join(TESTS_ROOT, 'client_certs', 'client.pem')

# We test against a local httpbin instance which uses a self-signed cert.
# Requests without --verify=<CA_BUNDLE> will fail with a verification error.
# See: https://github.com/kevin1024/pytest-httpbin#https-support
CA_BUNDLE = pytest_httpbin.certs.where()


class TestClientSSLCertHandling(object):

    def test_cert_file_not_found(self, httpbin_secure):
        """
        Tests that specifying a non-existent client certificate file results in an error.
        
        Sends a request with a missing certificate file path and asserts that the command exits with an error and the standard error output contains the appropriate file not found message.
        """
        r = http(httpbin_secure + '/get',
                 '--verify', CA_BUNDLE,
                 '--cert', '/__not_found__',
                 error_exit_ok=True)
        assert r.exit_status == ExitStatus.ERROR
        assert 'No such file or directory' in r.stderr

    def test_cert_file_invalid(self, httpbin_secure):
        """
        Tests that using an invalid client certificate file raises an SSLError.
        
        Attempts to authenticate with a certificate file that is not a valid certificate, expecting the SSL handshake to fail.
        """
        with pytest.raises(SSLError):
            http(httpbin_secure + '/get',
                 '--verify', CA_BUNDLE,
                 '--cert', __file__)

    def test_cert_ok_but_missing_key(self, httpbin_secure):
        """
        Tests that providing a client certificate without the corresponding private key raises an SSLError.
        """
        with pytest.raises(SSLError):
            http(httpbin_secure + '/get',
                 '--verify', CA_BUNDLE,
                 '--cert', CLIENT_CERT)

    def test_cert_and_key(self, httpbin_secure):
        """
        Tests that providing both a valid client certificate and its corresponding private key allows a successful HTTPS request to a server requiring client authentication.
        """
        r = http(httpbin_secure + '/get',
                 '--verify', CA_BUNDLE,
                 '--cert', CLIENT_CERT,
                 '--cert-key', CLIENT_KEY)
        assert HTTP_OK in r

    def test_cert_pem(self, httpbin_secure):
        """
        Tests that providing a combined PEM file containing both client certificate and key allows a successful HTTPS request to a server with a custom CA bundle.
        """
        r = http(httpbin_secure + '/get',
                 '--verify', CA_BUNDLE,
                 '--cert', CLIENT_PEM)
        assert HTTP_OK in r


class TestServerSSLCertHandling(object):

    def test_self_signed_server_cert_by_default_raises_ssl_error(
            self, httpbin_secure):
        """
            Tests that connecting to a server with a self-signed SSL certificate without specifying verification options raises an SSLError.
            """
            with pytest.raises(SSLError):
            http(httpbin_secure.url + '/get')

    def test_verify_no_OK(self, httpbin_secure):
        """
        Tests that disabling SSL verification allows a request to a server with a self-signed certificate to succeed.
        
        Asserts that the HTTP response indicates a successful request when the `--verify=no` option is used.
        """
        r = http(httpbin_secure.url + '/get', '--verify=no')
        assert HTTP_OK in r

    def test_verify_custom_ca_bundle_path(
            self, httpbin_secure):
        """
            Tests that specifying a custom CA bundle path allows successful SSL verification.
            
            Sends a request to the secure server using the provided CA bundle for certificate verification and asserts that the response indicates a successful HTTP request.
            """
            r = http(httpbin_secure.url + '/get', '--verify', CA_BUNDLE)
        assert HTTP_OK in r

    def test_verify_custom_ca_bundle_invalid_path(self, httpbin_secure):
        """
        Tests that specifying a non-existent CA bundle path for SSL verification raises an SSLError.
        """
        with pytest.raises(SSLError):
            http(httpbin_secure.url + '/get', '--verify', '/__not_found__')

    def test_verify_custom_ca_bundle_invalid_bundle(self, httpbin_secure):
        """
        Tests that specifying an invalid CA bundle file for SSL verification raises an SSLError.
        
        Attempts to verify the server's SSL certificate using a file that is not a valid CA bundle,
        expecting the request to fail with an SSLError.
        """
        with pytest.raises(SSLError):
            http(httpbin_secure.url + '/get', '--verify', __file__)
