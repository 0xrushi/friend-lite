"""
Base plugin classes for Chronicle multi-level plugin architecture.

Provides:
- PluginContext: Context passed to plugin execution
- PluginResult: Result from plugin execution
- BasePlugin: Abstract base class for all plugins
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class PluginContext:
    """Context passed to plugin execution"""
    user_id: str
    access_level: str
    data: Dict[str, Any]  # Access-level specific data
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginResult:
    """Result from plugin execution"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    should_continue: bool = True  # Whether to continue normal processing


class BasePlugin(ABC):
    """
    Base class for all Chronicle plugins.

    Plugins can hook into different stages of the processing pipeline:
    - transcript: When new transcript segment arrives
    - conversation: When conversation processing completes
    - memory: When memory extraction finishes

    Subclasses should:
    1. Set SUPPORTED_ACCESS_LEVELS to list which levels they support
    2. Implement initialize() for plugin initialization
    3. Implement the appropriate callback methods (on_transcript, on_conversation_complete, on_memory_processed)
    4. Optionally implement cleanup() for resource cleanup
    """

    # Subclasses declare which access levels they support
    SUPPORTED_ACCESS_LEVELS: List[str] = []

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize plugin with configuration.

        Args:
            config: Plugin configuration from config/plugins.yml
                   Contains: enabled, access_level, trigger, and plugin-specific config
        """
        self.config = config
        self.enabled = config.get('enabled', False)
        self.access_level = config.get('access_level')
        self.trigger = config.get('trigger', {'type': 'always'})

    @abstractmethod
    async def initialize(self):
        """
        Initialize plugin resources (connect to services, etc.)

        Called during application startup after plugin registration.
        Raise an exception if initialization fails.
        """
        pass

    async def cleanup(self):
        """
        Clean up plugin resources.

        Called during application shutdown.
        Override if your plugin needs cleanup (closing connections, etc.)
        """
        pass

    # Access-level specific methods (implement only what you need)

    async def on_transcript(self, context: PluginContext) -> Optional[PluginResult]:
        """
        Called when new transcript segment arrives.

        Context data contains:
            - transcript: str - The transcript text
            - segment_id: str - Unique segment identifier
            - conversation_id: str - Current conversation ID

        For wake_word triggers, router adds:
            - command: str - Command with wake word stripped
            - original_transcript: str - Full transcript

        Returns:
            PluginResult with success status, optional message, and should_continue flag
        """
        pass

    async def on_conversation_complete(self, context: PluginContext) -> Optional[PluginResult]:
        """
        Called when conversation processing completes.

        Context data contains:
            - conversation: dict - Full conversation data
            - transcript: str - Complete transcript
            - duration: float - Conversation duration
            - conversation_id: str - Conversation identifier

        Returns:
            PluginResult with success status, optional message, and should_continue flag
        """
        pass

    async def on_memory_processed(self, context: PluginContext) -> Optional[PluginResult]:
        """
        Called after memory extraction finishes.

        Context data contains:
            - memories: list - Extracted memories
            - conversation: dict - Source conversation
            - memory_count: int - Number of memories created
            - conversation_id: str - Conversation identifier

        Returns:
            PluginResult with success status, optional message, and should_continue flag
        """
        pass
