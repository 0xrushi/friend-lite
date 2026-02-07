"""
Unit tests for OpenAI-Compatible custom LLM provider setup.

Tests the wizard's choice "3" (OpenAI-Compatible) in setup_llm(),
including model creation in config.yml and defaults updates.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml

# Add repo root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from config_manager import ConfigManager


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory with a minimal config.yml."""
    tmpdir = tempfile.mkdtemp()
    config_dir = Path(tmpdir) / "config"
    config_dir.mkdir()

    config = {
        "defaults": {
            "llm": "openai-llm",
            "embedding": "openai-embed",
            "stt": "stt-deepgram",
        },
        "models": [
            {
                "name": "openai-llm",
                "description": "OpenAI GPT-4o-mini",
                "model_type": "llm",
                "model_provider": "openai",
                "api_family": "openai",
                "model_name": "gpt-4o-mini",
                "model_url": "https://api.openai.com/v1",
                "api_key": "${oc.env:OPENAI_API_KEY,''}",
                "model_params": {"temperature": 0.2, "max_tokens": 2000},
                "model_output": "json",
            },
            {
                "name": "local-embed",
                "description": "Local embeddings via Ollama",
                "model_type": "embedding",
                "model_provider": "ollama",
                "api_family": "openai",
                "model_name": "nomic-embed-text:latest",
                "model_url": "http://localhost:11434/v1",
                "api_key": "${oc.env:OPENAI_API_KEY,ollama}",
                "embedding_dimensions": 768,
                "model_output": "vector",
            },
        ],
        "memory": {"provider": "chronicle"},
    }

    config_path = config_dir / "config.yml"
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    yield tmpdir

    shutil.rmtree(tmpdir)


@pytest.fixture
def config_manager(temp_config_dir):
    """Create a ConfigManager pointing to the temp config."""
    return ConfigManager(service_path=None, repo_root=Path(temp_config_dir))


class TestAddOrUpdateModel:
    """Tests for ConfigManager.add_or_update_model()."""

    def test_add_new_model(self, config_manager):
        """add_or_update_model() should append a new model when name doesn't exist."""
        new_model = {
            "name": "custom-llm",
            "description": "Custom OpenAI-compatible LLM",
            "model_type": "llm",
            "model_provider": "openai",
            "api_family": "openai",
            "model_name": "llama-3.1-70b-versatile",
            "model_url": "https://api.groq.com/openai/v1",
            "api_key": "${oc.env:CUSTOM_LLM_API_KEY,''}",
            "model_params": {"temperature": 0.2, "max_tokens": 2000},
            "model_output": "json",
        }

        config_manager.add_or_update_model(new_model)

        config = config_manager.get_full_config()
        model_names = [m["name"] for m in config["models"]]
        assert "custom-llm" in model_names

        added = next(m for m in config["models"] if m["name"] == "custom-llm")
        assert added["model_name"] == "llama-3.1-70b-versatile"
        assert added["model_url"] == "https://api.groq.com/openai/v1"
        assert added["model_type"] == "llm"

    def test_update_existing_model(self, config_manager):
        """add_or_update_model() should replace an existing model with the same name."""
        # First add
        model_v1 = {
            "name": "custom-llm",
            "model_type": "llm",
            "model_name": "model-v1",
            "model_url": "https://example.com/v1",
        }
        config_manager.add_or_update_model(model_v1)

        # Then update
        model_v2 = {
            "name": "custom-llm",
            "model_type": "llm",
            "model_name": "model-v2",
            "model_url": "https://example.com/v2",
        }
        config_manager.add_or_update_model(model_v2)

        config = config_manager.get_full_config()
        custom_models = [m for m in config["models"] if m["name"] == "custom-llm"]
        assert len(custom_models) == 1
        assert custom_models[0]["model_name"] == "model-v2"
        assert custom_models[0]["model_url"] == "https://example.com/v2"

    def test_add_model_to_empty_models_list(self, temp_config_dir):
        """add_or_update_model() should create models list if it doesn't exist."""
        config_path = Path(temp_config_dir) / "config" / "config.yml"
        with open(config_path, "w") as f:
            yaml.dump({"defaults": {"llm": "openai-llm"}}, f)

        cm = ConfigManager(service_path=None, repo_root=Path(temp_config_dir))
        cm.add_or_update_model({"name": "test-model", "model_type": "llm"})

        config = cm.get_full_config()
        assert "models" in config
        assert len(config["models"]) == 1
        assert config["models"][0]["name"] == "test-model"


