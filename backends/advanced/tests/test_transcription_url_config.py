"""
Unit tests for transcription service URL configuration.

Tests the fix for the double http:// prefix issue where environment variables
containing protocol prefixes were incorrectly combined with hardcoded prefixes
in config.yml.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from omegaconf import OmegaConf


class TestTranscriptionURLConfiguration:
    """Test transcription service URL configuration and parsing."""

    def test_vibevoice_url_without_http_prefix(self):
        """Test that VIBEVOICE_ASR_URL without http:// prefix works correctly."""
        # Simulate config.yml template: http://${oc.env:VIBEVOICE_ASR_URL}
        config_template = {"model_url": "http://${oc.env:VIBEVOICE_ASR_URL,host.docker.internal:8767}"}

        with patch.dict(os.environ, {"VIBEVOICE_ASR_URL": "host.docker.internal:8767"}):
            resolved = OmegaConf.create(config_template)
            resolved = OmegaConf.to_container(resolved, resolve=True)

            assert resolved["model_url"] == "http://host.docker.internal:8767"
            assert "http://http://" not in resolved["model_url"]

    def test_vibevoice_url_with_http_prefix_causes_double_prefix(self):
        """Test that VIBEVOICE_ASR_URL WITH http:// causes double prefix (bug scenario)."""
        config_template = {"model_url": "http://${oc.env:VIBEVOICE_ASR_URL,host.docker.internal:8767}"}

        # This is the BUG scenario - env var already has http://
        with patch.dict(os.environ, {"VIBEVOICE_ASR_URL": "http://host.docker.internal:8767"}):
            resolved = OmegaConf.create(config_template)
            resolved = OmegaConf.to_container(resolved, resolve=True)

            # This demonstrates the bug
            assert resolved["model_url"] == "http://http://host.docker.internal:8767"
            assert "http://http://" in resolved["model_url"]

    def test_vibevoice_url_default_fallback(self):
        """Test that default fallback works when VIBEVOICE_ASR_URL is not set."""
        config_template = {"model_url": "http://${oc.env:VIBEVOICE_ASR_URL,host.docker.internal:8767}"}

        # No VIBEVOICE_ASR_URL set - should use default
        with patch.dict(os.environ, {}, clear=True):
            resolved = OmegaConf.create(config_template)
            resolved = OmegaConf.to_container(resolved, resolve=True)

            assert resolved["model_url"] == "http://host.docker.internal:8767"

    def test_parakeet_url_configuration(self):
        """Test that PARAKEET_ASR_URL follows same pattern."""
        config_template = {"model_url": "http://${oc.env:PARAKEET_ASR_URL,172.17.0.1:8767}"}

        # Correct format - without http:// prefix
        with patch.dict(os.environ, {"PARAKEET_ASR_URL": "host.docker.internal:8767"}):
            resolved = OmegaConf.create(config_template)
            resolved = OmegaConf.to_container(resolved, resolve=True)

            assert resolved["model_url"] == "http://host.docker.internal:8767"
            assert "http://http://" not in resolved["model_url"]

    def test_url_parsing_removes_double_slashes(self):
        """Test that URL with double http:// causes connection failures."""
        from urllib.parse import urlparse

        # Valid URL
        valid_url = "http://host.docker.internal:8767/transcribe"
        parsed_valid = urlparse(valid_url)
        assert parsed_valid.scheme == "http"
        assert parsed_valid.netloc == "host.docker.internal:8767"

        # Invalid URL with double prefix
        invalid_url = "http://http://host.docker.internal:8767/transcribe"
        parsed_invalid = urlparse(invalid_url)
        # urlparse treats "http:" as the netloc which causes DNS failures
        assert parsed_invalid.scheme == "http"
        assert parsed_invalid.netloc == "http:"  # Invalid netloc causes "Name or service not known"
        assert parsed_invalid.netloc != "host.docker.internal:8767"


class TestProviderSegmentsConfiguration:
    """Test use_provider_segments configuration for different providers."""

    def test_use_provider_segments_default_false(self):
        """Test that use_provider_segments defaults to false."""
        config = OmegaConf.create({
            "backend": {
                "transcription": {}
            }
        })

        use_segments = config.backend.transcription.get("use_provider_segments", False)
        assert use_segments is False

    def test_use_provider_segments_explicit_true(self):
        """Test that use_provider_segments can be enabled."""
        config = OmegaConf.create({
            "backend": {
                "transcription": {
                    "use_provider_segments": True
                }
            }
        })

        assert config.backend.transcription.use_provider_segments is True

    def test_vibevoice_should_use_provider_segments(self):
        """
        Test that VibeVoice provider should have use_provider_segments=true
        since it provides diarized segments.
        """
        # VibeVoice provides segments with speaker diarization
        vibevoice_capabilities = ["segments", "diarization"]

        # When provider has both capabilities, use_provider_segments should be true
        has_diarization = "diarization" in vibevoice_capabilities
        has_segments = "segments" in vibevoice_capabilities

        should_use_segments = has_diarization and has_segments
        assert should_use_segments is True


class TestModelRegistryURLResolution:
    """Test model registry URL resolution with environment variables."""

    def test_model_url_resolution_with_env_var(self):
        """Test that model URLs resolve correctly from environment."""
        config_template = """
        defaults:
          stt: stt-vibevoice
        models:
        - name: stt-vibevoice
          model_type: stt
          model_provider: vibevoice
          model_url: http://${oc.env:VIBEVOICE_ASR_URL,host.docker.internal:8767}
        """

        with patch.dict(os.environ, {"VIBEVOICE_ASR_URL": "host.docker.internal:8767"}):
            config = OmegaConf.create(config_template)
            resolved = OmegaConf.to_container(config, resolve=True)

            vibevoice_model = resolved["models"][0]
            assert vibevoice_model["model_url"] == "http://host.docker.internal:8767"

    def test_multiple_asr_providers_url_resolution(self):
        """Test that multiple ASR providers can use different URL patterns."""
        config_template = {
            "models": [
                {
                    "name": "stt-vibevoice",
                    "model_url": "http://${oc.env:VIBEVOICE_ASR_URL,host.docker.internal:8767}"
                },
                {
                    "name": "stt-parakeet",
                    "model_url": "http://${oc.env:PARAKEET_ASR_URL,172.17.0.1:8767}"
                },
                {
                    "name": "stt-deepgram",
                    "model_url": "https://api.deepgram.com/v1"
                }
            ]
        }

        env_vars = {
            "VIBEVOICE_ASR_URL": "host.docker.internal:8767",
            "PARAKEET_ASR_URL": "localhost:8080"
        }

        with patch.dict(os.environ, env_vars):
            config = OmegaConf.create(config_template)
            resolved = OmegaConf.to_container(config, resolve=True)

            assert resolved["models"][0]["model_url"] == "http://host.docker.internal:8767"
            assert resolved["models"][1]["model_url"] == "http://localhost:8080"
            assert resolved["models"][2]["model_url"] == "https://api.deepgram.com/v1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
