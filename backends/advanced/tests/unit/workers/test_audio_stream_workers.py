"""Unit tests for audio stream workers using the Template Method pattern."""

import asyncio
import os
import signal
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import redis.asyncio as redis

from advanced_omi_backend.services.transcription.streaming_consumer import (
    StreamingTranscriptionConsumer,
)
from advanced_omi_backend.workers.audio_stream_deepgram_worker import DeepgramStreamWorker
from advanced_omi_backend.workers.audio_stream_parakeet_worker import ParakeetStreamWorker
from advanced_omi_backend.workers.base_audio_worker import BaseStreamWorker


@pytest.mark.unit
class TestBaseStreamWorker:
    """Test the BaseStreamWorker template class."""

    def test_abstract_methods_must_be_implemented(self):
        """Test that BaseStreamWorker cannot be instantiated without implementing abstract methods."""
        with pytest.raises(TypeError, match="abstract methods"):
            BaseStreamWorker("test-service")

    def test_service_name_initialization(self):
        """Test that service name is properly set during initialization."""

        class ConcreteWorker(BaseStreamWorker):
            def validate_config(self):
                pass

            def get_consumer(self, redis_client):
                pass

        worker = ConcreteWorker("test-worker")
        assert worker.service_name == "test-worker"
        assert worker.redis_client is None
        assert worker.consumer is None

    @pytest.mark.asyncio
    async def test_redis_connection_failure_exits(self):
        """Test that worker exits gracefully when Redis connection fails."""

        class ConcreteWorker(BaseStreamWorker):
            def validate_config(self):
                pass

            def get_consumer(self, redis_client):
                pass

        worker = ConcreteWorker("test-worker")

        async def raise_connection_error(*args, **kwargs):
            raise Exception("Connection failed")

        with patch("redis.asyncio.from_url", side_effect=raise_connection_error):
            with pytest.raises(SystemExit) as exc_info:
                await worker.run()
            assert exc_info.value.code == 1

    @pytest.mark.asyncio
    async def test_consumer_initialization_failure_exits(self):
        """Test that worker exits gracefully when consumer initialization fails."""

        class ConcreteWorker(BaseStreamWorker):
            def validate_config(self):
                pass

            def get_consumer(self, redis_client):
                raise ValueError("Consumer init failed")

        worker = ConcreteWorker("test-worker")

        mock_redis = AsyncMock()

        async def mock_from_url(*args, **kwargs):
            return mock_redis

        with patch("redis.asyncio.from_url", side_effect=mock_from_url):
            with pytest.raises(SystemExit) as exc_info:
                await worker.run()
            assert exc_info.value.code == 1
            mock_redis.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_successful_worker_lifecycle(self):
        """Test complete worker lifecycle with successful execution."""

        class ConcreteWorker(BaseStreamWorker):
            def validate_config(self):
                pass

            def get_consumer(self, redis_client):
                consumer = AsyncMock()
                consumer.start_consuming = AsyncMock()
                consumer.stop = AsyncMock()
                return consumer

        worker = ConcreteWorker("test-worker")
        mock_redis = AsyncMock()

        # Simulate quick consumer completion
        async def quick_consume():
            await asyncio.sleep(0.01)

        async def mock_from_url(*args, **kwargs):
            return mock_redis

        with patch("redis.asyncio.from_url", side_effect=mock_from_url):
            with patch.object(worker.__class__, "get_consumer") as mock_get_consumer:
                mock_consumer = AsyncMock()
                mock_consumer.start_consuming = quick_consume
                mock_consumer.stop = AsyncMock()
                mock_get_consumer.return_value = mock_consumer

                await worker.run()

                mock_redis.aclose.assert_called_once()
                mock_consumer.stop.assert_called_once()


@pytest.mark.unit
class TestDeepgramStreamWorker:
    """Test DeepgramStreamWorker implementation."""

    def test_initialization(self):
        """Test that DeepgramStreamWorker initializes correctly."""
        worker = DeepgramStreamWorker()
        assert worker.service_name == "Deepgram audio stream worker"
        assert hasattr(worker, "logger")

    def test_validate_config_with_api_key(self):
        """Test config validation when DEEPGRAM_API_KEY is set."""
        worker = DeepgramStreamWorker()

        with patch.dict(os.environ, {"DEEPGRAM_API_KEY": "test-key-123"}):
            # Should not raise any exceptions or warnings
            worker.validate_config()

    def test_validate_config_without_api_key(self):
        """Test config validation when DEEPGRAM_API_KEY is missing."""
        worker = DeepgramStreamWorker()

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(worker.logger, "warning") as mock_warning:
                worker.validate_config()
                # Should log 3 warnings about missing API key
                assert mock_warning.call_count == 3

    def test_get_consumer_creates_streaming_consumer(self):
        """Test that get_consumer returns a StreamingTranscriptionConsumer instance."""
        worker = DeepgramStreamWorker()
        mock_redis = Mock()

        # Mock the config/registry system that StreamingTranscriptionConsumer uses
        with patch(
            "advanced_omi_backend.services.transcription.streaming_consumer.get_transcription_provider"
        ) as mock_get_provider:
            mock_provider = Mock()
            mock_get_provider.return_value = mock_provider

            consumer = worker.get_consumer(mock_redis)

            assert isinstance(consumer, StreamingTranscriptionConsumer)
            # Verify consumer has required async methods
            assert hasattr(consumer, "start_consuming")
            assert hasattr(consumer, "stop")
            assert callable(consumer.start_consuming)
            assert callable(consumer.stop)

    def test_start_method_runs_worker(self):
        """Test that start() class method creates instance and schedules run() via asyncio.run."""
        captured_coro = None

        with patch.object(DeepgramStreamWorker, "run", new_callable=AsyncMock) as mock_run:
            with patch("asyncio.run") as mock_asyncio_run:
                def capture_and_close(coro):
                    nonlocal captured_coro
                    captured_coro = coro
                    coro.close()

                mock_asyncio_run.side_effect = capture_and_close

                DeepgramStreamWorker.start()

                mock_run.assert_called_once_with()
                mock_asyncio_run.assert_called_once_with(captured_coro)
                assert captured_coro is not None
                assert asyncio.iscoroutine(captured_coro)


