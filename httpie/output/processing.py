import re

from httpie.plugins import plugin_manager
from httpie.context import Environment


MIME_RE = re.compile(r'^[^/]+/[^/]+$')


def is_valid_mime(mime):
    """
    Checks if the given MIME type string is valid according to the 'type/subtype' pattern.
    
    Args:
        mime: The MIME type string to validate.
    
    Returns:
        A match object if the MIME type is valid, otherwise None.
    """
    return mime and MIME_RE.match(mime)


class Conversion(object):

    def get_converter(self, mime):
        """
        Returns a converter instance that supports the specified MIME type.
        
        If the MIME type is valid and a suitable converter is found among the available plugins, returns an instance of that converter. Returns None if no converter supports the MIME type or if the MIME type is invalid.
        """
        if is_valid_mime(mime):
            for converter_class in plugin_manager.get_converters():
                if converter_class.supports(mime):
                    return converter_class(mime)


class Formatting(object):
    """A delegate class that invokes the actual processors."""

    def __init__(self, groups, env=Environment(), **kwargs):
        Initializes the Formatting delegate with enabled formatter plugins from specified groups.
        
        For each group name provided, instantiates formatter plugins with the given environment and keyword arguments, collecting only those that are enabled.
        available_plugins = plugin_manager.get_formatters_grouped()
        self.enabled_plugins = []
        for group in groups:
            for cls in available_plugins[group]:
                p = cls(env=env, **kwargs)
                if p.enabled:
                    self.enabled_plugins.append(p)

    def format_headers(self, headers):
        """
        Applies all enabled formatter plugins to the provided headers sequentially.
        
        Args:
            headers: The HTTP headers to be formatted.
        
        Returns:
            The headers after all enabled plugins have been applied.
        """
        for p in self.enabled_plugins:
            headers = p.format_headers(headers)
        return headers

    def format_body(self, content, mime):
        """
        Formats the body content using enabled plugins if the MIME type is valid.
        
        If the MIME type is valid, each enabled plugin's `format_body` method is applied
        sequentially to the content. If the MIME type is invalid, the content is returned
        unchanged.
        
        Args:
            content: The body content to be formatted.
            mime: The MIME type of the content.
        
        Returns:
            The formatted content if the MIME type is valid; otherwise, the original content.
        """
        if is_valid_mime(mime):
            for p in self.enabled_plugins:
                content = p.format_body(content, mime)
        return content
