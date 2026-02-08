"""
Base audio stream worker.

Provides a template for stream workers with consistent Redis connection,
signal handling, and error management.
"""

import asyncio
import logging
import os
import signal
import sys
from abc import ABC, abstractmethod

import redis.asyncio as redis

# Configure basic logging if not already configured
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

class BaseStreamWorker(ABC):
    """
    Base class for audio stream workers using the Template Method pattern.
    
    Subclasses must implement:
    - validate_config(): Check environment/config requirements
    - get_consumer(redis_client): Return the specific consumer instance
    """

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logging.getLogger(self.__class__.__name__)
        self.redis_client = None
        self.consumer = None

    @abstractmethod
    def validate_config(self):
        """
        Check required environment variables or configuration.
        Should log warnings/errors if configuration is missing.
        """
        pass

    @abstractmethod
    def get_consumer(self, redis_client):
        """
        Create and return the consumer instance.
        
        Args:
            redis_client: Initialized Redis client
            
        Returns:
            An instance complying with the BaseAudioStreamConsumer interface
        """
        pass

    async def run(self):
        """Main execution loop."""
        self.logger.info(f"🚀 Starting {self.service_name}")
        
        self.validate_config()

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        try:
            self.redis_client = await redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=False
            )
            self.logger.info("Connected to Redis")
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            sys.exit(1)

        try:
            self.consumer = self.get_consumer(self.redis_client)
        except Exception as e:
            self.logger.error(f"Failed to initialize consumer: {e}")
            await self.redis_client.aclose()
            sys.exit(1)

        # Setup graceful shutdown
        loop = asyncio.get_running_loop()
        stop_event = asyncio.Event()

        def signal_handler():
            self.logger.info("Received stop signal, shutting down...")
            stop_event.set()

        # Register signal handlers
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, signal_handler)
            except NotImplementedError:
                # Fallback for environments where add_signal_handler is not supported
                # (e.g. some Windows environments or custom loops)
                self.logger.warning(f"Could not add signal handler for {sig}")

        try:
            self.logger.info(f"✅ {self.service_name} ready")
            
            # Run consumer as a task
            consumer_task = asyncio.create_task(self.consumer.start_consuming())
            stop_wait_task = asyncio.create_task(stop_event.wait())

            # Wait for either the consumer to finish (error/done) or stop signal
            done, pending = await asyncio.wait(
                [consumer_task, stop_wait_task],
                return_when=asyncio.FIRST_COMPLETED
            )

            # Check if consumer failed
            if consumer_task in done:
                try:
                    await consumer_task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    self.logger.error(f"Consumer task failed: {e}", exc_info=True)
                    # We continue to cleanup

            # Trigger stop on consumer
            self.logger.info("Stopping consumer...")
            await self.consumer.stop()
            
            # Ensure consumer task finishes if it was running
            if consumer_task in pending:
                try:
                    await consumer_task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    # Ignore expected errors during shutdown if any
                    self.logger.debug(f"Consumer shutdown exception: {e}")

        except Exception as e:
            self.logger.error(f"Worker runtime error: {e}", exc_info=True)
            sys.exit(1)
        finally:
            if self.redis_client:
                await self.redis_client.aclose()
            self.logger.info(f"👋 {self.service_name} stopped")

    @classmethod
    def start(cls):
        """Entry point for script execution."""
        instance = cls()
        try:
            asyncio.run(instance.run())
        except KeyboardInterrupt:
            # Handle keyboard interrupt outside the loop if it propagates
            pass