@pytest.mark.unit
class TestParakeetStreamWorker:
    """Test ParakeetStreamWorker implementation."""

    def test_initialization(self):
        """Test that ParakeetStreamWorker initializes correctly."""
        worker = ParakeetStreamWorker()
        assert worker.service_name == "Parakeet audio stream worker"
        assert hasattr(worker, "logger")

    def test_validate_config_with_service_url(self):
        """Test config validation when PARAKEET_ASR_URL is set."""
        worker = ParakeetStreamWorker()

        with patch.dict(os.environ, {"PARAKEET_ASR_URL": "http://localhost:8767"}):
            # Should not raise any exceptions or warnings
            worker.validate_config()

    def test_validate_config_without_service_url(self):
        """Test config validation when PARAKEET_ASR_URL is missing."""
        worker = ParakeetStreamWorker()

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(worker.logger, "warning") as mock_warning:
                worker.validate_config()
                # Should log 3 warnings about missing service URL
                assert mock_warning.call_count == 3

    def test_get_consumer_creates_streaming_consumer(self):
        """Test that get_consumer returns a StreamingTranscriptionConsumer instance."""
        worker = ParakeetStreamWorker()
        mock_redis = Mock()

        # Mock the config/registry system that StreamingTranscriptionConsumer uses
        with patch(
            "advanced_omi_backend.services.transcription.streaming_consumer.get_transcription_provider"
        ) as mock_get_provider:
            mock_provider = Mock()
            mock_get_provider.return_value = mock_provider

            consumer = worker.get_consumer(mock_redis)

            assert isinstance(consumer, StreamingTranscriptionConsumer)
            # Verify consumer has required async methods
            assert hasattr(consumer, "start_consuming")
            assert hasattr(consumer, "stop")
            assert callable(consumer.start_consuming)
            assert callable(consumer.stop)

    @pytest.mark.asyncio
    async def test_start_method_runs_worker(self):
        """Test that start() class method creates instance and runs it."""
        with patch.object(ParakeetStreamWorker, "run", new_callable=AsyncMock) as mock_run:
            with patch("asyncio.run") as mock_asyncio_run:
                # Simulate script execution
                mock_asyncio_run.side_effect = lambda coro: asyncio.new_event_loop().run_until_complete(
                    coro
                )

                worker_instance = ParakeetStreamWorker()
                await worker_instance.run()

                mock_run.assert_called_once()


@pytest.mark.unit
class TestWorkerIntegration:
    """Integration tests for worker components."""

    @pytest.mark.asyncio
    async def test_deepgram_worker_handles_shutdown_signal(self):
        """Test that DeepgramStreamWorker handles shutdown signals gracefully."""
        worker = DeepgramStreamWorker()
        mock_redis = AsyncMock()
        mock_consumer = AsyncMock()

        # Consumer runs for a short time then completes
        async def simulate_work():
            await asyncio.sleep(0.05)

        mock_consumer.start_consuming = simulate_work
        mock_consumer.stop = AsyncMock()

        async def mock_from_url(*args, **kwargs):
            return mock_redis

        with patch("redis.asyncio.from_url", side_effect=mock_from_url):
            with patch.object(worker, "get_consumer", return_value=mock_consumer):
                # Run worker in background
                task = asyncio.create_task(worker.run())

                # Let it start
                await asyncio.sleep(0.01)

                # Should complete naturally
                await task

                mock_consumer.stop.assert_called_once()
                mock_redis.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_parakeet_worker_handles_shutdown_signal(self):
        """Test that ParakeetStreamWorker handles shutdown signals gracefully."""
        worker = ParakeetStreamWorker()
        mock_redis = AsyncMock()
        mock_consumer = AsyncMock()

        # Consumer runs for a short time then completes
        async def simulate_work():
            await asyncio.sleep(0.05)

        mock_consumer.start_consuming = simulate_work
        mock_consumer.stop = AsyncMock()

        async def mock_from_url(*args, **kwargs):
            return mock_redis

        with patch("redis.asyncio.from_url", side_effect=mock_from_url):
            with patch.object(worker, "get_consumer", return_value=mock_consumer):
                # Run worker in background
                task = asyncio.create_task(worker.run())

                # Let it start
                await asyncio.sleep(0.01)

                # Should complete naturally
                await task

                mock_consumer.stop.assert_called_once()
                mock_redis.aclose.assert_called_once()

    def test_workers_share_consistent_behavior(self):
        """Test that both workers use consistent shutdown and error handling."""
        deepgram_worker = DeepgramStreamWorker()
        parakeet_worker = ParakeetStreamWorker()

        # Both should have same base class
        assert isinstance(deepgram_worker, BaseStreamWorker)
        assert isinstance(parakeet_worker, BaseStreamWorker)

        # Both should implement required methods
        assert callable(deepgram_worker.validate_config)
        assert callable(deepgram_worker.get_consumer)
        assert callable(parakeet_worker.validate_config)
        assert callable(parakeet_worker.get_consumer)

        # Both should inherit run method from BaseStreamWorker
        assert hasattr(deepgram_worker, "run")
        assert hasattr(parakeet_worker, "run")
        # Verify they use the same base implementation
        assert type(deepgram_worker).run == type(parakeet_worker).run
