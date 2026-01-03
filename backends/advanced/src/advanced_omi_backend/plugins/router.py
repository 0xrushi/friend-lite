"""
Plugin routing system for multi-level plugin architecture.

Routes pipeline events to appropriate plugins based on access level and triggers.
"""

import logging
from typing import Dict, List, Optional

from .base import BasePlugin, PluginContext, PluginResult

logger = logging.getLogger(__name__)


class PluginRouter:
    """Routes pipeline events to appropriate plugins based on access level and triggers"""

    def __init__(self):
        self.plugins: Dict[str, BasePlugin] = {}
        # Index plugins by access level for fast lookup
        self._plugins_by_level: Dict[str, List[str]] = {
            'transcript': [],
            'streaming_transcript': [],
            'conversation': [],
            'memory': []
        }

    def register_plugin(self, plugin_id: str, plugin: BasePlugin):
        """Register a plugin with the router"""
        self.plugins[plugin_id] = plugin

        # Index by access level
        access_level = plugin.access_level
        if access_level in self._plugins_by_level:
            self._plugins_by_level[access_level].append(plugin_id)

        logger.info(f"Registered plugin '{plugin_id}' for access level '{access_level}'")

    async def trigger_plugins(
        self,
        access_level: str,
        user_id: str,
        data: Dict,
        metadata: Optional[Dict] = None
    ) -> List[PluginResult]:
        """
        Trigger all plugins registered for this access level.

        Args:
            access_level: 'transcript', 'streaming_transcript', 'conversation', or 'memory'
            user_id: User ID for context
            data: Access-level specific data
            metadata: Optional metadata

        Returns:
            List of plugin results
        """
        results = []

        # Hierarchical triggering logic:
        # - 'streaming_transcript': trigger both 'streaming_transcript' AND 'transcript' plugins
        # - 'transcript': trigger ONLY 'transcript' plugins (not 'streaming_transcript')
        # - Other levels: exact match only
        if access_level == 'streaming_transcript':
            # Streaming mode: trigger both streaming_transcript AND transcript plugins
            plugin_ids = (
                self._plugins_by_level.get('streaming_transcript', []) +
                self._plugins_by_level.get('transcript', [])
            )
        else:
            # Batch mode or other modes: exact match only
            plugin_ids = self._plugins_by_level.get(access_level, [])

        for plugin_id in plugin_ids:
            plugin = self.plugins[plugin_id]

            if not plugin.enabled:
                continue

            # Check trigger condition
            if not await self._should_trigger(plugin, data):
                continue

            # Execute plugin at appropriate access level
            try:
                context = PluginContext(
                    user_id=user_id,
                    access_level=access_level,
                    data=data,
                    metadata=metadata or {}
                )

                result = await self._execute_plugin(plugin, access_level, context)

                if result:
                    results.append(result)

                    # If plugin says stop processing, break
                    if not result.should_continue:
                        logger.info(f"Plugin '{plugin_id}' stopped further processing")
                        break

            except Exception as e:
                logger.error(f"Error executing plugin '{plugin_id}': {e}", exc_info=True)

        return results

    async def _should_trigger(self, plugin: BasePlugin, data: Dict) -> bool:
        """Check if plugin should be triggered based on trigger configuration"""
        trigger_type = plugin.trigger.get('type', 'always')

        if trigger_type == 'always':
            return True

        elif trigger_type == 'wake_word':
            # Check if transcript starts with wake word(s)
            transcript = data.get('transcript', '')
            transcript_lower = transcript.lower().strip()

            # Support both singular 'wake_word' and plural 'wake_words' (list)
            wake_words = plugin.trigger.get('wake_words', [])
            if not wake_words:
                # Fallback to singular wake_word for backward compatibility
                wake_word = plugin.trigger.get('wake_word', '')
                if wake_word:
                    wake_words = [wake_word]

            # Check if transcript starts with any wake word
            for wake_word in wake_words:
                wake_word_lower = wake_word.lower()
                if wake_word_lower and transcript_lower.startswith(wake_word_lower):
                    # Extract command (remove wake word)
                    command = transcript[len(wake_word):].strip()
                    data['command'] = command
                    data['original_transcript'] = transcript
                    return True

            return False

        elif trigger_type == 'conditional':
            # Future: Custom condition checking
            return True

        return False

    async def _execute_plugin(
        self,
        plugin: BasePlugin,
        access_level: str,
        context: PluginContext
    ) -> Optional[PluginResult]:
        """Execute plugin method for specified access level"""
        # Both 'transcript' and 'streaming_transcript' call on_transcript()
        if access_level in ('transcript', 'streaming_transcript'):
            return await plugin.on_transcript(context)
        elif access_level == 'conversation':
            return await plugin.on_conversation_complete(context)
        elif access_level == 'memory':
            return await plugin.on_memory_processed(context)

        return None

    async def cleanup_all(self):
        """Clean up all registered plugins"""
        for plugin_id, plugin in self.plugins.items():
            try:
                await plugin.cleanup()
                logger.info(f"Cleaned up plugin '{plugin_id}'")
            except Exception as e:
                logger.error(f"Error cleaning up plugin '{plugin_id}': {e}")
