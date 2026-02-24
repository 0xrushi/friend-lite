#!/bin/bash

# Enable strict error handling
set -euo pipefail

# Parse command line arguments
OPENAI_API_KEY=""
EMBEDDINGS_PROVIDER=""
LOCAL_EMBEDDINGS_BASE_URL=""
LOCAL_EMBEDDINGS_MODEL=""
LOCAL_EMBEDDINGS_API_KEY=""
LOCAL_EMBEDDINGS_DIMENSIONS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --openai-api-key)
            OPENAI_API_KEY="$2"
            shift 2
            ;;
        --embeddings-provider)
            EMBEDDINGS_PROVIDER="$2"
            shift 2
            ;;
        --embeddings-base-url)
            LOCAL_EMBEDDINGS_BASE_URL="$2"
            shift 2
            ;;
        --embeddings-model)
            LOCAL_EMBEDDINGS_MODEL="$2"
            shift 2
            ;;
        --embeddings-api-key)
            LOCAL_EMBEDDINGS_API_KEY="$2"
            shift 2
            ;;
        --embeddings-dimensions)
            LOCAL_EMBEDDINGS_DIMENSIONS="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1"
            exit 1
            ;;
    esac
done

echo "🧠 OpenMemory MCP Setup"
echo "======================"

# Check if already configured
if [ -f ".env" ]; then
    echo "⚠️  .env already exists. Backing up..."
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
fi

# Start from template - check existence first
if [ ! -r ".env.template" ]; then
    echo "Error: .env.template not found or not readable" >&2
    exit 1
fi

# Copy template and set secure permissions
if ! cp .env.template .env; then
    echo "Error: Failed to copy .env.template to .env" >&2
    exit 1
fi

# Set restrictive permissions (owner read/write only)
chmod 600 .env

# Utility: replace env key or append if missing
upsert_env_key() {
    local key="$1"
    local value="$2"
    local temp_file

    temp_file=$(mktemp)
    awk -v key="$key" -v value="$value" '
        BEGIN { found=0 }
        $0 ~ ("^" key "=") { print key "=" value; found=1; next }
        { print }
        END { if (!found) print key "=" value }
    ' .env > "$temp_file"
    mv "$temp_file" .env
}

if [ -z "$EMBEDDINGS_PROVIDER" ]; then
    echo ""
    echo "🧩 Embedding provider"
    echo "1) OpenAI embeddings"
    echo "2) Local OpenAI-compatible embeddings"
    while true; do
        read -r -p "Choose provider [1/2]: " provider_choice
        case "$provider_choice" in
            1)
                EMBEDDINGS_PROVIDER="openai"
                break
                ;;
            2)
                EMBEDDINGS_PROVIDER="local"
                break
                ;;
            *)
                echo "Error: Please enter 1 or 2."
                ;;
        esac
    done
fi

if [ "$EMBEDDINGS_PROVIDER" != "openai" ] && [ "$EMBEDDINGS_PROVIDER" != "local" ]; then
    echo "Error: --embeddings-provider must be 'openai' or 'local'" >&2
    exit 1
fi

if [ "$EMBEDDINGS_PROVIDER" = "openai" ]; then
    # Get OpenAI API Key (prompt only if not provided via command line)
    if [ -z "$OPENAI_API_KEY" ]; then
        echo ""
        echo "🔑 OpenAI API Key (required for memory extraction + embeddings)"
        echo "Get yours from: https://platform.openai.com/api-keys"
        while true; do
            read -s -r -p "OpenAI API Key: " OPENAI_API_KEY
            echo  # Print newline after silent input
            if [ -n "$OPENAI_API_KEY" ]; then
                break
            fi
            echo "Error: OpenAI API Key cannot be empty. Please try again."
        done
    else
        echo "✅ OpenAI API key configured from command line"
    fi

    upsert_env_key "OPENMEMORY_EMBEDDINGS_PROVIDER" "openai"
    upsert_env_key "OPENAI_API_KEY" "$OPENAI_API_KEY"

    # Clear local embedding overrides for pure OpenAI mode
    upsert_env_key "OPENAI_BASE_URL" ""
    upsert_env_key "OPENAI_EMBEDDING_MODEL" ""
    upsert_env_key "OPENAI_EMBEDDING_DIMENSIONS" ""
    upsert_env_key "OPENMEMORY_EMBEDDINGS_BASE_URL" ""
    upsert_env_key "OPENMEMORY_EMBEDDINGS_MODEL" ""
    upsert_env_key "OPENMEMORY_EMBEDDINGS_API_KEY" ""
    upsert_env_key "OPENMEMORY_EMBEDDINGS_DIMENSIONS" ""
