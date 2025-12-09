#!/bin/bash
set -e

# Friend-Lite Secrets Configuration Script
# This script handles interactive configuration of API keys and passwords

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔐 Step 1: Secrets Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if .env.secrets exists
if [ -f ".env.secrets" ]; then
    echo "ℹ️  .env.secrets already exists"
    echo ""
    read -p "Do you want to reconfigure it? (y/N): " reconfigure

    if [ "$reconfigure" != "y" ] && [ "$reconfigure" != "Y" ]; then
        echo ""
        echo "✅ Keeping existing secrets"
        exit 0
    fi

    echo ""
    echo "📝 Backing up existing .env.secrets..."
    cp .env.secrets .env.secrets.backup.$(date +%Y%m%d_%H%M%S)
    echo ""
else
    echo "📝 Creating .env.secrets from template..."
    cp .env.secrets.template .env.secrets
    echo "✅ Created .env.secrets"
    echo ""
fi

echo "🔑 Required Secrets Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Let's configure your secrets. Press Enter to skip optional ones."
echo ""

# JWT Secret Key (required)
echo "1️⃣  JWT Secret Key (required for authentication)"
echo "   This is used to sign JWT tokens. Should be random and secure."
read -p "   Enter JWT secret key (or press Enter to generate): " jwt_key

if [ -z "$jwt_key" ]; then
    jwt_key=$(openssl rand -hex 32 2>/dev/null || cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 64 | head -n 1)
    echo "   ✅ Generated random key: $jwt_key"
fi

sed -i.bak "s|^AUTH_SECRET_KEY=.*|AUTH_SECRET_KEY=$jwt_key|" .env.secrets && rm .env.secrets.bak
echo ""

# Admin credentials
echo "2️⃣  Admin Account"
read -p "   Admin email (default: admin@example.com): " admin_email
admin_email=${admin_email:-admin@example.com}
sed -i.bak "s|^ADMIN_EMAIL=.*|ADMIN_EMAIL=$admin_email|" .env.secrets && rm .env.secrets.bak

read -sp "   Admin password: " admin_pass
echo ""
if [ -n "$admin_pass" ]; then
    sed -i.bak "s|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD=$admin_pass|" .env.secrets && rm .env.secrets.bak
fi
echo ""

# OpenAI API Key
echo "3️⃣  OpenAI API Key (required for memory extraction)"
echo "   Get your key from: https://platform.openai.com/api-keys"
read -p "   OpenAI API key (or press Enter to skip): " openai_key

if [ -n "$openai_key" ]; then
    # Strip any leading = or whitespace
    openai_key=$(echo "$openai_key" | sed 's/^[[:space:]]*=*//')
    sed -i.bak "s|^OPENAI_API_KEY=.*|OPENAI_API_KEY=$openai_key|" .env.secrets && rm .env.secrets.bak
fi
echo ""

# Deepgram API Key
echo "4️⃣  Deepgram API Key (recommended for transcription)"
echo "   Get your key from: https://console.deepgram.com/"
read -p "   Deepgram API key (or press Enter to skip): " deepgram_key

if [ -n "$deepgram_key" ]; then
    # Strip any leading = or whitespace
    deepgram_key=$(echo "$deepgram_key" | sed 's/^[[:space:]]*=*//')
    sed -i.bak "s|^DEEPGRAM_API_KEY=.*|DEEPGRAM_API_KEY=$deepgram_key|" .env.secrets && rm .env.secrets.bak
fi
echo ""

# Mistral API Key (optional)
echo "5️⃣  Mistral API Key (optional - alternative transcription)"
echo "   Get your key from: https://console.mistral.ai/"
read -p "   Mistral API key (or press Enter to skip): " mistral_key

if [ -n "$mistral_key" ]; then
    # Strip any leading = or whitespace
    mistral_key=$(echo "$mistral_key" | sed 's/^[[:space:]]*=*//')
    sed -i.bak "s|^MISTRAL_API_KEY=.*|MISTRAL_API_KEY=$mistral_key|" .env.secrets && rm .env.secrets.bak
fi
echo ""

# Hugging Face Token (optional)
echo "6️⃣  Hugging Face Token (optional - for speaker recognition models)"
echo "   Get your token from: https://huggingface.co/settings/tokens"
read -p "   HF token (or press Enter to skip): " hf_token

if [ -n "$hf_token" ]; then
    # Strip any leading = or whitespace
    hf_token=$(echo "$hf_token" | sed 's/^[[:space:]]*=*//')
    sed -i.bak "s|^HF_TOKEN=.*|HF_TOKEN=$hf_token|" .env.secrets && rm .env.secrets.bak
fi
echo ""

# Neo4j Password (optional)
echo "7️⃣  Neo4j Password (optional - for OpenMemory graph memory)"
echo "   If you're using OpenMemory with Neo4j graph memory, set a secure password."
echo "   This is required if you enabled Neo4j in your environment setup."
read -sp "   Neo4j password (or press Enter to skip): " neo4j_pass
echo ""

if [ -n "$neo4j_pass" ]; then
    sed -i.bak "s|^NEO4J_PASSWORD=.*|NEO4J_PASSWORD=$neo4j_pass|" .env.secrets && rm .env.secrets.bak
    echo "   ✅ Neo4j password set"
else
    echo "   ⚠️  Skipped - using default password (not recommended for production)"
fi
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Secrets configured successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📄 Configuration saved to: .env.secrets"
echo "🔒 This file is gitignored and will not be committed"
echo ""
