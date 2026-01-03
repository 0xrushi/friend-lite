"""Plugin service for accessing the global plugin router.

This module provides singleton access to the plugin router, allowing
worker jobs to trigger plugins without accessing FastAPI app state directly.
"""

import logging
from typing import Optional
from pathlib import Path
import yaml

from advanced_omi_backend.plugins import PluginRouter

logger = logging.getLogger(__name__)

# Global plugin router instance
_plugin_router: Optional[PluginRouter] = None


def get_plugin_router() -> Optional[PluginRouter]:
    """Get the global plugin router instance.

    Returns:
        Plugin router instance if initialized, None otherwise
    """
    global _plugin_router
    return _plugin_router


def set_plugin_router(router: PluginRouter) -> None:
    """Set the global plugin router instance.

    This should be called during app initialization in app_factory.py.

    Args:
        router: Initialized plugin router instance
    """
    global _plugin_router
    _plugin_router = router
    logger.info("Plugin router registered with plugin service")


def init_plugin_router() -> Optional[PluginRouter]:
    """Initialize the plugin router from configuration.

    This is called during app startup to create and register the plugin router.

    Returns:
        Initialized plugin router, or None if no plugins configured
    """
    global _plugin_router

    if _plugin_router is not None:
        logger.warning("Plugin router already initialized")
        return _plugin_router

    try:
        _plugin_router = PluginRouter()

        # Load plugin configuration
        plugins_yml = Path("/app/plugins.yml")
        if plugins_yml.exists():
            with open(plugins_yml, 'r') as f:
                plugins_config = yaml.safe_load(f)
                plugins_data = plugins_config.get('plugins', {})

            # Initialize each enabled plugin
            for plugin_id, plugin_config in plugins_data.items():
                if not plugin_config.get('enabled', False):
                    continue

                try:
                    if plugin_id == 'homeassistant':
                        from advanced_omi_backend.plugins.homeassistant import HomeAssistantPlugin
                        plugin = HomeAssistantPlugin(plugin_config)
                        # Note: async initialization happens in app_factory lifespan
                        _plugin_router.register_plugin(plugin_id, plugin)
                        logger.info(f"✅ Plugin '{plugin_id}' registered")
                    else:
                        logger.warning(f"Unknown plugin: {plugin_id}")

                except Exception as e:
                    logger.error(f"Failed to register plugin '{plugin_id}': {e}", exc_info=True)

            logger.info(f"Plugins registered: {len(_plugin_router.plugins)} total")
        else:
            logger.info("No plugins.yml found, plugins disabled")

        return _plugin_router

    except Exception as e:
        logger.error(f"Failed to initialize plugin router: {e}", exc_info=True)
        _plugin_router = None
        return None


async def cleanup_plugin_router() -> None:
    """Clean up the plugin router and all registered plugins."""
    global _plugin_router

    if _plugin_router:
        try:
            await _plugin_router.cleanup_all()
            logger.info("Plugin router cleanup complete")
        except Exception as e:
            logger.error(f"Error during plugin router cleanup: {e}")
        finally:
            _plugin_router = None
