#!/usr/bin/env python3
"""Create a proper Mycelia API key (not OAuth client) for Friend-Lite user."""

import os
import sys
import secrets
import hashlib
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime

# MongoDB configuration
# When running with Docker Compose, MongoDB is on localhost:27017
# The script auto-detects the environment from backends/advanced/.env if available
MONGO_URL = os.getenv("MONGO_URL", os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
MYCELIA_DB = os.getenv("MYCELIA_DB", os.getenv("DATABASE_NAME", "mycelia"))

# User ID from JWT or argument (can be passed via command line or environment)
# This will be determined in main() after loading .env file
USER_ID = None


def hash_api_key_with_salt(api_key: str, salt: bytes) -> str:
    """Hash API key with salt (matches Mycelia's hashApiKey function)."""
    # SHA256(salt + apiKey) in base64
    import base64
    h = hashlib.sha256()
    h.update(salt)
    h.update(api_key.encode('utf-8'))
    return base64.b64encode(h.digest()).decode('utf-8')  # Use base64 like Mycelia


def load_env_from_file():
    """Load environment variables from environment file."""
    # Check if ENV_NAME is provided (from Makefile)
    env_name = os.getenv("ENV_NAME")

    if env_name:
        # Load from environments/<env_name>.env in project root
        # Script is at: backends/advanced/scripts/create_mycelia_api_key.py
        # Project root is: ../../.. from script location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.join(script_dir, "..", "..", "..")
        env_file = os.path.join(project_root, "environments", f"{env_name}.env")
        if os.path.exists(env_file):
            print(f"📄 Loading environment: {env_name}\n")
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    # Parse KEY=VALUE
                    if '=' in line:
                        key, value = line.split('=', 1)
                        # Remove quotes if present
                        value = value.strip('"').strip("'")
                        # Always override critical database variables from environment file
                        if key in ('MONGODB_DATABASE', 'MONGODB_URI', 'MONGO_URL', 'MYCELIA_DB'):
                            os.environ[key] = value
                        # Only set if not already in environment for other variables
                        elif key not in os.environ:
                            os.environ[key] = value

            # Also load from generated backends/advanced/.env.<env_name> to get calculated ports
            generated_env = os.path.join(script_dir, "..", f".env.{env_name}")
            if os.path.exists(generated_env):
                with open(generated_env, 'r') as f:
                    for line in f:
                        line = line.strip()
                        # Skip comments and empty lines
                        if not line or line.startswith('#'):
                            continue
                        # Parse KEY=VALUE
                        if '=' in line:
                            key, value = line.split('=', 1)
                            # Remove quotes if present
                            value = value.strip('"').strip("'")
                            # Load port variables from generated file
                            if 'PORT' in key and key not in os.environ:
                                os.environ[key] = value
            return
        else:
            print(f"⚠️  Environment file not found: {env_file}\n")

    # Fallback: try to load from backends/advanced/.env (symlink)
    env_file = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_file):
        print(f"📄 Loading environment from: {env_file}\n")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                # Parse KEY=VALUE
                if '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip('"').strip("'")
                    # Always override critical database variables from environment file
                    if key in ('MONGODB_DATABASE', 'MONGODB_URI', 'MONGO_URL', 'MYCELIA_DB'):
                        os.environ[key] = value
                    # Only set if not already in environment for other variables
                    elif key not in os.environ:
                        os.environ[key] = value
    else:
        print(f"ℹ️  No environment file found")
        print("   Run from Makefile: make mycelia-create-token")
        print("   Or start environment: ./start-env.sh <env-name>\n")


