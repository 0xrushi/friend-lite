#!/bin/bash
# Friend-Lite Environment Starter
# Loads environment-specific config and starts services
#
# Usage:
#   ./start-env.sh dev                    # Start dev environment
#   ./start-env.sh feature-123            # Start feature branch
#   ./start-env.sh test                   # Start test environment
#   ./start-env.sh dev --profile mycelia  # With additional profiles

set -e

# Check if environment name provided
if [ -z "$1" ]; then
    echo "Usage: $0 <environment> [docker-compose-options]"
    echo ""
    echo "Available environments:"
    ls -1 environments/*.env 2>/dev/null | sed 's|environments/||;s|.env$|  |' | sed 's/^/  - /'
    echo ""
    echo "Examples:"
    echo "  $0 dev                    # Start dev environment"
    echo "  $0 feature-123            # Start feature branch"
    echo "  $0 test                   # Start test environment"
    echo "  $0 dev --profile mycelia  # Dev with mycelia"
    exit 1
fi

ENV_NAME="$1"
shift  # Remove environment name from args

ENV_FILE="environments/${ENV_NAME}.env"

# Check if environment file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Environment file not found: $ENV_FILE"
    echo ""
    echo "Available environments:"
    ls -1 environments/*.env 2>/dev/null | sed 's|environments/||;s|.env$|  |' | sed 's/^/  - /'
    exit 1
fi

# Load Docker Compose system defaults first
if [ -f "docker-defaults.env" ]; then
    source docker-defaults.env
fi

# Load user settings (overrides defaults)
if [ -f "config-docker.env" ]; then
    source config-docker.env
elif [ -f "config.env" ]; then
    # Fallback to config.env for backwards compatibility
    source config.env
fi

# Load secrets (gitignored)
if [ -f ".env.secrets" ]; then
    source .env.secrets
else
    echo "⚠️  Warning: .env.secrets not found"
    echo "    Copy .env.secrets.template to .env.secrets and fill in your credentials"
    echo ""
fi

# Load environment-specific config (overrides base)
source "$ENV_FILE"

# Calculate actual ports based on offset
BACKEND_PORT=$((8000 + PORT_OFFSET))
WEBUI_PORT=$((3010 + PORT_OFFSET))
MONGO_PORT=$((27017 + PORT_OFFSET))
REDIS_PORT=$((6379 + PORT_OFFSET))
QDRANT_GRPC_PORT=$((6033 + PORT_OFFSET))
QDRANT_HTTP_PORT=$((6034 + PORT_OFFSET))
MYCELIA_BACKEND_PORT=$((5100 + PORT_OFFSET))
MYCELIA_FRONTEND_PORT=$((3003 + PORT_OFFSET))
SPEAKER_PORT=$((8085 + PORT_OFFSET))
OPENMEMORY_PORT=$((8765 + PORT_OFFSET))
PARAKEET_PORT=$((8767 + PORT_OFFSET))

# Export all variables for docker compose
export ENV_NAME
export BACKEND_PORT
export WEBUI_PORT
export MONGO_PORT
export REDIS_PORT
export QDRANT_GRPC_PORT
export QDRANT_HTTP_PORT
export MYCELIA_BACKEND_PORT
export MYCELIA_FRONTEND_PORT
export SPEAKER_PORT
export OPENMEMORY_PORT
export PARAKEET_PORT
export MONGODB_DATABASE
export MYCELIA_DB
export QDRANT_DATA_PATH="${DATA_DIR}/qdrant_data"
export REDIS_DATA_PATH="${DATA_DIR}/redis_data"
export COMPOSE_PROJECT_NAME

# Display configuration
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Starting Friend-Lite: ${ENV_NAME}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📦 Project:          ${COMPOSE_PROJECT_NAME}"
echo "🗄️  MongoDB Database: ${MONGODB_DATABASE}"
echo "🗄️  Mycelia Database: ${MYCELIA_DB}"
echo "💾 Data Directory:   ${DATA_DIR}"
echo ""
echo "🌐 Service URLs:"
echo "   Backend:          http://localhost:${BACKEND_PORT}"
echo "   Web UI:           http://localhost:${WEBUI_PORT}"
echo "   MongoDB:          mongodb://localhost:${MONGO_PORT}"
echo "   Redis:            redis://localhost:${REDIS_PORT}"
echo "   Qdrant HTTP:      http://localhost:${QDRANT_HTTP_PORT}"
echo "   Qdrant gRPC:      http://localhost:${QDRANT_GRPC_PORT}"
echo ""

# Show optional service URLs if enabled via --profile or SERVICES variable
if [[ "$SERVICES" == *"mycelia"* ]] || [[ "$*" == *"mycelia"* ]]; then
    echo "📊 Mycelia Services:"
    echo "   Backend:          http://localhost:${MYCELIA_BACKEND_PORT}"
    echo "   Frontend:         http://localhost:${MYCELIA_FRONTEND_PORT}"
    echo ""
fi

if [[ "$SERVICES" == *"speaker"* ]] || [[ "$*" == *"speaker"* ]]; then
    echo "🎤 Speaker Recognition:"
    echo "   Service:          http://localhost:${SPEAKER_PORT}"
    echo ""
fi

if [[ "$SERVICES" == *"openmemory"* ]] || [[ "$*" == *"openmemory"* ]]; then
    echo "🧠 OpenMemory MCP:"
    echo "   Service:          http://localhost:${OPENMEMORY_PORT}"
    echo ""
fi

if [[ "$SERVICES" == *"asr"* ]] || [[ "$*" == *"parakeet"* ]]; then
    echo "🗣️  Parakeet ASR:"
    echo "   Service:          http://localhost:${PARAKEET_PORT}"
    echo ""
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Create data directory
mkdir -p "${DATA_DIR}"

# Update backends/advanced/.env with environment-specific values
# This ensures the backend uses the correct database names
if [ -f "backends/advanced/.env" ]; then
    # Create backup
    cp backends/advanced/.env backends/advanced/.env.backup.$(date +%Y%m%d_%H%M%S)
fi

# Generate environment-specific .env file for backend
# This exports all currently loaded environment variables to the backend
{
    echo "# Auto-generated for environment: ${ENV_NAME}"
    echo "# Generated: $(date)"
    echo "#"
    echo "# This file is regenerated every time you run start-env.sh"
    echo "# It combines: docker-defaults.env + config-docker.env + .env.secrets + environments/${ENV_NAME}.env"
    echo ""
    echo "# Database configuration (environment-specific)"
    echo "MONGODB_URI=mongodb://mongo:27017/${MONGODB_DATABASE}"
    echo "MYCELIA_DB=${MYCELIA_DB}"
    echo ""
    echo "# All loaded environment variables"

    # Export configuration variables from our config files
    # This uses an allowlist approach to only include relevant variables
    # and exclude host system paths (HOME, CONDA_*, BUNDLED_*, etc.)

    # Collect all variable names from config files
    config_vars=()

    # From docker-defaults.env
    if [ -f "docker-defaults.env" ]; then
        while IFS='=' read -r key value; do
            # Skip comments and empty lines
            [[ $key =~ ^#.*$ ]] && continue
            [[ -z $key ]] && continue
            config_vars+=("$key")
        done < <(grep -E '^[A-Z_][A-Z0-9_]*=' docker-defaults.env || true)
    fi

    # From config-docker.env
    if [ -f "config-docker.env" ]; then
        while IFS='=' read -r key value; do
            [[ $key =~ ^#.*$ ]] && continue
            [[ -z $key ]] && continue
            config_vars+=("$key")
        done < <(grep -E '^[A-Z_][A-Z0-9_]*=' config-docker.env || true)
    elif [ -f "config.env" ]; then
        while IFS='=' read -r key value; do
            [[ $key =~ ^#.*$ ]] && continue
            [[ -z $key ]] && continue
            config_vars+=("$key")
        done < <(grep -E '^[A-Z_][A-Z0-9_]*=' config.env || true)
    fi

    # From .env.secrets
    if [ -f ".env.secrets" ]; then
        while IFS='=' read -r key value; do
            [[ $key =~ ^#.*$ ]] && continue
            [[ -z $key ]] && continue
            config_vars+=("$key")
        done < <(grep -E '^[A-Z_][A-Z0-9_]*=' .env.secrets || true)
    fi

    # From environment-specific file
    if [ -f "$ENV_FILE" ]; then
        while IFS='=' read -r key value; do
            [[ $key =~ ^#.*$ ]] && continue
            [[ -z $key ]] && continue
            config_vars+=("$key")
        done < <(grep -E '^[A-Z_][A-Z0-9_]*=' "$ENV_FILE" || true)
    fi

    # Add port variables calculated by this script
    config_vars+=(
        "BACKEND_PORT"
        "WEBUI_PORT"
        "MONGO_PORT"
        "REDIS_PORT"
        "QDRANT_GRPC_PORT"
        "QDRANT_HTTP_PORT"
        "MYCELIA_BACKEND_PORT"
        "MYCELIA_FRONTEND_PORT"
        "SPEAKER_PORT"
        "OPENMEMORY_PORT"
        "PARAKEET_PORT"
        "QDRANT_DATA_PATH"
        "REDIS_DATA_PATH"
    )

    # Remove duplicates and sort
    config_vars=($(printf '%s\n' "${config_vars[@]}" | sort -u))

    # Export only the allowlisted variables
    for key in "${config_vars[@]}"; do
        if [ -n "${!key}" ]; then
            echo "${key}=${!key}"
        fi
    done
} > backends/advanced/.env.${ENV_NAME}

# Symlink to active .env
ln -sf .env.${ENV_NAME} backends/advanced/.env

echo "✅ Environment configured"
echo "📝 Backend .env: backends/advanced/.env.${ENV_NAME}"
echo ""

# Start services
echo "🚀 Starting Docker Compose..."
echo ""

docker compose "$@" up
