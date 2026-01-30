"""
User-loop helper functions for Robot Framework tests.
Provides MongoDB CRUD operations for user-loop tests.
"""

import os
import time
from pathlib import Path
from pymongo import MongoClient
from dotenv import load_dotenv
from bson import ObjectId

# Load test environment variables
tests_dir = Path(__file__).parent.parent
load_dotenv(tests_dir / ".env.test", override=False)


def get_mongodb_uri():
    """Get MongoDB URI from environment."""
    # docker-compose-test.yml maps MongoDB to localhost:27018
    return os.getenv("MONGODB_URI", "mongodb://localhost:27018")


def get_db_name():
    """Get database name from environment."""
    return os.getenv("TEST_DB_NAME", "test_db")


def connect_to_mongodb():
    """Connect to MongoDB and return client and db."""
    client = MongoClient(get_mongodb_uri())
    db = client[get_db_name()]
    return client, db


def disconnect_from_mongodb(client):
    """Disconnect from MongoDB."""
    if client:
        client.close()


def _to_boolean(value):
    """Convert string 'true'/'false' to boolean."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return bool(value)


def insert_test_conversation(conv_id, version_id, maybe_anomaly):
    """
    Insert test conversation into MongoDB with all required fields.

    Args:
        conv_id: Conversation ID
        version_id: Version ID
        maybe_anomaly: Value for maybe_anomaly (True/False/"verified")

    Returns:
        MongoDB insert result
    """
    client, db = connect_to_mongodb()
    try:
        timestamp = int(time.time())
        # Convert string to boolean
        maybe_anomaly_bool = _to_boolean(maybe_anomaly)
        
        # Create complete conversation document with all required fields
        data = {
            "conversation_id": conv_id,
            "user_id": "test-user-id",  # Required field
            "client_id": "test-client-id",  # Required field
            "deleted": False,
            "created_at": timestamp,
            "transcript_versions": [{
                "version_id": version_id,
                "transcript": "Test transcript",
                "maybe_anomaly": maybe_anomaly_bool,
                "created_at": timestamp,  # Required field
                "segments": [],
                "metadata": {"word_count": 5}
            }],
            "audio_chunks_count": 1,
            "audio_total_duration": 10.0,
            "active_transcript_version": version_id,
            "title": f"Test Conversation {conv_id}",
            "summary": "Test summary",
            "detailed_summary": None,
            "memory_versions": [],
            "active_memory_version": None,
            "completed_at": None,
            "end_reason": None,
            "deletion_reason": None,
            "deleted_at": None,
            "external_source_id": None,
            "external_source_type": None
        }
        result = db.conversations.insert_one(data)
        return result
    finally:
        disconnect_from_mongodb(client)


def delete_test_conversation(conv_id):
    """
    Delete test conversation from MongoDB.

    Args:
        conv_id: Conversation ID to delete

    Returns:
        MongoDB delete result
    """
    client, db = connect_to_mongodb()
    try:
        result = db.conversations.delete_one({"conversation_id": conv_id})
        return result
    finally:
        disconnect_from_mongodb(client)


def get_test_conversation(conv_id):
    """
    Get test conversation from MongoDB.

    Args:
        conv_id: Conversation ID to get

    Returns:
        Conversation document or None
    """
    client, db = connect_to_mongodb()
    try:
        doc = db.conversations.find_one({"conversation_id": conv_id})
        return doc
    finally:
        disconnect_from_mongodb(client)


def insert_test_audio_chunk(conv_id, chunk_index, audio_data):
    """
    Insert test audio chunk into MongoDB.

    Args:
        conv_id: Conversation ID
        chunk_index: Chunk index
        audio_data: Audio data (bytes or string)

    Returns:
        MongoDB insert result
    """
    client, db = connect_to_mongodb()
    try:
        data = {
            "conversation_id": conv_id,
            "chunk_index": chunk_index,
            "audio_data": audio_data
        }
        result = db.audio_chunks.insert_one(data)
        return result
    finally:
        disconnect_from_mongodb(client)


def delete_test_audio_chunks(conv_id):
    """Delete all audio chunks for a test conversation."""
    client, db = connect_to_mongodb()
    try:
        return db.audio_chunks.delete_many({"conversation_id": conv_id})
    finally:
        disconnect_from_mongodb(client)


def get_training_stash_entry(stash_id):
    """
    Get training stash entry from MongoDB.

    Args:
        stash_id: Stash ID to get

    Returns:
        Stash document or None
    """
    client, db = connect_to_mongodb()
    try:
        doc = db.training_stash.find_one({"_id": ObjectId(stash_id)})
        return doc
    finally:
        disconnect_from_mongodb(client)


def delete_training_stash_entry(stash_id):
    """
    Delete training stash entry from MongoDB.

    Args:
        stash_id: Stash ID to delete

    Returns:
        MongoDB delete result
    """
    client, db = connect_to_mongodb()
    try:
        result = db.training_stash.delete_one({"_id": ObjectId(stash_id)})
        return result
    finally:
        disconnect_from_mongodb(client)


def get_timestamp():
    """Get current timestamp (epoch)."""
    return int(time.time())
