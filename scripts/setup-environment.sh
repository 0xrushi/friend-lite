#!/bin/bash
set -e

# Friend-Lite Environment Setup Script
# This script creates custom environment configurations

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 Step 1: Environment Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Environments allow you to:"
echo "  • Run multiple isolated instances (dev, staging, prod)"
echo "  • Use different databases and ports for each"
echo "  • Test changes without affecting production"
echo ""

# Check existing environments
if [ -d "environments" ] && [ -n "$(ls -A environments/*.env 2>/dev/null)" ]; then
    echo "📋 Existing environments:"
    ls -1 environments/*.env 2>/dev/null | sed 's|environments/||;s|.env$||' | sed 's/^/  - /'
    echo ""
fi

# Get user name for personalized configuration
echo "👤 User Information"
echo ""
echo "This name will be used for the memory system and personalization"
echo ""
read -p "Your name [user]: " user_name
user_name=${user_name:-user}
echo ""

# Get environment name
read -p "Environment name [dev]: " env_name
env_name=${env_name:-dev}
mkdir -p environments
env_file="environments/$env_name.env"
echo ""

if [ -f "$env_file" ]; then
    echo "⚠️  Environment '$env_name' already exists"
    read -p "Do you want to overwrite it? (y/N): " overwrite
    if [ "$overwrite" != "y" ] && [ "$overwrite" != "Y" ]; then
        echo ""
        echo "ℹ️  Keeping existing environment"
        exit 0
    fi
    echo ""
    cp "$env_file" "$env_file.backup.$(date +%Y%m%d_%H%M%S)"
    echo "📝 Backed up existing environment"
    echo ""
fi

# Get port offset
echo "🔢 Port Configuration"
echo ""
echo "Each environment needs a unique port offset to avoid conflicts."
echo ""
echo "Port offset applies ONLY to API and WebUI containers:"
echo "  dev:     0   (Backend: 8000, WebUI: 3010)"
echo "  staging: 100 (Backend: 8100, WebUI: 3110)"
echo "  prod:    200 (Backend: 8200, WebUI: 3210)"
echo ""
echo "Note: Infrastructure services (MongoDB:27017, Redis:6379, Qdrant:6033/6034)"
echo "      use fixed ports and are shared across all environments."
echo ""
read -p "Port offset [0]: " port_offset
port_offset=${port_offset:-0}
echo ""

# Memory Backend Selection
echo "🧠 Memory Backend"
echo ""
echo "Choose your memory backend:"
echo "  1) OpenMemory (recommended - MCP server with advanced features)"
echo "  2) Friend-Lite Standard (built-in memory system)"
echo "  3) Mycelia (experimental - graph-based memory)"
echo ""
read -p "Memory backend (1-3) [1]: " memory_choice
memory_choice=${memory_choice:-1}
echo ""

case $memory_choice in
    1)
        memory_provider="openmemory_mcp"
        echo "✅ Using OpenMemory MCP backend"
        echo ""

        # Ask about Neo4j graph memory
        echo "🔗 Neo4j Graph Memory (Optional)"
        echo ""
        echo "Neo4j enables advanced graph-based memory relationships."
        echo "This allows OpenMemory to store and query complex connections"
        echo "between memories, entities, and concepts."
        echo ""
        read -p "Enable Neo4j graph memory? (y/N): " enable_neo4j
        ;;
    2)
        memory_provider="friend_lite"
        echo "✅ Using Friend-Lite standard backend"
        ;;
    3)
        memory_provider="mycelia"
        echo "✅ Using Mycelia backend"
        ;;
    *)
        memory_provider="openmemory_mcp"
        echo "⚠️  Invalid choice, defaulting to OpenMemory"

        # Ask about Neo4j for default case too
        echo ""
        echo "🔗 Neo4j Graph Memory (Optional)"
        echo ""
        echo "Neo4j enables advanced graph-based memory relationships."
        echo "This allows OpenMemory to store and query complex connections"
        echo "between memories, entities, and concepts."
        echo ""
        read -p "Enable Neo4j graph memory? (y/N): " enable_neo4j
        ;;
esac
echo ""

# Optional services
echo "🔌 Optional Services"
echo ""
read -p "Enable Speaker Recognition? (y/N): " enable_speaker
read -p "Enable Parakeet ASR? (y/N): " enable_parakeet
echo ""

# Auto-enable services based on memory choice
if [ "$memory_provider" = "mycelia" ]; then
    enable_mycelia="y"
    echo "✅ Mycelia service will be enabled (required for Mycelia backend)"
    echo ""
elif [ "$memory_provider" = "openmemory_mcp" ]; then
    enable_openmemory="y"
    echo "✅ OpenMemory MCP service will be enabled"

    # Handle Neo4j enablement
    if [ "$enable_neo4j" = "y" ] || [ "$enable_neo4j" = "Y" ]; then
        echo "✅ Neo4j graph memory will be enabled"
    fi
    echo ""
fi

# Find an unused Redis database number (0-15)
find_unused_redis_db() {
    local used_dbs=$(grep -h "^REDIS_DATABASE=" environments/*.env 2>/dev/null | cut -d= -f2 | sort -n)
    for db in {0..15}; do
        if ! echo "$used_dbs" | grep -q "^${db}$"; then
            echo "$db"
            return
        fi
    done
    # Fallback to 0 if all are used (shouldn't happen with 16 databases)
    echo "0"
}

redis_db=$(find_unused_redis_db)

# Get database names
echo "💾 Database Configuration"
echo ""
read -p "MongoDB database name [chronicle-$env_name]: " mongodb_db
mongodb_db=${mongodb_db:-chronicle-$env_name}
echo "   Redis database: $redis_db (auto-assigned)"

# Only ask for Mycelia database if Mycelia is enabled
if [ "$enable_mycelia" = "y" ] || [ "$enable_mycelia" = "Y" ]; then
    read -p "Mycelia database name [mycelia-$env_name]: " mycelia_db
    mycelia_db=${mycelia_db:-mycelia-$env_name}
else
    mycelia_db="mycelia-$env_name"
fi

# Only ask for OpenMemory database if OpenMemory is enabled
if [ "$enable_openmemory" = "y" ] || [ "$enable_openmemory" = "Y" ]; then
    read -p "OpenMemory database name [openmemory-$env_name]: " openmemory_db
    openmemory_db=${openmemory_db:-openmemory-$env_name}
else
    openmemory_db="openmemory-$env_name"
fi
echo ""

# If speaker recognition or ASR is enabled, ask about GPU support
pytorch_cuda_version="cpu"
if [ "$enable_speaker" = "y" ] || [ "$enable_speaker" = "Y" ] || [ "$enable_parakeet" = "y" ] || [ "$enable_parakeet" = "Y" ]; then
    echo "🎤 GPU Configuration (for Speaker Recognition / ASR)"
    echo ""
    echo "   GPU Support:"
    echo "   • cpu   - CPU only (slower, works everywhere)"
    echo "   • cu121 - CUDA 12.1 (NVIDIA GPU)"
    echo "   • cu126 - CUDA 12.6 (NVIDIA GPU)"
    echo "   • cu128 - CUDA 12.8 (Latest NVIDIA GPU)"
    read -p "   PyTorch version [cpu]: " pytorch_input
    pytorch_cuda_version=${pytorch_input:-cpu}
    echo ""
fi

services=""
if [ "$enable_mycelia" = "y" ] || [ "$enable_mycelia" = "Y" ]; then
    services="${services:+$services }mycelia"
fi
if [ "$enable_speaker" = "y" ] || [ "$enable_speaker" = "Y" ]; then
    services="${services:+$services }speaker"
fi
if [ "$enable_openmemory" = "y" ] || [ "$enable_openmemory" = "Y" ]; then
    services="${services:+$services }openmemory"
fi
if [ "$enable_parakeet" = "y" ] || [ "$enable_parakeet" = "Y" ]; then
    services="${services:+$services }asr"
fi
# Note: Neo4j is infrastructure, not a profile service
echo ""

# Write environment file
echo "📝 Creating environment file: $env_file"
echo ""

{
    printf "# ========================================\n"
    printf "# Friend-Lite Environment: %s\n" "$env_name"
    printf "# ========================================\n"
    printf "# Generated: %s\n" "$(date)"
    printf "\n"
    printf "# Environment identification\n"
    printf "ENV_NAME=%s\n" "$env_name"
    printf "COMPOSE_PROJECT_NAME=chronicle-%s\n" "$env_name"
    printf "\n"
    printf "# Port offset (each environment needs unique ports)\n"
    printf "PORT_OFFSET=%s\n" "$port_offset"
    printf "\n"
    printf "# Data directory (isolated per environment)\n"
    printf "DATA_DIR=./data/%s\n" "$env_name"
    printf "\n"
    printf "# Database names (isolated per environment)\n"
    printf "MONGODB_DATABASE=%s\n" "$mongodb_db"
    printf "REDIS_DATABASE=%s\n" "$redis_db"
    printf "MYCELIA_DB=%s\n" "$mycelia_db"
    printf "OPENMEMORY_DB=%s\n" "$openmemory_db"
    printf "\n"
    printf "# Memory Backend\n"
    printf "MEMORY_PROVIDER=%s\n" "$memory_provider"
    printf "\n"
    printf "# OpenMemory User Configuration\n"
    printf "OPENMEMORY_USER_ID=%s\n" "$user_name"
    printf "\n"
    printf "# Neo4j Graph Memory (for OpenMemory)\n"
    if [ "$enable_neo4j" = "y" ] || [ "$enable_neo4j" = "Y" ]; then
        printf "NEO4J_ENABLED=true\n"
    else
        printf "NEO4J_ENABLED=false\n"
    fi
    printf "\n"
    printf "# Optional services\n"
    printf "SERVICES=\"%s\"\n" "$services"
    printf "\n"
    printf "# Speaker Recognition PyTorch version\n"
    printf "PYTORCH_CUDA_VERSION=%s\n" "$pytorch_cuda_version"
    printf "\n"

    # Add Vite base path for Caddy path-based routing
    if [ -f "config-docker.env" ] && grep -q "USE_CADDY_PROXY=true" config-docker.env; then
        printf "# WebUI base path for Caddy reverse proxy\n"
        printf "VITE_BASE_PATH=/%s/\n" "$env_name"
        printf "\n"
    fi
} > "$env_file"

echo "✅ Environment created: $env_name"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Environment setup complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📄 Environment file: $env_file"
echo "👤 User: $user_name"
if [ -n "$services" ]; then
    echo "🔌 Configured services: $services"
fi
echo ""
echo "🚀 Start this environment with:"
echo "   ./start-env.sh $env_name"
echo ""
echo "💡 Your selected services will start automatically!"
echo ""
