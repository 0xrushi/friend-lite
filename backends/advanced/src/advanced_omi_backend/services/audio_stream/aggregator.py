"""
Transcription results aggregator - reads results from Redis Streams.
"""

import json
import logging

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class TranscriptionResultsAggregator:
    """
    Reads transcription results from Redis Streams.

    Results are in: transcription:results:{session_id}
    """

    def __init__(self, redis_client: redis.Redis):
        """
        Initialize aggregator.

        Args:
            redis_client: Connected Redis client
        """
        self.redis_client = redis_client

    async def get_session_results(self, session_id: str) -> list[dict]:
        """
        Get all transcription results for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of result dictionaries with text, confidence, provider, etc.
        """
        stream_name = f"transcription:results:{session_id}"

        try:
            # Read all messages from stream
            messages = await self.redis_client.xrange(stream_name)

            results = []
            for message_id, fields in messages:
                result = {
                    "message_id": message_id.decode(),
                    "text": fields[b"text"].decode(),
                    "confidence": float(fields[b"confidence"].decode()),
                    "provider": fields[b"provider"].decode(),
                    "chunk_id": fields.get(b"chunk_id", b"unknown").decode(),  # Handle missing chunk_id gracefully
                    "processing_time": float(fields.get(b"processing_time", b"0.0").decode()),
                    "timestamp": float(fields[b"timestamp"].decode()),
                }

                # Optional fields
                if b"words" in fields:
                    result["words"] = json.loads(fields[b"words"].decode())
                if b"segments" in fields:
                    result["segments"] = json.loads(fields[b"segments"].decode())

                results.append(result)

            # Sort by timestamp
            results.sort(key=lambda x: x["timestamp"])

            # Log detailed result info
            chunk_ids = [r["chunk_id"] for r in results]
            total_text_length = sum(len(r["text"]) for r in results)
            logger.debug(
                f"🔄 Retrieved {len(results)} results for session {session_id}: "
                f"chunks={chunk_ids}, total_text={total_text_length} chars"
            )
            return results

        except Exception as e:
            logger.error(f"🔄 Error getting results for session {session_id}: {e}")
            return []

    async def get_combined_results(self, session_id: str) -> dict:
        """
        Get all transcription results combined into a single aggregated result.

        Args:
            session_id: Session identifier

        Returns:
            Combined result dict with:
                - text: Full transcript (all chunks joined)
                - words: All words combined
                - segments: All segments combined and sorted
                - chunk_count: Number of chunks combined
                - total_confidence: Average confidence
                - provider: Provider name
        """
        # Get raw chunks
        results = await self.get_session_results(session_id)

        if not results:
            return {
                "text": "",
                "words": [],
                "segments": [],
                "chunk_count": 0,
                "total_confidence": 0.0,
                "provider": None
            }

        # For streaming providers (Deepgram), use ONLY the latest final result
        # Each is_final=true result supersedes interim results for the same speech segment
        # The latest result contains the most accurate transcription with best timing/confidence
        latest_result = results[-1]

        combined = {
            "text": latest_result.get("text", ""),
            "words": latest_result.get("words", []),
            "segments": latest_result.get("segments", []),
            "chunk_count": len(results),  # Track how many results were received
            "total_confidence": latest_result.get("confidence", 0.0),
            "provider": latest_result.get("provider")
        }

        logger.info(
            f"🔤 TRANSCRIPT [AGGREGATOR] session={session_id}, "
            f"total_results={len(results)}, words={len(combined['words'])}, "
            f"text=\"{combined['text']}\""
        )

        return combined

    async def get_realtime_results(
        self,
        session_id: str,
        last_id: str = "0",
        timeout_ms: int = 1000
    ) -> tuple[list[dict], str]:
        """
        Get new results since last_id (for real-time streaming).

        Args:
            session_id: Session identifier
            last_id: Last message ID received (use "0" to start from beginning)
            timeout_ms: Block timeout in milliseconds

        Returns:
            Tuple of (results list, new_last_id)
        """
        stream_name = f"transcription:results:{session_id}"

        try:
            # Read new messages since last_id
            messages = await self.redis_client.xread(
                {stream_name: last_id},
                count=10,
                block=timeout_ms
            )

            results = []
            new_last_id = last_id

            if messages:
                for _, msgs in messages:
                    for message_id, fields in msgs:
                        result = {
                            "message_id": message_id.decode(),
                            "text": fields[b"text"].decode(),
                            "confidence": float(fields[b"confidence"].decode()),
                            "provider": fields[b"provider"].decode(),
                            "chunk_id": fields.get(b"chunk_id", b"unknown").decode(),  # Handle missing chunk_id gracefully
                        }

                        # Optional fields
                        if b"words" in fields:
                            result["words"] = json.loads(fields[b"words"].decode())
                        if b"segments" in fields:
                            result["segments"] = json.loads(fields[b"segments"].decode())

                        results.append(result)
                        new_last_id = message_id.decode()

            return results, new_last_id

        except Exception as e:
            logger.error(f"🔄 Error getting realtime results for session {session_id}: {e}")
            return [], last_id
