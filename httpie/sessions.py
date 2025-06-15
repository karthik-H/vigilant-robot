"""Persistent, JSON-serialized sessions.

"""
import re
import os

from requests.cookies import RequestsCookieJar, create_cookie

from httpie.compat import urlsplit
from httpie.config import BaseConfigDict, DEFAULT_CONFIG_DIR
from httpie.plugins import plugin_manager


SESSIONS_DIR_NAME = 'sessions'
DEFAULT_SESSIONS_DIR = os.path.join(DEFAULT_CONFIG_DIR, SESSIONS_DIR_NAME)
VALID_SESSION_NAME_PATTERN = re.compile('^[a-zA-Z0-9_.-]+$')
# Request headers starting with these prefixes won't be stored in sessions.
# They are specific to each request.
# http://en.wikipedia.org/wiki/List_of_HTTP_header_fields#Requests
SESSION_IGNORED_HEADER_PREFIXES = ['Content-', 'If-']


def get_response(requests_session, session_name,
                 config_dir, args, read_only=False):
    """
                 Executes an HTTP request using session data persisted in a JSON file.
                 
                 Loads session headers, cookies, and authentication from a file based on the session name and request hostname, applies them to the outgoing request, and updates the session with new cookies and headers from the response unless in read-only mode. Returns the HTTP response object.
                 """
    from .client import get_requests_kwargs, dump_request
    if os.path.sep in session_name:
        path = os.path.expanduser(session_name)
    else:
        hostname = (args.headers.get('Host', None)
                    or urlsplit(args.url).netloc.split('@')[-1])
        if not hostname:
            # HACK/FIXME: httpie-unixsocket's URLs have no hostname.
            hostname = 'localhost'

        # host:port => host_port
        hostname = hostname.replace(':', '_')
        path = os.path.join(config_dir,
                            SESSIONS_DIR_NAME,
                            hostname,
                            session_name + '.json')

    session = Session(path)
    session.load()

    kwargs = get_requests_kwargs(args, base_headers=session.headers)
    if args.debug:
        dump_request(kwargs)
    session.update_headers(kwargs['headers'])

    if args.auth:
        session.auth = {
            'type': args.auth_type,
            'username': args.auth.key,
            'password': args.auth.value,
        }
    elif session.auth:
        kwargs['auth'] = session.auth

    requests_session.cookies = session.cookies

    try:
        response = requests_session.request(**kwargs)
    except Exception:
        raise
    else:
        # Existing sessions with `read_only=True` don't get updated.
        if session.is_new() or not read_only:
            session.cookies = requests_session.cookies
            session.save()
        return response


class Session(BaseConfigDict):
    helpurl = 'https://github.com/jkbrzt/httpie#sessions'
    about = 'HTTPie session file'

    def __init__(self, path, *args, **kwargs):
        """
        Initializes a new Session instance with empty headers, cookies, and authentication data.
        
        Args:
            path: The file path where the session data will be stored.
        """
        super(Session, self).__init__(*args, **kwargs)
        self._path = path
        self['headers'] = {}
        self['cookies'] = {}
        self['auth'] = {
            'type': None,
            'username': None,
            'password': None
        }

    def _get_path(self):
        """
        Returns the file path where the session data is stored.
        """
        return self._path

    def update_headers(self, request_headers):
        """
        Updates the session's stored headers with values from the provided request headers, excluding headers with ignored prefixes and 'User-Agent' headers starting with 'HTTPie/'.
        
        Args:
            request_headers: Dictionary of request headers to merge into the session.
        """
        for name, value in request_headers.items():
            value = value.decode('utf8')
            if name == 'User-Agent' and value.startswith('HTTPie/'):
                continue

            for prefix in SESSION_IGNORED_HEADER_PREFIXES:
                if name.lower().startswith(prefix.lower()):
                    break
            else:
                self['headers'][name] = value

    @property
    def headers(self):
        """
        Returns the session's stored HTTP headers as a dictionary.
        """
        return self['headers']

    @property
    def cookies(self):
        """
        Returns the session's cookies as a RequestsCookieJar.
        
        Converts the internally stored cookie dictionaries into a RequestsCookieJar object, recreating each cookie with its attributes and removing any expired cookies.
        """
        jar = RequestsCookieJar()
        for name, cookie_dict in self['cookies'].items():
            jar.set_cookie(create_cookie(
                name, cookie_dict.pop('value'), **cookie_dict))
        jar.clear_expired_cookies()
        return jar

    @cookies.setter
    def cookies(self, jar):
        """
        Serializes cookies from a CookieJar into the session for persistent storage.
        
        Only selected attributes ('value', 'path', 'secure', 'expires') are stored for each cookie.
        """
        # http://docs.python.org/2/library/cookielib.html#cookie-objects
        stored_attrs = ['value', 'path', 'secure', 'expires']
        self['cookies'] = {}
        for cookie in jar:
            self['cookies'][cookie.name] = dict(
                (attname, getattr(cookie, attname))
                for attname in stored_attrs
            )

    @property
    def auth(self):
        """
        Returns the authentication object for the session, if available.
        
        If authentication details are stored in the session, retrieves the corresponding authentication plugin and constructs the authentication object using the stored username and password. Returns None if no valid authentication is configured.
        """
        auth = self.get('auth', None)
        if not auth or not auth['type']:
            return
        auth_plugin = plugin_manager.get_auth_plugin(auth['type'])()
        return auth_plugin.get_auth(auth['username'], auth['password'])

    @auth.setter
    def auth(self, auth):
        """
        Sets the session's authentication data.
        
        Args:
        	auth: A dictionary containing 'type', 'username', and 'password' keys.
        """
        assert set(['type', 'username', 'password']) == set(auth.keys())
        self['auth'] = auth
