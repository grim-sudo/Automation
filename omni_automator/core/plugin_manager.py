"""
Plugin manager for extensible automation modules
"""

import os
import sys
import importlib
import inspect
from typing import Dict, Any, List, Optional, Type
from abc import ABC, abstractmethod


class AutomationPlugin(ABC):
    """Base class for all automation plugins"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Plugin description"""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Get list of actions this plugin can perform"""
        pass
    
    @abstractmethod
    def execute(self, action: str, params: Dict[str, Any]) -> Any:
        """Execute a plugin action"""
        pass
    
    def initialize(self) -> bool:
        """Initialize the plugin (optional override)"""
        return True
    
    def cleanup(self):
        """Cleanup plugin resources (optional override)"""
        pass


class PluginManager:
    """Manages loading and execution of automation plugins"""
    
    def __init__(self, plugin_dir: Optional[str] = None):
        self.plugins: Dict[str, AutomationPlugin] = {}
        self.plugin_dir = plugin_dir or self._get_default_plugin_dir()
        self._load_plugins()
    
    def _get_default_plugin_dir(self) -> str:
        """Get default plugin directory"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(os.path.dirname(current_dir), 'plugins')
    
    def _load_plugins(self):
        """Load all plugins from the plugin directory"""
        if not os.path.exists(self.plugin_dir):
            os.makedirs(self.plugin_dir, exist_ok=True)
            return
        
        # Add plugin directory to Python path
        if self.plugin_dir not in sys.path:
            sys.path.insert(0, self.plugin_dir)
        
        # Load plugins from Python files
        for filename in os.listdir(self.plugin_dir):
            if filename.endswith('.py') and not filename.startswith('_'):
                module_name = filename[:-3]
                try:
                    self._load_plugin_from_module(module_name)
                except Exception as e:
                    print(f"Failed to load plugin {module_name}: {e}")
    
    def _load_plugin_from_module(self, module_name: str):
        """Load a plugin from a Python module"""
        try:
            module = importlib.import_module(module_name)
            
            # Find plugin classes in the module
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, AutomationPlugin) and 
                    obj != AutomationPlugin):
                    
                    # Instantiate and register the plugin
                    plugin_instance = obj()
                    if plugin_instance.initialize():
                        self.plugins[plugin_instance.name] = plugin_instance
                        print(f"Loaded plugin: {plugin_instance.name} v{plugin_instance.version}")
                    
        except Exception as e:
            raise Exception(f"Error loading plugin module {module_name}: {e}")
    
    def register_plugin(self, plugin: AutomationPlugin) -> bool:
        """Register a plugin instance"""
        try:
            if plugin.initialize():
                self.plugins[plugin.name] = plugin
                return True
            return False
        except Exception as e:
            print(f"Failed to register plugin {plugin.name}: {e}")
            return False
    
    def unregister_plugin(self, plugin_name: str) -> bool:
        """Unregister a plugin"""
        if plugin_name in self.plugins:
            try:
                self.plugins[plugin_name].cleanup()
                del self.plugins[plugin_name]
                return True
            except Exception as e:
                print(f"Error unregistering plugin {plugin_name}: {e}")
        return False
    
    def execute(self, plugin_name: str, action: str, params: Dict[str, Any]) -> Any:
        """Execute an action using a specific plugin"""
        if plugin_name not in self.plugins:
            raise ValueError(f"Plugin '{plugin_name}' not found")
        
        plugin = self.plugins[plugin_name]
        
        if action not in plugin.get_capabilities():
            raise ValueError(f"Action '{action}' not supported by plugin '{plugin_name}'")
        
        return plugin.execute(action, params)
    
    def get_available_plugins(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all available plugins"""
        plugin_info = {}
        
        for name, plugin in self.plugins.items():
            plugin_info[name] = {
                'description': plugin.description,
                'version': plugin.version,
                'capabilities': plugin.get_capabilities()
            }
        
        return plugin_info
    
    def get_plugin_by_capability(self, capability: str) -> List[str]:
        """Get plugins that support a specific capability"""
        matching_plugins = []
        
        for name, plugin in self.plugins.items():
            if capability in plugin.get_capabilities():
                matching_plugins.append(name)
        
        return matching_plugins
    
    def shutdown(self):
        """Shutdown all plugins"""
        for plugin in self.plugins.values():
            try:
                plugin.cleanup()
            except Exception as e:
                print(f"Error during plugin cleanup: {e}")
        
        self.plugins.clear()
