# Test Environment Configuration
import os
from pathlib import Path
from dotenv import load_dotenv

# Determine environment type: 'test' (default) or 'normal'
ENV_TYPE = os.getenv('ENV_TYPE', 'test')

# Project paths - absolute paths that work from any working directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # friend-lite root
TESTS_DIR = Path(__file__).resolve().parents[1]      # tests directory
BACKENDS_ADVANCED_DIR = PROJECT_ROOT / "backends" / "advanced"

# Load appropriate .env file based on ENV_TYPE
if ENV_TYPE == 'normal':
    env_file = TESTS_DIR / ".env.normal"
    # Also load the main .env from backends/advanced
    main_env = BACKENDS_ADVANCED_DIR / ".env"
    load_dotenv(main_env)  # Load main env first
    load_dotenv(env_file, override=True)  # Override with test-specific settings
else:  # test (default)
    env_file = TESTS_DIR / ".env.test"
    load_dotenv(env_file)

# Convert to strings for Robot Framework
PROJECT_ROOT_STR = str(PROJECT_ROOT)
BACKENDS_ADVANCED_DIR_STR = str(BACKENDS_ADVANCED_DIR)

# Environment-specific configurations
if ENV_TYPE == 'normal':
    # Normal environment (production-like)
    API_PORT = '8000'
    FRONTEND_PORT = '5173'
    COMPOSE_FILE = 'docker-compose.yml'
    MONGO_PORT = '27017'
    QDRANT_PORT = '6333'
else:  # test
    # Test environment (isolated)
    API_PORT = '8001'
    FRONTEND_PORT = '3001'
    COMPOSE_FILE = 'docker-compose-test.yml'
    MONGO_PORT = '27018'
    QDRANT_PORT = '6337'

# API Configuration
API_URL = os.getenv('BACKEND_URL', f'http://localhost:{API_PORT}')
API_BASE = f'{API_URL}/api'
SPEAKER_RECOGNITION_URL = 'http://localhost:8085'  # Speaker recognition service

WEB_URL = os.getenv('FRONTEND_URL', f'http://localhost:{FRONTEND_PORT}')

# Admin user credentials (Robot Framework format)
ADMIN_USER = {
    "email": os.getenv('ADMIN_EMAIL', 'test-admin@example.com'),
    "password": os.getenv('ADMIN_PASSWORD', 'test-admin-password-123')
}

# Individual variables for Robot Framework
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'test-admin@example.com')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'test-admin-password-123')

TEST_USER = {
    "email": "test@example.com",
    "password": "test-password"
}

# Individual variables for Robot Framework
TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "test-password"



# API Endpoints
ENDPOINTS = {
    "health": "/health",
    "readiness": "/readiness",
    "auth": "/auth/jwt/login",
    "conversations": "/api/conversations",
    "memories": "/api/memories",
    "memory_search": "/api/memories/search",
    "users": "/api/users"
}

# API Keys (loaded from test.env)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY')
HF_TOKEN = os.getenv('HF_TOKEN')

# Test Configuration
TEST_CONFIG = {
    "retry_count": 3,
    "retry_delay": 1,
    "default_timeout": 30
}