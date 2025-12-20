"""Centralized configuration for the Obsidian RAG project.

This module exposes typed configuration values and a shared OpenAI client
instance. Environment variables can override defaults where provided.
"""

from __future__ import annotations

import os
import logging
from pathlib import Path
import yaml
from openai import OpenAI

# Helper to load .env file manually
def load_env_file(filepath: Path) -> dict[str, str]:
    env_vars = {}
    if filepath.exists():
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    # Handle quotes
                    value = value.strip()
                    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    env_vars[key.strip()] = value
    return env_vars

# Helper to resolve ${VAR:-default}
def resolve_value(value: str | int | float) -> str | int | float:
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        content = value[2:-1]
        if ":-" in content:
            var_name, default_val = content.split(":-", 1)
            return os.getenv(var_name, default_val)
        else:
            return os.getenv(content, "")
    return value

# Resolve paths
CURRENT_DIR = Path(__file__).parent.resolve()
ROOT_DIR = CURRENT_DIR.parent.parent
CONFIG_YML_PATH = ROOT_DIR / "config.yml"
ADVANCED_ENV_PATH = ROOT_DIR / "backends" / "advanced" / ".env"

# Load Configs
config_data = {}
if CONFIG_YML_PATH.exists():
    with open(CONFIG_YML_PATH, 'r') as f:
        config_data = yaml.safe_load(f)

env_data = load_env_file(ADVANCED_ENV_PATH)

# Helper to get model config
def get_model_config(model_role: str):
    default_name = config_data.get('defaults', {}).get(model_role)
    if not default_name:
        return None
    
    for model in config_data.get('models', []):
        if model.get('name') == default_name:
            return model
    return None

llm_config = get_model_config('llm')
if not llm_config:
    raise ValueError("Configuration for 'defaults.llm' not found or model not defined in config.yml")

embed_config = get_model_config('embedding')
if not embed_config:
    raise ValueError("Configuration for 'defaults.embedding' not found or model not defined in config.yml")

# Neo4j Connection
# Loaded strictly from backends/advanced/.env
if "NEO4J_HOST" not in env_data:
     raise KeyError("NEO4J_HOST not found in backends/advanced/.env")

neo4j_host = env_data["NEO4J_HOST"]
NEO4J_URI: str = f"bolt://{neo4j_host}:7687"
NEO4J_USER: str = env_data.get("NEO4J_USER")
NEO4J_PASSWORD: str = env_data.get("NEO4J_PASSWORD")

# Embeddings / Models
# Loaded strictly from config.yml
EMBEDDING_MODEL: str = resolve_value(embed_config['model_name'])
EMBEDDING_DIMENSIONS: int = int(resolve_value(embed_config['embedding_dimensions']))
LLM_MODEL: str = resolve_value(llm_config['model_name'])

# Chunking
CHUNK_CHAR_LIMIT: int = int(os.getenv("CHUNK_CHAR_LIMIT", "1000"))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))

# OpenAI-Compatible API
# Loaded strictly from config.yml
OPENAI_BASE_URL: str = resolve_value(llm_config['model_url'])
OPENAI_API_KEY: str = resolve_value(llm_config['api_key'])

# Logging configuration
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT: str = os.getenv(
    "LOG_FORMAT", "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

def _configure_logging() -> None:
    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(level=level, format=LOG_FORMAT)
    else:
        root.setLevel(level)

_configure_logging()

# Shared OpenAI client instance
client: OpenAI = OpenAI(base_url=OPENAI_BASE_URL, api_key=OPENAI_API_KEY)

# Paths / Data
VAULT_PATH: str = os.getenv("VAULT_PATH", "./obsidian_dataview_example_vault")

__all__ = [
    "VAULT_PATH",
    "NEO4J_URI",
    "NEO4J_USER",
    "NEO4J_PASSWORD",
    "EMBEDDING_MODEL",
    "EMBEDDING_DIMENSIONS",
    "LLM_MODEL",
    "CHUNK_CHAR_LIMIT",
    "CHUNK_OVERLAP",
    "OPENAI_BASE_URL",
    "OPENAI_API_KEY",
    "LOG_LEVEL",
    "LOG_FORMAT",
    "client",
]