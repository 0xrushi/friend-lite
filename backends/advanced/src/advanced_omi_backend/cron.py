import asyncio
import logging
import os
from datetime import datetime
import signal
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger("cron_scheduler")

from advanced_omi_backend.workers.annotation_jobs import surface_error_suggestions, finetune_hallucination_model
from advanced_omi_backend.database import init_db

# Frequency configuration (in seconds)
SUGGESTION_INTERVAL = 24 * 60 * 60 # Daily
TRAINING_INTERVAL = 7 * 24 * 60 * 60 # Weekly

# For testing purposes, we can check more frequently if ENV var is set
if os.getenv("DEV_MODE", "false").lower() == "true":
    SUGGESTION_INTERVAL = 60 # 1 minute
    TRAINING_INTERVAL = 300 # 5 minutes

async def run_scheduler():
    logger.info("Starting Cron Scheduler...")
    
    # Initialize DB connection
    await init_db()
    
    last_suggestion_run = datetime.min
    last_training_run = datetime.min
    
    while True:
        now = datetime.utcnow()
        
        # Check Suggestions Job
        if (now - last_suggestion_run).total_seconds() >= SUGGESTION_INTERVAL:
            logger.info("Running scheduled job: surface_error_suggestions")
            try:
                await surface_error_suggestions()
                last_suggestion_run = now
            except Exception as e:
                logger.error(f"Error in surface_error_suggestions: {e}", exc_info=True)
                
        # Check Training Job
        if (now - last_training_run).total_seconds() >= TRAINING_INTERVAL:
            logger.info("Running scheduled job: finetune_hallucination_model")
            try:
                await finetune_hallucination_model()
                last_training_run = now
            except Exception as e:
                logger.error(f"Error in finetune_hallucination_model: {e}", exc_info=True)
        
        # Sleep for a bit before next check (e.g. 1 minute)
        await asyncio.sleep(60)

def handle_shutdown(signum, frame):
    logger.info("Shutting down Cron Scheduler...")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
    
    try:
        asyncio.run(run_scheduler())
    except KeyboardInterrupt:
        pass