else
    echo ""
    echo "🏠 Local embeddings configuration (OpenAI-compatible endpoint)"

    if [ -z "$LOCAL_EMBEDDINGS_BASE_URL" ]; then
        while true; do
            read -r -p "Embeddings base URL (e.g. http://host.docker.internal:11434/v1): " LOCAL_EMBEDDINGS_BASE_URL
            if [ -n "$LOCAL_EMBEDDINGS_BASE_URL" ]; then
                break
            fi
            echo "Error: Base URL cannot be empty. Please try again."
        done
    fi

    if [ -z "$LOCAL_EMBEDDINGS_MODEL" ]; then
        while true; do
            read -r -p "Embeddings model name: " LOCAL_EMBEDDINGS_MODEL
            if [ -n "$LOCAL_EMBEDDINGS_MODEL" ]; then
                break
            fi
            echo "Error: Model name cannot be empty. Please try again."
        done
    fi

    if [ -z "$LOCAL_EMBEDDINGS_API_KEY" ]; then
        while true; do
            read -s -r -p "Embeddings API key: " LOCAL_EMBEDDINGS_API_KEY
            echo
            if [ -n "$LOCAL_EMBEDDINGS_API_KEY" ]; then
                break
            fi
            echo "Error: API key cannot be empty. Please try again."
        done
    fi

    if [ -z "$LOCAL_EMBEDDINGS_DIMENSIONS" ]; then
        while true; do
            read -r -p "Embedding dimensions (e.g. 768): " LOCAL_EMBEDDINGS_DIMENSIONS
            if [[ "$LOCAL_EMBEDDINGS_DIMENSIONS" =~ ^[0-9]+$ ]] && [ "$LOCAL_EMBEDDINGS_DIMENSIONS" -gt 0 ]; then
                break
            fi
            echo "Error: Dimensions must be a positive integer."
        done
    fi

    upsert_env_key "OPENMEMORY_EMBEDDINGS_PROVIDER" "local"

    # Keep OpenAI-compatible defaults pointed at the local embeddings endpoint.
    # OpenMemory reads OPENAI_API_KEY by default, and OPENAI_BASE_URL can redirect
    # OpenAI client calls to local-compatible servers.
    upsert_env_key "OPENAI_API_KEY" "$LOCAL_EMBEDDINGS_API_KEY"
    upsert_env_key "OPENAI_BASE_URL" "$LOCAL_EMBEDDINGS_BASE_URL"
    upsert_env_key "OPENAI_EMBEDDING_MODEL" "$LOCAL_EMBEDDINGS_MODEL"
    upsert_env_key "OPENAI_EMBEDDING_DIMENSIONS" "$LOCAL_EMBEDDINGS_DIMENSIONS"

    # Also store explicit OpenMemory-local embedding fields for future tooling.
    upsert_env_key "OPENMEMORY_EMBEDDINGS_BASE_URL" "$LOCAL_EMBEDDINGS_BASE_URL"
    upsert_env_key "OPENMEMORY_EMBEDDINGS_MODEL" "$LOCAL_EMBEDDINGS_MODEL"
    upsert_env_key "OPENMEMORY_EMBEDDINGS_API_KEY" "$LOCAL_EMBEDDINGS_API_KEY"
    upsert_env_key "OPENMEMORY_EMBEDDINGS_DIMENSIONS" "$LOCAL_EMBEDDINGS_DIMENSIONS"
fi

echo ""
echo "✅ OpenMemory MCP configured!"
echo "📁 Configuration saved to .env"
echo ""
if [ "$EMBEDDINGS_PROVIDER" = "local" ]; then
    echo "ℹ️  Local embeddings mode enabled"
    echo "   Base URL: $LOCAL_EMBEDDINGS_BASE_URL"
    echo "   Model: $LOCAL_EMBEDDINGS_MODEL"
    echo "   Dimensions: $LOCAL_EMBEDDINGS_DIMENSIONS"
else
    echo "ℹ️  OpenAI embeddings mode enabled"
fi
echo ""
echo "🚀 To start: docker compose up -d"
echo "🌐 MCP Server: http://localhost:8765"
echo "📱 Web UI: http://localhost:3001"