def main():
    # Try to load environment from backends/advanced/.env
    load_env_from_file()

    # Re-read configuration after loading .env file
    global MONGO_URL, MYCELIA_DB, USER_ID

    # Try to get MongoDB URL from environment
    MONGO_URL = os.getenv("MONGO_URL") or os.getenv("MONGODB_URI")

    # If not set, construct from MONGODB_DATABASE or use default
    if not MONGO_URL:
        mongodb_database = os.getenv("MONGODB_DATABASE", "friend-lite")
        MONGO_URL = f"mongodb://localhost:27017/{mongodb_database}"

    # Replace Docker/K8s hostnames with "localhost" when running from host
    if "mongo:27017" in MONGO_URL:
        MONGO_URL = MONGO_URL.replace("mongo:27017", "localhost:27017")
        print(f"ℹ️  Converted Docker MongoDB URL to localhost\n")
    elif "mongodb.root.svc.cluster.local" in MONGO_URL:
        # Kubernetes service hostname - replace with localhost
        MONGO_URL = MONGO_URL.replace("mongodb.root.svc.cluster.local:27017", "localhost:27017")
        print(f"ℹ️  Converted Kubernetes MongoDB URL to localhost\n")
    elif "mongodb://" in MONGO_URL and "localhost" not in MONGO_URL and "127.0.0.1" not in MONGO_URL:
        # Any other remote MongoDB URL - try to use localhost
        import re
        # Extract database name if present
        db_match = re.search(r'mongodb://[^/]+/([^?]+)', MONGO_URL)
        if db_match:
            db_name = db_match.group(1)
            MONGO_URL = f"mongodb://localhost:27017/{db_name}"
        else:
            MONGO_URL = "mongodb://localhost:27017"
        print(f"ℹ️  Using localhost MongoDB instead of remote URL\n")

    MYCELIA_DB = os.getenv("MYCELIA_DB", os.getenv("DATABASE_NAME", "mycelia"))

    # Determine USER_ID from command line arg, environment, or prompt
    USER_ID = os.getenv("USER_ID", None)
    if USER_ID is None and len(sys.argv) > 1:
        USER_ID = sys.argv[1]

    # If still no USER_ID, list available users and prompt
    if USER_ID is None:
        print("📋 Available users in Friend-Lite:")
        # Try to list users from the friend-lite database
        try:
            # Extract base URL without database name
            base_url = MONGO_URL.rsplit('/', 1)[0] if '/' in MONGO_URL else MONGO_URL

            # Get the Friend-Lite database name from environment
            # MONGODB_DATABASE is set in the environment file (e.g., "friend-lite-test2")
            friend_db = os.getenv("MONGODB_DATABASE", "friend-lite")

            print(f"   Database: {friend_db}")
            print()

            client = MongoClient(base_url, serverSelectionTimeoutMS=5000)
            db = client[friend_db]
            users = db["users"].find({}, {"_id": 1, "email": 1})
            user_list = list(users)

            if not user_list:
                print("   (No users found - create a user in Friend-Lite first)")
                client.close()
                return 1

            # Display users with numbers
            print()
            for idx, user in enumerate(user_list, 1):
                print(f"   {idx}) {user['email']} (ID: {user['_id']})")
            print()

            # Prompt for selection
            while True:
                try:
                    selection = input("Select user (number or enter USER_ID): ").strip()

                    # Try to parse as number (user selection)
                    try:
                        user_idx = int(selection) - 1
                        if 0 <= user_idx < len(user_list):
                            USER_ID = str(user_list[user_idx]['_id'])
                            print(f"✅ Selected: {user_list[user_idx]['email']}")
                            break
                        else:
                            print(f"❌ Invalid selection. Choose 1-{len(user_list)}")
                    except ValueError:
                        # Not a number, treat as USER_ID
                        if len(selection) == 24:  # MongoDB ObjectId length
                            USER_ID = selection
                            print(f"✅ Using USER_ID: {USER_ID}")
                            break
                        else:
                            print("❌ Invalid USER_ID format (should be 24 characters)")
                except KeyboardInterrupt:
                    print("\n\n❌ Cancelled by user")
                    client.close()
                    return 1

            client.close()
            print()
        except Exception as e:
            print(f"   ❌ Could not list users: {e}")
            print()
            return 1

    # Get Friend-Lite database name
    friend_db = os.getenv("MONGODB_DATABASE", "friend-lite")

    print(f"📊 MongoDB Configuration:")
    print(f"   URL: {MONGO_URL}")
    print(f"   Friend-Lite DB: {friend_db}")
    print(f"   Mycelia DB: {MYCELIA_DB}")
    print(f"   User ID: {USER_ID}")
    print()

    print("🔐 Creating Mycelia API Key\n")

    # Generate API key in Mycelia format: mycelia_{random_base64url}
    random_part = secrets.token_urlsafe(32)
    api_key = f"mycelia_{random_part}"

    # Generate salt (32 bytes)
    salt = secrets.token_bytes(32)

    # Hash the API key with salt
    hashed_key = hash_api_key_with_salt(api_key, salt)

    # Open prefix (first 16 chars for fast lookup)
    open_prefix = api_key[:16]

    print(f"✅ Generated API Key:")
    print(f"   Key: {api_key}")
    print(f"   Open Prefix: {open_prefix}")
    print(f"   Owner: {USER_ID}\n")

    # Connect to MongoDB
    client = MongoClient(MONGO_URL)
    db = client[MYCELIA_DB]
    api_keys = db["api_keys"]

    # Check for existing active keys for this user
    existing = api_keys.find_one({"owner": USER_ID, "isActive": True})
    if existing:
        print(f"ℹ️  Existing active API key found: {existing['_id']}")
        print(f"   Deactivating old key...\n")
        api_keys.update_one(
            {"_id": existing["_id"]},
            {"$set": {"isActive": False}}
        )

    # Create API key document (matches Mycelia's format)
    import base64
    api_key_doc = {
        "hashedKey": hashed_key,  # Note: hashedKey, not hash!
        "salt": base64.b64encode(salt).decode('utf-8'),  # Store as base64 like Mycelia
        "owner": USER_ID,
        "name": "Friend-Lite Integration",
        "policies": [
            {
                "resource": "**",
                "action": "*",
                "effect": "allow"
            }
        ],
        "openPrefix": open_prefix,
        "createdAt": datetime.now(),
        "isActive": True,
    }

    # Insert into database
    result = api_keys.insert_one(api_key_doc)
    client_id = str(result.inserted_id)

    # Detect Mycelia ports from environment
    mycelia_frontend_port = os.getenv("MYCELIA_FRONTEND_PORT", "3002")
    mycelia_backend_port = os.getenv("MYCELIA_BACKEND_PORT", os.getenv("MYCELIA_PORT", "5100"))

    print(f"🎉 API Key Created Successfully!")
    print(f"   Client ID: {client_id}")
    print(f"   API Key: {api_key}")
    print(f"\n" + "=" * 70)
    print("📋 MYCELIA CONFIGURATION")
    print("=" * 70)
    print(f"\n1️⃣  Configure Mycelia Frontend Settings:")
    print(f"   • Go to: http://localhost:{mycelia_frontend_port}/settings")
    print(f"   • API Endpoint: http://localhost:{mycelia_backend_port}")
    print(f"   • Client ID: {client_id}")
    print(f"   • Client Secret: {api_key}")
    print(f"   • Click 'Save' and then 'Test Token'")
    print(f"\n✅ This API key uses the proper Mycelia format with salt!")
    print("=" * 70 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
