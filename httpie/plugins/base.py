class BasePlugin(object):

    # The name of the plugin, eg. "My auth".
    name = None

    # Optional short description. Will be be shown in the help
    # under --auth-type.
    description = None

    # This be set automatically once the plugin has been loaded.
    package_name = None


class AuthPlugin(BasePlugin):
    """
    Base auth plugin class.

    See <https://github.com/jkbrzt/httpie-ntlm> for an example auth plugin.

    """
    # The value that should be passed to --auth-type
    # to use this auth plugin. Eg. "my-auth"
    auth_type = None

    def get_auth(self, username, password):
        """
        Returns an authentication object for use with HTTP requests.
        
        Args:
            username: The username for authentication.
            password: The password for authentication.
        
        Returns:
            An instance of a subclass of `requests.auth.AuthBase` configured with the provided credentials.
        
        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError()


class TransportPlugin(BasePlugin):
    """

    http://docs.python-requests.org/en/latest/user/advanced/#transport-adapters

    """

    # The URL prefix the adapter should be mount to.
    prefix = None

    def get_adapter(self):
        """
        Returns a transport adapter instance for use with the specified URL prefix.
        
        Subclasses must implement this method to provide a custom `requests.adapters.BaseAdapter` for handling HTTP requests matching the plugin's `prefix`.
        """
        raise NotImplementedError()


class ConverterPlugin(object):

    def __init__(self, mime):
        """
        Initializes the converter plugin with the specified MIME type.
        
        Args:
            mime: The MIME type string that this converter will handle.
        """
        self.mime = mime

    def convert(self, content_bytes):
        """
        Converts raw content bytes to a processed format.
        
        Subclasses must implement this method to handle conversion of content based on the plugin's purpose.
        
        Args:
            content_bytes: The raw content as bytes to be converted.
        
        Returns:
            The converted content in the appropriate format.
        """
        raise NotImplementedError

    @classmethod
    def supports(cls, mime):
        """
        Determines if the converter supports the specified MIME type.
        
        Args:
            mime: The MIME type string to check.
        
        Returns:
            True if the converter supports the given MIME type, otherwise False.
        
        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError


class FormatterPlugin(object):

    def __init__(self, **kwargs):
        """
        Initializes the formatter plugin with optional keyword arguments.
        
        All provided keyword arguments are stored for use by the formatter. The plugin is enabled by default.
        """
        self.enabled = True
        self.kwargs = kwargs

    def format_headers(self, headers):
        """
        Processes HTTP headers and returns the formatted result.
        
        Args:
            headers: The HTTP headers as a text string.
        
        Returns:
            The processed headers as a text string. By default, returns the input unchanged.
        """
        return headers

    def format_body(self, content, mime):
        """
        Processes and returns the HTTP body content, optionally based on the provided MIME type.
        
        Args:
            content: The HTTP body content as text.
            mime: The MIME type of the content (e.g., 'application/atom+xml').
        
        Returns:
            The processed body content as text. By default, returns the input unchanged.
        """
        return content
