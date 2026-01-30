"""
Placeholder anomaly detection script.

This will be a cron job which uses some kind of algorithm to detect if transcription
is bad. It scans MongoDB for transcripts that don't have the maybe_anomaly flag set,
runs the detection in run_anomaly_detection(), and sets maybe_anomaly to True for
transcripts that look anomalous (placeholder - currently always marks as true).
"""

import asyncio
import os
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

# MongoDB Configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = "chronicle"

async def run_anomaly_detection():
    """Run anomaly detection on all transcripts without maybe_anomaly flag."""
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DB_NAME]
    
    print("🔍 Starting anomaly detection scan...")
    
    try:
        # Find conversations with transcript versions where maybe_anomaly is not set
        cursor = db.conversations.find({
            "deleted": False,
            "transcript_versions.maybe_anomaly": None  # Find transcripts without flag
        })
        
        count = 0
        conversations = await cursor.to_list(length=100)
        
        for conversation in conversations:
            transcript_versions = conversation.get("transcript_versions", [])
            
            for version in transcript_versions:
                if version.get("maybe_anomaly") is None:
                    # Mark as potential anomaly (placeholder - always returns true)
                    version_id = version.get("version_id")
                    
                    result = await db.conversations.update_one(
                        {
                            "conversation_id": conversation["conversation_id"],
                            "transcript_versions.version_id": version_id
                        },
                        {
                            "$set": {
                                "transcript_versions.$.maybe_anomaly": True
                            }
                        }
                    )
                    
                    if result.matched_count > 0:
                        count += 1
                        print(f"✅ Marked version {version_id} as potential anomaly")
        
        print(f"🎉 Scan complete! Marked {count} transcripts as potential anomalies")
        
        # Also count total anomalies
        anomaly_count = await db.conversations.count_documents({
            "deleted": False,
            "transcript_versions.maybe_anomaly": True
        })
        print(f"📊 Total potential anomalies in system: {anomaly_count}")
        
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(run_anomaly_detection())
