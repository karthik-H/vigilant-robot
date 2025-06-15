from base64 import b64encode

import requests.auth

from httpie.plugins.base import AuthPlugin


class BuiltinAuthPlugin(AuthPlugin):

    package_name = '(builtin)'


class HTTPBasicAuth(requests.auth.HTTPBasicAuth):

    def __call__(self, r):
        """
        Adds a Basic Authorization header with Unicode support to the HTTP request.
        
        Overrides the default serialization to allow Unicode characters in the username and password.
        """
        r.headers['Authorization'] = type(self).make_header(
            self.username, self.password).encode('latin1')
        return r

    @staticmethod
    def make_header(username, password):
        """
        Generates a Basic HTTP authentication header value for the given credentials.
        
        Args:
            username: The username for authentication.
            password: The password for authentication.
        
        Returns:
            A string suitable for use as the value of the HTTP 'Authorization' header using Basic authentication.
        """
        credentials = u'%s:%s' % (username, password)
        token = b64encode(credentials.encode('utf8')).strip().decode('latin1')
        return 'Basic %s' % token


class BasicAuthPlugin(BuiltinAuthPlugin):

    name = 'Basic HTTP auth'
    auth_type = 'basic'

    def get_auth(self, username, password):
        """
        Returns an HTTPBasicAuth instance configured with the provided username and password.
        
        Args:
            username: The username for HTTP Basic authentication.
            password: The password for HTTP Basic authentication.
        
        Returns:
            An HTTPBasicAuth object for use with HTTP requests.
        """
        return HTTPBasicAuth(username, password)


class DigestAuthPlugin(BuiltinAuthPlugin):

    name = 'Digest HTTP auth'
    auth_type = 'digest'

    def get_auth(self, username, password):
        """
        Returns an HTTPDigestAuth instance configured with the provided username and password.
        
        Args:
            username: The username for HTTP Digest authentication.
            password: The password for HTTP Digest authentication.
        
        Returns:
            An HTTPDigestAuth object for use with HTTP requests.
        """
        return requests.auth.HTTPDigestAuth(username, password)
