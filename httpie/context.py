import sys

from httpie.compat import is_windows
from httpie.config import DEFAULT_CONFIG_DIR, Config


class Environment(object):
    """
    Information about the execution context
    (standard streams, config directory, etc).

    By default, it represents the actual environment.
    All of the attributes can be overwritten though, which
    is used by the test suite to simulate various scenarios.

    """
    is_windows = is_windows
    config_dir = DEFAULT_CONFIG_DIR
    stdin = sys.stdin
    stdin_isatty = stdin.isatty()
    stdin_encoding = None
    stdout = sys.stdout
    stdout_isatty = stdout.isatty()
    stdout_encoding = None
    stderr = sys.stderr
    stderr_isatty = stderr.isatty()
    colors = 256
    if not is_windows:
        import curses
        try:
            curses.setupterm()
            try:
                colors = curses.tigetnum('colors')
            except TypeError:
                # pypy3 (2.4.0)
                colors = curses.tigetnum(b'colors')
        except curses.error:
            pass
        del curses
    else:
        # noinspection PyUnresolvedReferences
        import colorama.initialise
        stdout = colorama.initialise.wrap_stream(
            stdout, convert=None, strip=None,
            autoreset=True, wrap=True
        )
        stderr = colorama.initialise.wrap_stream(
            stderr, convert=None, strip=None,
            autoreset=True, wrap=True
        )
        del colorama

    def __init__(self, **kwargs):
        """
        Initializes an Environment instance, allowing class attributes to be overridden via keyword arguments.
        
        Keyword arguments can be used to customize any class attribute for this instance. Standard input and output encodings are determined based on provided values, stream encodings, or default to 'utf8' if unspecified. On Windows, the actual encoding is retrieved from the unwrapped output stream if colorama is used.
        """
        assert all(hasattr(type(self), attr) for attr in kwargs.keys())
        self.__dict__.update(**kwargs)

        # Keyword arguments > stream.encoding > default utf8
        if self.stdin_encoding is None:
            self.stdin_encoding = getattr(
                self.stdin, 'encoding', None) or 'utf8'
        if self.stdout_encoding is None:
            actual_stdout = self.stdout
            if is_windows:
                # noinspection PyUnresolvedReferences
                from colorama import AnsiToWin32
                if isinstance(self.stdout, AnsiToWin32):
                    actual_stdout = self.stdout.wrapped
            self.stdout_encoding = getattr(
                actual_stdout, 'encoding', None) or 'utf8'

    @property
    def config(self):
        """
        Lazily initializes and returns the configuration object for the environment.
        
        If the configuration does not exist, it is created and saved; otherwise, the existing configuration is loaded. The configuration instance is cached for subsequent access.
        """
        if not hasattr(self, '_config'):
            self._config = Config(directory=self.config_dir)
            if self._config.is_new():
                self._config.save()
            else:
                self._config.load()
        return self._config
