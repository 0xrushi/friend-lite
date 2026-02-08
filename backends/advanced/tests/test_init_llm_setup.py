"""Unit tests for OpenAI custom API setup/initialization flow in init.py.

These tests verify that wizard setup can initialize OpenAI-compatible providers
with custom API endpoints (base URL), API keys, and model names.
"""

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, call


_INIT_PATH = Path(__file__).resolve().parents[1] / "init.py"
_SPEC = importlib.util.spec_from_file_location("advanced_init", _INIT_PATH)
_MODULE = importlib.util.module_from_spec(_SPEC)
assert _SPEC and _SPEC.loader
_SPEC.loader.exec_module(_MODULE)
ChronicleSetup = _MODULE.ChronicleSetup


def _build_setup_with_mocks() -> ChronicleSetup:
    """Create ChronicleSetup instance without running __init__ side effects."""
    setup = ChronicleSetup.__new__(ChronicleSetup)
    setup.console = MagicMock()
    setup.config = {}
    setup.config_manager = MagicMock()
    setup.print_section = MagicMock()
    return setup


def test_upsert_openai_models_updates_existing_defs_and_defaults():
    """Checks OpenAI custom API config upsert in init flow.

    Verifies that init setup updates OpenAI model definitions with custom API
    settings and switches defaults to those OpenAI entries.
    """
    setup = _build_setup_with_mocks()
    setup.config_manager.get_full_config.return_value = {
        "defaults": {"llm": "local-llm", "embedding": "local-embed"},
        "models": [
            {
                "name": "openai-llm",
                "model_type": "llm",
                "model_provider": "openai",
                "model_name": "gpt-4o-mini",
                "model_url": "https://api.openai.com/v1",
                "api_key": "old-key",
                "model_params": {"temperature": 0.3},
            },
            {
                "name": "openai-embed",
                "model_type": "embedding",
                "model_provider": "openai",
                "model_name": "text-embedding-3-small",
                "model_url": "https://api.openai.com/v1",
                "api_key": "old-key",
                "embedding_dimensions": 1536,
            },
        ],
    }

    setup._upsert_openai_models(
        api_key="new-key",
        base_url="http://custom.example/v1",
        llm_model_name="gpt-oss-20b",
        embedding_model_name="text-embedding-3-large",
    )

    saved_config = setup.config_manager.save_full_config.call_args[0][0]
    saved_models = {m["name"]: m for m in saved_config["models"]}

    assert saved_config["defaults"]["llm"] == "openai-llm"
    assert saved_config["defaults"]["embedding"] == "openai-embed"

    assert saved_models["openai-llm"]["model_url"] == "http://custom.example/v1"
    assert saved_models["openai-llm"]["api_key"] == "new-key"
    assert saved_models["openai-llm"]["model_name"] == "gpt-oss-20b"
    # Existing params are preserved and missing defaults are filled.
    assert saved_models["openai-llm"]["model_params"]["temperature"] == 0.3
    assert saved_models["openai-llm"]["model_params"]["max_tokens"] == 2000

    assert saved_models["openai-embed"]["model_url"] == "http://custom.example/v1"
    assert saved_models["openai-embed"]["api_key"] == "new-key"
    assert saved_models["openai-embed"]["model_name"] == "text-embedding-3-large"
    # Existing embedding dimensions are preserved.
    assert saved_models["openai-embed"]["embedding_dimensions"] == 1536


def test_setup_llm_openai_prompts_for_custom_values_and_updates_models():
    """Checks init OpenAI setup prompts for custom API initialization values."""
    setup = _build_setup_with_mocks()
    setup.prompt_choice = MagicMock(return_value="1")
    setup.prompt_value = MagicMock(
        side_effect=["http://my-openai-compatible/v1", "my-chat-model", "my-embed-model"]
    )
    setup.prompt_with_existing_masked = MagicMock(return_value="test-api-key")
    setup._upsert_openai_models = MagicMock()
    setup.config_manager.get_full_config.return_value = {
        "models": [
            {"name": "openai-llm", "model_url": "https://api.openai.com/v1", "model_name": "gpt-4o-mini"},
            {"name": "openai-embed", "model_url": "https://api.openai.com/v1", "model_name": "text-embedding-3-small"},
        ]
    }

    setup.setup_llm()

    setup.prompt_value.assert_has_calls(
        [
            call("OpenAI-compatible base URL", "https://api.openai.com/v1"),
            call("LLM model name", "gpt-4o-mini"),
            call("Embedding model name", "text-embedding-3-small"),
        ]
    )
    setup._upsert_openai_models.assert_called_once_with(
        api_key="test-api-key",
        base_url="http://my-openai-compatible/v1",
        llm_model_name="my-chat-model",
        embedding_model_name="my-embed-model",
    )
    assert setup.config["OPENAI_API_KEY"] == "test-api-key"


def test_setup_llm_openai_skips_upsert_when_api_key_missing():
    """Checks init OpenAI custom API setup guards against missing API key."""
    setup = _build_setup_with_mocks()
    setup.prompt_choice = MagicMock(return_value="1")
    setup.prompt_value = MagicMock(
        side_effect=["https://api.openai.com/v1", "gpt-4o-mini", "text-embedding-3-small"]
    )
    setup.prompt_with_existing_masked = MagicMock(return_value="")
    setup._upsert_openai_models = MagicMock()
    setup.config_manager.get_full_config.return_value = {"models": []}

    setup.setup_llm()

    setup._upsert_openai_models.assert_not_called()
    assert "OPENAI_API_KEY" not in setup.config
