from itertools import groupby
from pkg_resources import iter_entry_points
from httpie.plugins import AuthPlugin, FormatterPlugin, ConverterPlugin
from httpie.plugins.base import TransportPlugin


ENTRY_POINT_NAMES = [
    'httpie.plugins.auth.v1',
    'httpie.plugins.formatter.v1',
    'httpie.plugins.converter.v1',
    'httpie.plugins.transport.v1',
]


class PluginManager(object):

    def __init__(self):
        """
        Initializes the PluginManager with an empty list of registered plugins.
        """
        self._plugins = []

    def __iter__(self):
        """
        Returns an iterator over the registered plugins.
        """
        return iter(self._plugins)

    def register(self, *plugins):
        """
        Registers one or more plugin classes with the manager.
        
        Each provided plugin class is added to the internal registry for later retrieval and use.
        """
        for plugin in plugins:
            self._plugins.append(plugin)

    def load_installed_plugins(self):
        """
        Loads and registers plugins from installed packages based on predefined entry points.
        
        Iterates over each entry point name, loads available plugins, assigns their package name, and registers them with the manager.
        """
        for entry_point_name in ENTRY_POINT_NAMES:
            for entry_point in iter_entry_points(entry_point_name):
                plugin = entry_point.load()
                plugin.package_name = entry_point.dist.key
                self.register(entry_point.load())

    # Auth
    def get_auth_plugins(self):
        """
        Returns a list of registered authentication plugin classes.
        
        Only plugins that are subclasses of AuthPlugin are included.
        """
        return [plugin for plugin in self if issubclass(plugin, AuthPlugin)]

    def get_auth_plugin_mapping(self):
        """
        Returns a dictionary mapping authentication plugin types to their corresponding plugin classes.
        
        Each key is the `auth_type` attribute of an authentication plugin, and each value is the plugin class itself.
        """
        return dict((plugin.auth_type, plugin)
                    for plugin in self.get_auth_plugins())

    def get_auth_plugin(self, auth_type):
        """
        Retrieves the authentication plugin class associated with the given authentication type.
        
        Args:
            auth_type: The key identifying the authentication type.
        
        Returns:
            The authentication plugin class corresponding to the specified type.
        
        Raises:
            KeyError: If no plugin is registered for the given authentication type.
        """
        return self.get_auth_plugin_mapping()[auth_type]

    # Output processing
    def get_formatters(self):
        """
        Returns a list of registered plugins that are subclasses of FormatterPlugin.
        """
        return [plugin for plugin in self
                if issubclass(plugin, FormatterPlugin)]

    def get_formatters_grouped(self):
        """
        Groups registered formatter plugins by their group name.
        
        Returns:
            A dictionary mapping each group name to a list of formatter plugin classes in that group. If a plugin does not specify a group name, it is grouped under 'format'.
        """
        groups = {}
        for group_name, group in groupby(
                self.get_formatters(),
                key=lambda p: getattr(p, 'group_name', 'format')):
            groups[group_name] = list(group)
        return groups

    def get_converters(self):
        """
        Returns a list of registered plugins that are subclasses of ConverterPlugin.
        """
        return [plugin for plugin in self
                if issubclass(plugin, ConverterPlugin)]

    # Adapters
    def get_transport_plugins(self):
        """
        Returns a list of registered plugins that are subclasses of TransportPlugin.
        """
        return [plugin for plugin in self
                if issubclass(plugin, TransportPlugin)]
