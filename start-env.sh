#!/bin/bash
# Friend-Lite Environment Starter
# Loads environment-specific config and starts services
#
# Usage:
#   ./start-env.sh dev                    # Start dev environment
#   ./start-env.sh dev -f                 # Force recreate containers
#   ./start-env.sh feature-123            # Start feature branch
#   ./start-env.sh test                   # Start test environment
#   ./start-env.sh dev --profile mycelia  # With additional profiles

set -e

# Check if environment name provided
if [ -z "$1" ]; then
    echo "Usage: $0 <environment> [options] [docker-compose-options]"
    echo ""
    echo "Available environments:"
    ls -1 environments/*.env 2>/dev/null | sed 's|environments/||;s|.env$|  |' | sed 's/^/  - /'
    echo ""
    echo "Options:"
    echo "  -f, --force              Force recreate containers (useful after config changes)"
    echo ""
    echo "Examples:"
    echo "  $0 dev                   # Start dev environment"
    echo "  $0 dev -f                # Force recreate dev containers"
    echo "  $0 feature-123           # Start feature branch"
    echo "  $0 test                  # Start test environment"
    echo "  $0 dev --profile mycelia # Dev with mycelia"
    exit 1
fi

ENV_NAME="$1"
shift  # Remove environment name from args

# Parse flags
FORCE_RECREATE=false
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--force)
            FORCE_RECREATE=true
            shift
            ;;
        *)
            # Not our flag, pass through to docker compose
            break
            ;;
    esac
done

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
    # Export secrets for docker-compose to access
    export AUTH_SECRET_KEY
    export ADMIN_EMAIL
    export ADMIN_PASSWORD
    export OPENAI_API_KEY
    export DEEPGRAM_API_KEY
    export MISTRAL_API_KEY
    export GROQ_API_KEY
    export HF_TOKEN
    export LANGFUSE_PUBLIC_KEY
    export LANGFUSE_SECRET_KEY
    export NGROK_AUTHTOKEN
    export NEO4J_PASSWORD
else
    echo "⚠️  Warning: .env.secrets not found"
    echo "    Copy .env.secrets.template to .env.secrets and fill in your credentials"
    echo ""
fi

# Load environment-specific config (overrides base)
source "$ENV_FILE"

# Calculate actual ports based on offset
# Infrastructure ports (MongoDB, Redis, Qdrant) are NOT offset - they're shared across environments
# Only API and WebUI ports get the offset for multi-environment support
BACKEND_PORT=$((8000 + PORT_OFFSET))
WEBUI_PORT=$((3010 + PORT_OFFSET))
MYCELIA_BACKEND_PORT=$((5100 + PORT_OFFSET))
MYCELIA_FRONTEND_PORT=$((3003 + PORT_OFFSET))
SPEAKER_PORT=$((8085 + PORT_OFFSET))
OPENMEMORY_PORT=$((8765 + PORT_OFFSET))
OPENMEMORY_UI_PORT=$((3330 + PORT_OFFSET))
PARAKEET_PORT=$((8767 + PORT_OFFSET))

# Infrastructure ports - no offset (shared across environments)
MONGO_PORT=27017
REDIS_PORT=6379
QDRANT_GRPC_PORT=6033
QDRANT_HTTP_PORT=6034
NEO4J_HTTP_PORT=7474
NEO4J_BOLT_PORT=7687

# Calculate VITE_BACKEND_URL based on Caddy/Tailscale configuration
if [ "$USE_CADDY_PROXY" = "true" ]; then
    # Use relative URLs for same-origin requests (Caddy handles routing)
    VITE_BACKEND_URL=""
    echo "🔄 Using Caddy reverse proxy - frontend will use relative URLs"
elif [ -n "$TAILSCALE_HOSTNAME" ]; then
    # Direct Tailscale access with ports
    if [ "$HTTPS_ENABLED" = "true" ]; then
        VITE_BACKEND_URL="https://${TAILSCALE_HOSTNAME}:${BACKEND_PORT}"
    else
        VITE_BACKEND_URL="http://${TAILSCALE_HOSTNAME}:${BACKEND_PORT}"
    fi
else
    # Use localhost for local-only development
    VITE_BACKEND_URL="http://localhost:${BACKEND_PORT}"
fi

# Calculate CORS_ORIGINS based on Caddy/Tailscale configuration
if [ "$USE_CADDY_PROXY" = "true" ]; then
    # With Caddy, same-origin requests mean minimal CORS needed
    # Add Tailscale hostname and common subdomains
    CORS_ORIGINS="https://${TAILSCALE_HOSTNAME}"
    CORS_ORIGINS="${CORS_ORIGINS},https://dev.${TAILSCALE_HOSTNAME}"
    CORS_ORIGINS="${CORS_ORIGINS},https://test.${TAILSCALE_HOSTNAME}"
    CORS_ORIGINS="${CORS_ORIGINS},https://prod.${TAILSCALE_HOSTNAME}"
    # Add localhost for development
    CORS_ORIGINS="${CORS_ORIGINS},http://localhost:${WEBUI_PORT},http://localhost:5173,http://localhost:${BACKEND_PORT}"
    echo "🌐 CORS configured for Caddy subdomain routing"
else
    # Standard CORS for direct access
    CORS_ORIGINS="http://localhost:${WEBUI_PORT},http://localhost:5173,http://localhost:${BACKEND_PORT}"

    # Add Tailscale URLs to CORS if Tailscale hostname is configured
    if [ -n "$TAILSCALE_HOSTNAME" ]; then
        echo "🌐 Adding Tailscale URLs to CORS_ORIGINS..."
        # Add both HTTP and HTTPS URLs for the Tailscale hostname with ports
        CORS_ORIGINS="${CORS_ORIGINS},http://${TAILSCALE_HOSTNAME}:${BACKEND_PORT},https://${TAILSCALE_HOSTNAME}:${BACKEND_PORT}"
        CORS_ORIGINS="${CORS_ORIGINS},http://${TAILSCALE_HOSTNAME}:${WEBUI_PORT},https://${TAILSCALE_HOSTNAME}:${WEBUI_PORT}"
        # Also add URLs without ports (for tailscale serve)
        CORS_ORIGINS="${CORS_ORIGINS},http://${TAILSCALE_HOSTNAME},https://${TAILSCALE_HOSTNAME}"
    fi
fi

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
export OPENMEMORY_UI_PORT
export OPENMEMORY_USER_ID
export OPENMEMORY_DB
export PARAKEET_PORT
export MONGODB_DATABASE
export MYCELIA_DB
export NEO4J_HTTP_PORT
export NEO4J_BOLT_PORT
export QDRANT_DATA_PATH="${DATA_DIR}/qdrant_data"
export REDIS_DATA_PATH="${DATA_DIR}/redis_data"
export COMPOSE_PROJECT_NAME
export VITE_BACKEND_URL
export VITE_BASE_PATH
export CORS_ORIGINS

# Check if infrastructure is running (shared or per-environment)
echo "🔍 Checking infrastructure..."
INFRA_RUNNING=true

# Check for MongoDB by container name and status
if docker ps --filter "name=^chronicle-mongo$" --format '{{.Names}}' | grep -q chronicle-mongo; then
    echo "✅ MongoDB: chronicle-mongo"
else
    echo "⚠️  MongoDB not running"
    INFRA_RUNNING=false
fi

# Check for Redis by container name and status
if docker ps --filter "name=^chronicle-redis$" --format '{{.Names}}' | grep -q chronicle-redis; then
    echo "✅ Redis: chronicle-redis"
else
    echo "⚠️  Redis not running"
    INFRA_RUNNING=false
fi

# Check for Qdrant by container name and status
if docker ps --filter "name=^chronicle-qdrant$" --format '{{.Names}}' | grep -q chronicle-qdrant; then
    echo "✅ Qdrant: chronicle-qdrant"
else
    echo "⚠️  Qdrant not running"
    INFRA_RUNNING=false
fi

# Check for Neo4j if enabled in ANY environment
NEO4J_NEEDED=false
NEO4J_RUNNING=false
if grep -q "^NEO4J_ENABLED=true" environments/*.env 2>/dev/null; then
    NEO4J_NEEDED=true
    if docker ps --filter "name=^chronicle-neo4j$" --format '{{.Names}}' | grep -q chronicle-neo4j; then
        echo "✅ Neo4j: chronicle-neo4j"
        NEO4J_RUNNING=true
    else
        echo "⚠️  Neo4j not running (required by at least one environment)"
        # Don't mark core infrastructure as not running - Neo4j can be started separately
    fi
fi

# Check for Caddy if configured
if [ "$USE_CADDY_PROXY" = "true" ]; then
    if docker ps --filter "name=^chronicle-caddy$" --format '{{.Names}}' | grep -q chronicle-caddy; then
        echo "✅ Caddy: chronicle-caddy"
    else
        echo "ℹ️  Caddy not running (will be started)"
        # Don't mark infrastructure as not running - Caddy is optional
    fi
fi

# Auto-start infrastructure if not running
if [ "$INFRA_RUNNING" = "false" ]; then
    echo ""
    echo "🚀 Starting shared infrastructure..."
    echo ""

    # Create network if it doesn't exist
    docker network inspect chronicle-network >/dev/null 2>&1 || docker network create chronicle-network

    # Clean up any orphaned network endpoints for this environment
    docker network inspect chronicle-network --format '{{range .Containers}}{{.Name}} {{end}}' 2>/dev/null | \
        grep "${COMPOSE_PROJECT_NAME}" | \
        xargs -n1 docker network disconnect -f chronicle-network 2>/dev/null || true

    # Check if infrastructure containers exist but are stopped (exited or created status)
    STOPPED_CONTAINERS=$(docker ps -a --filter "status=exited" --filter "status=created" --format "{{.Names}}" 2>/dev/null | grep -E '^chronicle-(mongo|redis|qdrant|neo4j|caddy)$' || true)

    if [ -n "$STOPPED_CONTAINERS" ]; then
        echo "   Found stopped infrastructure containers: $STOPPED_CONTAINERS"
        echo "   Starting stopped containers..."
        echo "$STOPPED_CONTAINERS" | xargs docker start 2>/dev/null || true

        # If Neo4j is needed but not in stopped containers, start it with compose
        if [ "$NEO4J_NEEDED" = "true" ] && ! echo "$STOPPED_CONTAINERS" | grep -q "neo4j"; then
            echo "   Starting Neo4j (required by at least one environment)..."
            # Clean up any orphaned network endpoint first
            docker network disconnect -f chronicle-network chronicle-neo4j 2>/dev/null || true
            docker compose -p chronicle-infra -f compose/infrastructure-shared.yml --profile neo4j up -d --remove-orphans neo4j
        fi
    else
        # Start infrastructure with compose
        # Add Neo4j profile if enabled in ANY environment
        if [ "$NEO4J_NEEDED" = "true" ]; then
            echo "   Starting infrastructure with Neo4j support (required by at least one environment)..."
            docker compose -p chronicle-infra -f compose/infrastructure-shared.yml --profile neo4j up -d --remove-orphans
        else
            docker compose -p chronicle-infra -f compose/infrastructure-shared.yml up -d --remove-orphans
        fi
    fi

    # Wait for services to be ready
    echo ""
    echo "⏳ Waiting for infrastructure to be ready..."
    sleep 5

    echo "✅ Infrastructure started"
    echo ""
fi

# Start Neo4j separately if needed but not running
if [ "$NEO4J_NEEDED" = "true" ] && [ "$NEO4J_RUNNING" = "false" ]; then
    echo "🔗 Starting Neo4j (required by at least one environment)..."
    echo ""

    # Remove any existing Neo4j container in Created/Exited state
    docker rm -f chronicle-neo4j 2>/dev/null || true

    # Clean up any orphaned network endpoint
    docker network disconnect -f chronicle-network chronicle-neo4j 2>/dev/null || true

    # Start Neo4j with compose under infrastructure project
    # Use -p to explicitly set project to chronicle-infra
    docker compose -p chronicle-infra -f compose/infrastructure-shared.yml --profile neo4j up -d neo4j

    echo ""
    echo "✅ Neo4j started"
    echo ""
fi

# Display configuration
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Starting Friend-Lite: ${ENV_NAME}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📦 Project:          ${COMPOSE_PROJECT_NAME}"
echo "🗄️  MongoDB Database: ${MONGODB_DATABASE}"
echo "🗄️  Mycelia Database: ${MYCELIA_DB}"
if [ "$NEO4J_ENABLED" = "true" ]; then
    echo "🔗 Neo4j Database:   ${OPENMEMORY_DB} (graph memory enabled)"
fi
echo "💾 Data Directory:   ${DATA_DIR}"
echo ""
echo "🌐 Service URLs:"
echo "   Backend:          http://localhost:${BACKEND_PORT}"
echo "   Web UI:           http://localhost:${WEBUI_PORT}"
echo "   MongoDB:          mongodb://localhost:${MONGO_PORT} (shared)"
echo "   Redis:            redis://localhost:${REDIS_PORT} (shared)"
echo "   Qdrant HTTP:      http://localhost:${QDRANT_HTTP_PORT} (shared)"
echo "   Qdrant gRPC:      http://localhost:${QDRANT_GRPC_PORT} (shared)"
# Show Neo4j if it's running (means at least one environment uses it)
if docker ps --format '{{.Names}}' | grep -q '^chronicle-neo4j$'; then
    echo "   Neo4j Browser:    http://localhost:${NEO4J_HTTP_PORT} (shared)"
    echo "   Neo4j Bolt:       neo4j://localhost:${NEO4J_BOLT_PORT} (shared)"
fi
echo ""

# Show Tailscale configuration if enabled
if [ -n "$TAILSCALE_HOSTNAME" ]; then
    echo "🌐 Tailscale Configuration:"
    echo "   Hostname:         ${TAILSCALE_HOSTNAME}"
    echo "   Backend URL:      ${VITE_BACKEND_URL}"
    echo "   Remote Web UI:    http://${TAILSCALE_HOSTNAME}:${WEBUI_PORT}"
    echo "   CORS:             ✅ Tailscale URLs included"
    echo ""
    echo "💡 Frontend is configured to use Tailscale backend"
    echo "   Access from any device: http://${TAILSCALE_HOSTNAME}:${WEBUI_PORT}"
    echo ""
fi

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
    echo "🧠 OpenMemory:"
    echo "   API:              http://localhost:${OPENMEMORY_PORT}"
    echo "   UI:               http://localhost:${OPENMEMORY_UI_PORT}"
    echo "   User:             ${OPENMEMORY_USER_ID:-user}"
    echo ""
fi

if [[ "$SERVICES" == *"asr"* ]] || [[ "$*" == *"asr"* ]]; then
    echo "🗣️  Parakeet ASR:"
    echo "   Service:          http://localhost:${PARAKEET_PORT}"
    echo ""
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Note: DATA_DIR is set for reference but actual data is stored in backends/advanced/data/
# Data isolation is achieved via database names (MONGODB_DATABASE, MYCELIA_DB), not file directories

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
    echo "# NOTE: MONGODB_URI includes database name and should not be overridden"
    echo "MONGODB_URI=mongodb://mongo:27017/${MONGODB_DATABASE}"
    echo "MONGODB_DATABASE=${MONGODB_DATABASE}"
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
        "OPENMEMORY_DB"
        "PARAKEET_PORT"
        "NEO4J_HTTP_PORT"
        "NEO4J_BOLT_PORT"
        "QDRANT_DATA_PATH"
        "REDIS_DATA_PATH"
        "VITE_BACKEND_URL"
        "CORS_ORIGINS"
    )

    # Remove duplicates and sort
    config_vars=($(printf '%s\n' "${config_vars[@]}" | sort -u))

    # Export only the allowlisted variables
    # Skip MONGODB_URI and MONGODB_DATABASE as they're set explicitly above
    for key in "${config_vars[@]}"; do
        if [ "$key" = "MONGODB_URI" ] || [ "$key" = "MONGODB_DATABASE" ]; then
            continue
        fi
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

# Build profile flags from SERVICES variable
PROFILE_FLAGS=()
if [ -n "$SERVICES" ]; then
    for service in $SERVICES; do
        PROFILE_FLAGS+=(--profile "$service")
    done
fi

# Generate Caddyfile if Caddy proxy is enabled
# Note: Caddy runs as a shared service, not per-environment
if [ "$USE_CADDY_PROXY" = "true" ]; then
    echo "🔧 Generating Caddyfile for path-based routing..."
    ./scripts/generate-caddyfile.sh
    echo ""

    # Check if Tailscale certificates exist, provision if needed
    if [ -n "$TAILSCALE_HOSTNAME" ]; then
        # Create certs directory if it doesn't exist
        mkdir -p certs

        CERT_FILE="certs/${TAILSCALE_HOSTNAME}.crt"
        KEY_FILE="certs/${TAILSCALE_HOSTNAME}.key"

        if [ ! -f "$CERT_FILE" ]; then
            echo "🔐 Tailscale certificates not found - provisioning now..."
            echo ""
            echo "   Running: tailscale cert ${TAILSCALE_HOSTNAME}"
            echo ""

            # Run tailscale cert and move files to certs directory
            if tailscale cert "${TAILSCALE_HOSTNAME}" 2>&1; then
                # Move certificates to certs directory
                mv "${TAILSCALE_HOSTNAME}.crt" "certs/"
                mv "${TAILSCALE_HOSTNAME}.key" "certs/"

                echo ""
                echo "✅ Certificates provisioned successfully!"
                echo "   Location: certs/${TAILSCALE_HOSTNAME}.{crt,key}"
                echo ""
            else
                echo ""
                echo "❌ Certificate provisioning failed!"
                echo ""
                echo "   This may happen if:"
                echo "   • Tailscale is not running (run: sudo tailscale up)"
                echo "   • You don't have permission to provision certs"
                echo ""
                echo "   You can provision certificates manually with:"
                echo "      tailscale cert ${TAILSCALE_HOSTNAME}"
                echo "      mv ${TAILSCALE_HOSTNAME}.* certs/"
                echo ""
                exit 1
            fi
        else
            echo "✅ Tailscale certificates found at: $CERT_FILE"

            # Check certificate expiry
            if command -v openssl &> /dev/null; then
                EXPIRY_DATE=$(openssl x509 -enddate -noout -in "$CERT_FILE" 2>/dev/null | cut -d= -f2)
                if [ -n "$EXPIRY_DATE" ]; then
                    EXPIRY_EPOCH=$(date -j -f "%b %d %T %Y %Z" "$EXPIRY_DATE" "+%s" 2>/dev/null || date -d "$EXPIRY_DATE" "+%s" 2>/dev/null)
                    CURRENT_EPOCH=$(date "+%s")
                    DAYS_UNTIL_EXPIRY=$(( ($EXPIRY_EPOCH - $CURRENT_EPOCH) / 86400 ))

                    if [ $DAYS_UNTIL_EXPIRY -lt 0 ]; then
                        echo "   ⚠️  Certificate EXPIRED ${DAYS_UNTIL_EXPIRY#-} days ago!"
                        echo "   Run: tailscale cert ${TAILSCALE_HOSTNAME}"
                        echo ""
                    elif [ $DAYS_UNTIL_EXPIRY -lt 30 ]; then
                        echo "   ⚠️  Certificate expires in ${DAYS_UNTIL_EXPIRY} days (${EXPIRY_DATE})"
                        echo "   Consider renewing: tailscale cert ${TAILSCALE_HOSTNAME}"
                        echo ""
                    else
                        echo "   Valid until: ${EXPIRY_DATE} (${DAYS_UNTIL_EXPIRY} days)"
                        echo ""
                    fi
                fi
            fi
        fi
    fi

    # Check if Caddy is running, start if needed
    if docker ps --format '{{.Names}}' | grep -q '^chronicle-caddy$'; then
        # Check if it's part of the infrastructure project
        CADDY_PROJECT=$(docker inspect chronicle-caddy --format '{{index .Config.Labels "com.docker.compose.project"}}' 2>/dev/null)
        if [ "$CADDY_PROJECT" = "chronicle-infra" ]; then
            echo "✅ Caddy is already running (chronicle-infra)"
            echo "   Access all environments at: https://${TAILSCALE_HOSTNAME}/"
            echo ""
        else
            echo "⚠️  Caddy is running but not in infrastructure project (project: $CADDY_PROJECT)"
            echo ""
            echo "🔄 Recreating Caddy in infrastructure project..."
            echo ""

            # Stop and remove the old container
            docker stop chronicle-caddy >/dev/null 2>&1
            docker rm chronicle-caddy >/dev/null 2>&1

            # Start fresh from infrastructure-shared.yml
            docker compose -f compose/infrastructure-shared.yml up -d caddy

            echo ""
            echo "✅ Caddy recreated in chronicle-infra project"
            echo "   Access all environments at: https://${TAILSCALE_HOSTNAME}/"
            echo ""
        fi
    else
        echo "⚠️  Caddy is not running"
        echo ""
        echo "🚀 Starting Caddy (shared infrastructure)..."
        echo ""

        # Remove any stopped caddy containers from wrong projects
        if docker ps -a --filter "name=chronicle-caddy" --format "{{.Names}}" 2>/dev/null | grep -q chronicle-caddy; then
            echo "   Removing old Caddy container..."
            docker rm -f chronicle-caddy >/dev/null 2>&1
        fi

        # Start Caddy from infrastructure-shared.yml
        echo "   Starting: docker compose -f compose/infrastructure-shared.yml up -d caddy"
        docker compose -f compose/infrastructure-shared.yml up -d caddy

        echo ""
        echo "✅ Caddy started in chronicle-infra project"
        echo "   Access all environments at: https://${TAILSCALE_HOSTNAME}/"
        echo ""
    fi
fi

# Check if frontend needs rebuild for Tailscale or Caddy path-based routing
if [ -n "$TAILSCALE_HOSTNAME" ] && [ "$USE_CADDY_PROXY" != "true" ]; then
    echo "⚠️  Tailscale configured - forcing frontend rebuild with backend URL: ${VITE_BACKEND_URL}"
    echo "   (This ensures frontend can reach backend from remote devices)"
    echo ""
    # Force rebuild webui to pick up new VITE_BACKEND_URL
    docker compose "${PROFILE_FLAGS[@]}" build --no-cache webui
elif [ "$USE_CADDY_PROXY" = "true" ]; then
    if [ -n "$VITE_BASE_PATH" ] && [ "$VITE_BASE_PATH" != "/" ]; then
        echo "🔄 Caddy path-based routing enabled - rebuilding WebUI with base path: ${VITE_BASE_PATH}"
        echo "   (This ensures routing works correctly at ${VITE_BASE_PATH})"
        echo ""
        docker compose "${PROFILE_FLAGS[@]}" build webui
    else
        echo "🔄 Caddy proxy enabled - frontend will use relative URLs (no rebuild needed)"
        echo ""
    fi
fi

# Check if OpenMemory UI needs rebuild (bakes OPENMEMORY_USER_ID at build time)
if [[ "$SERVICES" == *"openmemory"* ]] || [[ "$*" == *"openmemory"* ]]; then
    echo "🧠 OpenMemory enabled - rebuilding UI with user: ${OPENMEMORY_USER_ID:-user}"
    echo "   (Build args need to be baked into Next.js)"
    echo ""
    docker compose "${PROFILE_FLAGS[@]}" build openmemory-ui
fi

# Clean up network endpoints only if force recreating
if [ "$FORCE_RECREATE" = "true" ]; then
    echo "🧹 Cleaning up network endpoints (force mode)..."
    docker network inspect chronicle-network --format '{{range .Containers}}{{.Name}}{{"\n"}}{{end}}' 2>/dev/null | \
        grep "^${COMPOSE_PROJECT_NAME}-" | \
        while read container; do
            echo "   Disconnecting: $container"
            docker network disconnect -f chronicle-network "$container" 2>/dev/null || true
        done
fi

# Build docker compose command
COMPOSE_ARGS=("${PROFILE_FLAGS[@]}" "$@" "up" "-d")

# Add --force-recreate if requested
if [ "$FORCE_RECREATE" = "true" ]; then
    echo "🔄 Force recreating containers..."
    COMPOSE_ARGS+=("--force-recreate")
fi

# Start services
docker compose "${COMPOSE_ARGS[@]}"

# Wait for services to be healthy
echo ""
echo "⏳ Waiting for services to become healthy..."
sleep 5

# Clear screen and display service URLs
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Services Started Successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🌐 Access Your Services:"
echo ""
echo "   📱 Web Dashboard:     http://localhost:${WEBUI_PORT}"
echo "   🔌 Backend API:       http://localhost:${BACKEND_PORT}"
echo "   📊 API Health:        http://localhost:${BACKEND_PORT}/health"
echo "   📚 API Docs:          http://localhost:${BACKEND_PORT}/docs"
echo ""

# Show Caddy/Tailscale URLs if configured
if [ "$USE_CADDY_PROXY" = "true" ] && [ -n "$TAILSCALE_HOSTNAME" ]; then
    echo "🌐 Caddy Reverse Proxy Access (Path-Based Routing):"
    echo ""
    echo "   📱 ${ENV_NAME} Environment:  https://${TAILSCALE_HOSTNAME}/${ENV_NAME}/"
    echo "   📊 Environment List:       https://${TAILSCALE_HOSTNAME}/"
    echo ""
    echo "   ℹ️  Other environments:"
    echo "      https://${TAILSCALE_HOSTNAME}/dev/"
    echo "      https://${TAILSCALE_HOSTNAME}/test/"
    echo "      https://${TAILSCALE_HOSTNAME}/prod/"
    echo ""
    echo "   🔗 API Endpoints:"
    echo "      Backend API:  https://${TAILSCALE_HOSTNAME}/${ENV_NAME}/api/"
    echo "      WebSocket:    wss://${TAILSCALE_HOSTNAME}/${ENV_NAME}/ws_pcm"
    echo "      API Docs:     https://${TAILSCALE_HOSTNAME}/${ENV_NAME}/docs"
    echo ""
elif command -v tailscale >/dev/null 2>&1 && tailscale status >/dev/null 2>&1; then
    TAILSCALE_HOSTNAME=$(tailscale status --json 2>/dev/null | grep -A 20 '"Self"' | grep '"DNSName"' | cut -d'"' -f4 | sed 's/\.$//')
    if [ -n "$TAILSCALE_HOSTNAME" ]; then
        echo "🌐 Tailscale Access (from any device in your tailnet):"
        echo ""
        echo "   📱 Web Dashboard:     http://${TAILSCALE_HOSTNAME}:${WEBUI_PORT}"
        echo "   🔌 Backend API:       http://${TAILSCALE_HOSTNAME}:${BACKEND_PORT}"
        echo "   📚 API Docs:          http://${TAILSCALE_HOSTNAME}:${BACKEND_PORT}/docs"
        echo ""
    fi
fi
echo "🗄️  Database Connections:"
echo ""
echo "   MongoDB:              mongodb://localhost:${MONGO_PORT}"
echo "   Redis:                redis://localhost:${REDIS_PORT}"
echo "   Qdrant HTTP:          http://localhost:${QDRANT_HTTP_PORT}"
echo "   Qdrant gRPC:          localhost:${QDRANT_GRPC_PORT}"
# Show Neo4j if it's running (means at least one environment uses it)
if docker ps --format '{{.Names}}' | grep -q '^chronicle-neo4j$'; then
    echo "   Neo4j Browser:        http://localhost:${NEO4J_HTTP_PORT}"
    echo "   Neo4j Bolt:           neo4j://localhost:${NEO4J_BOLT_PORT}"
fi
echo ""

# Show optional service URLs if they're running
if [[ "$SERVICES" == *"mycelia"* ]] || [[ "$*" == *"mycelia"* ]]; then
    echo "📊 Mycelia Memory Services:"
    echo ""
    echo "   Backend API:          http://localhost:${MYCELIA_BACKEND_PORT}"
    echo "   Web Interface:        http://localhost:${MYCELIA_FRONTEND_PORT}"
    echo ""
fi

if [[ "$SERVICES" == *"speaker"* ]] || [[ "$*" == *"speaker"* ]]; then
    echo "🎤 Speaker Recognition:"
    echo ""
    echo "   Service API:          http://localhost:${SPEAKER_PORT}"
    echo ""
fi

if [[ "$SERVICES" == *"openmemory"* ]] || [[ "$*" == *"openmemory"* ]]; then
    echo "🧠 OpenMemory MCP:"
    echo ""
    echo "   Service API:          http://localhost:${OPENMEMORY_PORT}"
    echo ""
fi

if [[ "$SERVICES" == *"asr"* ]] || [[ "$*" == *"asr"* ]]; then
    echo "🗣️  Parakeet ASR:"
    echo ""
    echo "   Service API:          http://localhost:${PARAKEET_PORT}"
    echo ""
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 Useful Commands:"
echo ""
echo "   View logs:            docker compose -p ${COMPOSE_PROJECT_NAME} logs -f"
echo "   Stop services:        docker compose -p ${COMPOSE_PROJECT_NAME} down"
echo "   Restart:              docker compose -p ${COMPOSE_PROJECT_NAME} restart"
echo "   Status:               docker compose -p ${COMPOSE_PROJECT_NAME} ps"
echo ""
echo "💾 Environment:         ${ENV_NAME}"
echo "📦 Project Name:        ${COMPOSE_PROJECT_NAME}"
echo "📂 Data Directory:      ${DATA_DIR}"
echo "🗄️  Database:            ${MONGODB_DATABASE}"
if [ "$NEO4J_ENABLED" = "true" ]; then
    echo "🔗 Neo4j Database:      ${OPENMEMORY_DB}"
fi
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Determine and display main URL
MAIN_URL=""
if [ "$USE_CADDY_PROXY" = "true" ] && [ -n "$TAILSCALE_HOSTNAME" ]; then
    # Caddy with path-based routing
    MAIN_URL="https://${TAILSCALE_HOSTNAME}/${ENV_NAME}/"
elif command -v tailscale >/dev/null 2>&1 && tailscale status >/dev/null 2>&1; then
    # Check if tailscale serve is configured for root path
    TAILSCALE_HOSTNAME_DETECT=$(tailscale status --json 2>/dev/null | grep -A 20 '"Self"' | grep '"DNSName"' | cut -d'"' -f4 | sed 's/\.$//')
    if [ -n "$TAILSCALE_HOSTNAME_DETECT" ] && tailscale serve status 2>/dev/null | grep -q "^|-- /"; then
        # Tailscale serve is configured
        MAIN_URL="https://${TAILSCALE_HOSTNAME_DETECT}/"
    else
        # Tailscale available but serve not configured, use port-based
        MAIN_URL="http://localhost:${WEBUI_PORT}"
    fi
else
    # Local access only
    MAIN_URL="http://localhost:${WEBUI_PORT}"
fi

echo "🌐 Main URL:  ${MAIN_URL}"
echo ""