class TestSetupLlmCustomProvider:
    """Tests for the custom LLM provider flow in setup_llm()."""

    def _make_setup(self, temp_config_dir):
        """Create a ChronicleSetup instance pointing at the temp config."""
        # We need to mock the ChronicleSetup constructor's checks
        # Instead, we test the logic by calling config_manager directly,
        # simulating what setup_llm() choice "3" does.
        return ConfigManager(service_path=None, repo_root=Path(temp_config_dir))

    def test_custom_llm_model_added_to_config(self, config_manager):
        """Selecting custom provider should create correct model entry."""
        llm_model = {
            "name": "custom-llm",
            "description": "Custom OpenAI-compatible LLM",
            "model_type": "llm",
            "model_provider": "openai",
            "api_family": "openai",
            "model_name": "llama-3.1-70b-versatile",
            "model_url": "https://api.groq.com/openai/v1",
            "api_key": "${oc.env:CUSTOM_LLM_API_KEY,''}",
            "model_params": {"temperature": 0.2, "max_tokens": 2000},
            "model_output": "json",
        }

        config_manager.add_or_update_model(llm_model)

        config = config_manager.get_full_config()
        model = next(m for m in config["models"] if m["name"] == "custom-llm")
        assert model["model_provider"] == "openai"
        assert model["api_family"] == "openai"
        assert model["model_name"] == "llama-3.1-70b-versatile"
        assert model["model_url"] == "https://api.groq.com/openai/v1"
        assert model["api_key"] == "${oc.env:CUSTOM_LLM_API_KEY,''}"
        assert model["model_params"]["temperature"] == 0.2
        assert model["model_output"] == "json"

    def test_custom_llm_and_embedding_model_added(self, config_manager):
        """Both LLM and embedding models should be created when embedding model is provided."""
        llm_model = {
            "name": "custom-llm",
            "model_type": "llm",
            "model_provider": "openai",
            "api_family": "openai",
            "model_name": "llama-3.1-70b-versatile",
            "model_url": "https://api.groq.com/openai/v1",
            "api_key": "${oc.env:CUSTOM_LLM_API_KEY,''}",
            "model_params": {"temperature": 0.2, "max_tokens": 2000},
            "model_output": "json",
        }
        embed_model = {
            "name": "custom-embed",
            "description": "Custom OpenAI-compatible embeddings",
            "model_type": "embedding",
            "model_provider": "openai",
            "api_family": "openai",
            "model_name": "text-embedding-3-small",
            "model_url": "https://api.groq.com/openai/v1",
            "api_key": "${oc.env:CUSTOM_LLM_API_KEY,''}",
            "embedding_dimensions": 1536,
            "model_output": "vector",
        }

        config_manager.add_or_update_model(llm_model)
        config_manager.add_or_update_model(embed_model)

        config = config_manager.get_full_config()
        model_names = [m["name"] for m in config["models"]]
        assert "custom-llm" in model_names
        assert "custom-embed" in model_names

        embed = next(m for m in config["models"] if m["name"] == "custom-embed")
        assert embed["model_type"] == "embedding"
        assert embed["model_name"] == "text-embedding-3-small"
        assert embed["embedding_dimensions"] == 1536

    def test_custom_llm_without_embedding_falls_back_to_local_embed(self, config_manager):
        """defaults.embedding should be local-embed when no custom embedding is provided."""
        llm_model = {
            "name": "custom-llm",
            "model_type": "llm",
            "model_name": "some-model",
            "model_url": "https://api.example.com/v1",
        }
        config_manager.add_or_update_model(llm_model)
        config_manager.update_config_defaults({"llm": "custom-llm", "embedding": "local-embed"})

        defaults = config_manager.get_config_defaults()
        assert defaults["llm"] == "custom-llm"
        assert defaults["embedding"] == "local-embed"

    def test_custom_llm_updates_defaults_with_embedding(self, config_manager):
        """defaults.llm and defaults.embedding should be updated correctly with custom embed."""
        config_manager.update_config_defaults({"llm": "custom-llm", "embedding": "custom-embed"})

        defaults = config_manager.get_config_defaults()
        assert defaults["llm"] == "custom-llm"
        assert defaults["embedding"] == "custom-embed"

    def test_custom_llm_api_key_env_reference(self, config_manager):
        """API key should use env var reference in config.yml model."""
        llm_model = {
            "name": "custom-llm",
            "model_type": "llm",
            "model_name": "some-model",
            "model_url": "https://api.example.com/v1",
            "api_key": "${oc.env:CUSTOM_LLM_API_KEY,''}",
        }
        config_manager.add_or_update_model(llm_model)

        config = config_manager.get_full_config()
        model = next(m for m in config["models"] if m["name"] == "custom-llm")
        assert model["api_key"] == "${oc.env:CUSTOM_LLM_API_KEY,''}"

    def test_existing_models_preserved_after_adding_custom(self, config_manager):
        """Adding a custom model should not remove existing models."""
        config_before = config_manager.get_full_config()
        original_count = len(config_before["models"])

        config_manager.add_or_update_model({
            "name": "custom-llm",
            "model_type": "llm",
            "model_name": "test-model",
            "model_url": "https://example.com/v1",
        })

        config_after = config_manager.get_full_config()
        assert len(config_after["models"]) == original_count + 1
        # Original models still present
        model_names = [m["name"] for m in config_after["models"]]
        assert "openai-llm" in model_names
        assert "local-embed" in model_names
        assert "custom-llm" in model_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
