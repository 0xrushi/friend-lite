"""Plugin service for accessing the global plugin router.

This module provides singleton access to the plugin router, allowing
worker jobs to trigger plugins without accessing FastAPI app state directly.
"""

import logging
import os
import re
from typing import Optional, Any
from pathlib import Path
import yaml

from advanced_omi_backend.plugins import PluginRouter

logger = logging.getLogger(__name__)

# Global plugin router instance
_plugin_router: Optional[PluginRouter] = None


def expand_env_vars(value: Any) -> Any:
    """
    Recursively expand environment variables in configuration values.

    Supports ${ENV_VAR} syntax. If the environment variable is not set,
    the original placeholder is kept.

    Args:
        value: Configuration value (can be str, dict, list, or other)

    Returns:
        Value with environment variables expanded

    Examples:
        >>> os.environ['MY_TOKEN'] = 'secret123'
        >>> expand_env_vars('token: ${MY_TOKEN}')
        'token: secret123'
        >>> expand_env_vars({'token': '${MY_TOKEN}'})
        {'token': 'secret123'}
    """
    if isinstance(value, str):
        # Pattern: ${ENV_VAR} or ${ENV_VAR:-default}
        def replacer(match):
            var_expr = match.group(1)
            # Support default values: ${VAR:-default}
            if ':-' in var_expr:
                var_name, default = var_expr.split(':-', 1)
                return os.environ.get(var_name.strip(), default.strip())
            else:
                var_name = var_expr.strip()
                env_value = os.environ.get(var_name)
                if env_value is None:
                    logger.warning(
                        f"Environment variable '{var_name}' not found, "
                        f"keeping placeholder: ${{{var_name}}}"
                    )
                    return match.group(0)  # Keep original placeholder
                return env_value

        return re.sub(r'\$\{([^}]+)\}', replacer, value)

    elif isinstance(value, dict):
        return {k: expand_env_vars(v) for k, v in value.items()}

    elif isinstance(value, list):
        return [expand_env_vars(item) for item in value]

    else:
        return value


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
        logger.info(f"🔍 Looking for plugins config at: {plugins_yml}")
        logger.info(f"🔍 File exists: {plugins_yml.exists()}")

        if plugins_yml.exists():
            with open(plugins_yml, 'r') as f:
                plugins_config = yaml.safe_load(f)
                # Expand environment variables in configuration
                plugins_config = expand_env_vars(plugins_config)
                plugins_data = plugins_config.get('plugins', {})

            logger.info(f"🔍 Loaded plugins config with {len(plugins_data)} plugin(s): {list(plugins_data.keys())}")

            # Initialize each enabled plugin
            for plugin_id, plugin_config in plugins_data.items():
                logger.info(f"🔍 Processing plugin '{plugin_id}', enabled={plugin_config.get('enabled', False)}")
                if not plugin_config.get('enabled', False):
                    continue

                try:
                    if plugin_id == 'homeassistant':
                        from advanced_omi_backend.plugins.homeassistant import HomeAssistantPlugin
                        plugin = HomeAssistantPlugin(plugin_config)
                        # Note: async initialization happens in app_factory lifespan
                        _plugin_router.register_plugin(plugin_id, plugin)
                        logger.info(f"✅ Plugin '{plugin_id}' registered")
                    elif plugin_id == 'test_event':
                        from advanced_omi_backend.plugins.test_event import TestEventPlugin
                        plugin = TestEventPlugin(plugin_config)
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
