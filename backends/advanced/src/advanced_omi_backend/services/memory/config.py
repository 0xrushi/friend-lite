"""Memory service configuration utilities."""

import logging
import os
import yaml
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Union

memory_logger = logging.getLogger("memory_service")


def _is_langfuse_enabled() -> bool:
    """Check if Langfuse is properly configured."""
    return bool(
        os.getenv("LANGFUSE_PUBLIC_KEY")
        and os.getenv("LANGFUSE_SECRET_KEY")
        and os.getenv("LANGFUSE_HOST")
    )


class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    OLLAMA = "ollama"
    CUSTOM = "custom"

class VectorStoreProvider(Enum):
    """Supported vector store providers."""
    QDRANT = "qdrant"
    WEAVIATE = "weaviate"
    CUSTOM = "custom"

class MemoryProvider(Enum):
    """Supported memory service providers."""
    CHRONICLE = "chronicle"            # Default sophisticated implementation
    OPENMEMORY_MCP = "openmemory_mcp"  # OpenMemory MCP backend
    MYCELIA = "mycelia"                # Mycelia memory backend

@dataclass
class MemoryConfig:
    """Configuration for memory service."""
    memory_provider: MemoryProvider = MemoryProvider.CHRONICLE
    llm_provider: LLMProvider = LLMProvider.OPENAI
    vector_store_provider: VectorStoreProvider = VectorStoreProvider.QDRANT
    llm_config: Dict[str, Any] = None
    vector_store_config: Dict[str, Any] = None
    embedder_config: Dict[str, Any] = None
    openmemory_config: Dict[str, Any] = None  # Configuration for OpenMemory MCP
    mycelia_config: Dict[str, Any] = None  # Configuration for Mycelia
    extraction_prompt: str = None
    extraction_enabled: bool = True
    timeout_seconds: int = 1200

# Helper to resolve ${VAR:-default}
def resolve_value(value: Union[str, int, float]) -> Union[str, int, float]:
    """Resolve environment variable references in configuration values.
    
    Supports ${VAR} and ${VAR:-default} syntax. Returns the original value
    if it's not a string or doesn't match the pattern.
    """
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        content = value[2:-1]
        if ":-" in content:
            var_name, default_val = content.split(":-", 1)
            return os.getenv(var_name, default_val)
        else:
            return os.getenv(content, "")
    return value

def load_config_yml() -> Dict[str, Any]:
    """Load config.yml from standard locations."""
    # Check /app/config.yml (Docker) or root relative to file
    current_dir = Path(__file__).parent.resolve()
    # Path inside Docker: /app/config.yml (if mounted) or ../../../config.yml relative to src
    paths = [
        Path("/app/config.yml"),
        current_dir.parent.parent.parent.parent.parent / "config.yml", # Relative to src/
        Path("./config.yml"),
    ]
    
    for path in paths:
        if path.exists():
            with open(path, 'r') as f:
                return yaml.safe_load(f) or {}
                
    raise FileNotFoundError(f"config.yml not found in any of: {[str(p) for p in paths]}")

def build_memory_config_from_env() -> MemoryConfig:
    """Build memory configuration strictly from config.yml."""
    root_config = load_config_yml()
    
    # 1. Basic Memory Provider Settings
    mem_section = root_config.get('memory', {})
    provider_name = mem_section.get('provider', 'chronicle').lower()
    if provider_name not in [p.value for p in MemoryProvider]:
        raise ValueError(f"Unsupported memory provider: {provider_name}")
    
    provider_enum = MemoryProvider(provider_name)
    timeout_seconds = int(mem_section.get('timeout_seconds', 1200))
    extraction_section = mem_section.get('extraction', {})
    extraction_enabled = extraction_section.get('enabled', True)
    extraction_prompt = extraction_section.get('prompt')

    # 2. OpenMemory MCP / Mycelia specific configs
    openmemory_config = None
    if provider_enum == MemoryProvider.OPENMEMORY_MCP:
        om_raw = mem_section.get('openmemory_mcp', {})
        openmemory_config = {
            "server_url": resolve_value(om_raw.get('server_url', 'http://localhost:8765')),
            "client_name": resolve_value(om_raw.get('client_name', 'chronicle')),
            "user_id": resolve_value(om_raw.get('user_id', 'default')),
            "timeout": int(resolve_value(om_raw.get('timeout', 30)))
        }

    mycelia_config = None
    if provider_enum == MemoryProvider.MYCELIA:
        my_raw = mem_section.get('mycelia', {})
        mycelia_config = {
            "api_url": resolve_value(my_raw.get('api_url', 'http://localhost:5173')),
            "timeout": int(resolve_value(my_raw.get('timeout', 30)))
        }

    # 3. LLM Configuration (for Chronicle or Mycelia temporal extraction)
    default_llm_name = root_config.get('defaults', {}).get('llm')
    default_embed_name = root_config.get('defaults', {}).get('embedding')
    
    def find_model(name):
        for m in root_config.get('models', []):
            if m.get('name') == name:
                return m
        return None

    llm_def = find_model(default_llm_name)
    if not llm_def:
        raise ValueError(f"Default LLM model '{default_llm_name}' not found in config.yml")
    
    embed_def = find_model(default_embed_name)
    if not embed_def:
        raise ValueError(f"Default embedding model '{default_embed_name}' not found in config.yml")

    llm_provider_name = llm_def.get('model_provider', 'openai').lower()
    llm_provider_enum = LLMProvider(llm_provider_name)
    
    llm_config = {
        "api_key": str(resolve_value(llm_def.get('api_key', ''))),
        "model": str(resolve_value(llm_def.get('model_name', ''))),
        "base_url": str(resolve_value(llm_def.get('model_url', ''))),
        "embedding_model": str(resolve_value(embed_def.get('model_name', ''))),
        "temperature": llm_def.get('model_params', {}).get('temperature', 0.1),
        "max_tokens": llm_def.get('model_params', {}).get('max_tokens', 2000)
    }

    # 4. Vector Store Configuration
    default_vs_name = root_config.get('defaults', {}).get('vector_store')
    vs_def = find_model(default_vs_name)
    if not vs_def:
        raise ValueError(f"Default vector store '{default_vs_name}' not found in config.yml")
    
    vs_provider_name = vs_def.get('model_provider', 'qdrant').lower()
    vs_provider_enum = VectorStoreProvider(vs_provider_name)
    
    # Get embedding dims for vector store
    # Since we can't easily query model here without potentially hanging, 
    # we'll use the dimension from embed_def if provided, or default
    embedding_dims = int(resolve_value(embed_def.get('embedding_dimensions')))

    vs_config = {
        "host": resolve_value(vs_def.get('model_params', {}).get('host', 'localhost')),
        "port": int(resolve_value(vs_def.get('model_params', {}).get('port', 6333))),
        "collection_name": resolve_value(vs_def.get('model_params', {}).get('collection_name', 'memories')),
        "embedding_dims": embedding_dims
    }

    return MemoryConfig(
        memory_provider=provider_enum,
        llm_provider=llm_provider_enum,
        vector_store_provider=vs_provider_enum,
        llm_config=llm_config,
        vector_store_config=vs_config,
        openmemory_config=openmemory_config,
        mycelia_config=mycelia_config,
        extraction_prompt=extraction_prompt,
        extraction_enabled=extraction_enabled,
        timeout_seconds=timeout_seconds
    )
