#!/bin/bash
# Configure Tailscale Serve for Friend-Lite
# This script sets up Tailscale serve with all required routes

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 Tailscale Serve Configuration for Friend-Lite"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if Tailscale is installed
if ! command -v tailscale >/dev/null 2>&1; then
    echo "❌ Tailscale not found"
    echo ""
    echo "📦 Install Tailscale:"
    echo "   curl -fsSL https://tailscale.com/install.sh | sh"
    echo "   sudo tailscale up"
    exit 1
fi

# Check if Tailscale is running
if ! tailscale status >/dev/null 2>&1; then
    echo "❌ Tailscale is not running"
    echo ""
    echo "🔧 Start Tailscale:"
    echo "   sudo tailscale up"
    exit 1
fi

# Get environment name
if [ -n "$1" ]; then
    ENV_NAME="$1"
else
    echo "Which environment are you configuring?"
    echo ""
    echo "Available environments:"
    ls -1 environments/*.env 2>/dev/null | sed 's|environments/||;s|.env$|  |' | sed 's/^/  - /' || echo "  (none found)"
    echo ""
    read -p "Environment name [serve]: " ENV_NAME
    ENV_NAME=${ENV_NAME:-serve}
fi

# Load environment to get PORT_OFFSET
if [ -f "environments/${ENV_NAME}.env" ]; then
    echo "✅ Loading environment: $ENV_NAME"
    source "environments/${ENV_NAME}.env"
    BACKEND_PORT=$((8000 + ${PORT_OFFSET:-0}))
    WEBUI_PORT=$((3010 + ${PORT_OFFSET:-0}))
else
    echo "⚠️  Environment file not found: environments/${ENV_NAME}.env"
    echo "   Using default ports (no offset)"
    BACKEND_PORT=8000
    WEBUI_PORT=3010
fi

echo ""
echo "📝 Configuration:"
echo "   Environment: $ENV_NAME"
echo "   Backend:     localhost:$BACKEND_PORT"
echo "   WebUI:       localhost:$WEBUI_PORT"
echo ""

# Get Tailscale hostname
TAILSCALE_HOSTNAME=$(tailscale status --json 2>/dev/null | grep -A 20 '"Self"' | grep '"DNSName"' | cut -d'"' -f4 | sed 's/\.$//')
if [ -z "$TAILSCALE_HOSTNAME" ]; then
    echo "❌ Could not detect Tailscale hostname"
    exit 1
fi

echo "   Hostname:    $TAILSCALE_HOSTNAME"
echo ""

# Confirm before proceeding
read -p "Configure Tailscale serve with these settings? (y/N): " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "❌ Aborted"
    exit 0
fi

echo ""
echo "🔧 Stopping existing Tailscale serve configuration..."
tailscale serve off 2>/dev/null || true

echo ""
echo "🔧 Configuring routes..."

# Configure backend API routes
tailscale serve --bg --set-path /api http://localhost:${BACKEND_PORT}/api 2>/dev/null
echo "   ✅ /api"

tailscale serve --bg --set-path /auth http://localhost:${BACKEND_PORT}/auth 2>/dev/null
echo "   ✅ /auth"

tailscale serve --bg --set-path /users http://localhost:${BACKEND_PORT}/users 2>/dev/null
echo "   ✅ /users"

tailscale serve --bg --set-path /docs http://localhost:${BACKEND_PORT}/docs 2>/dev/null
echo "   ✅ /docs"

tailscale serve --bg --set-path /health http://localhost:${BACKEND_PORT}/health 2>/dev/null
echo "   ✅ /health"

tailscale serve --bg --set-path /readiness http://localhost:${BACKEND_PORT}/readiness 2>/dev/null
echo "   ✅ /readiness"

tailscale serve --bg --set-path /ws_pcm http://localhost:${BACKEND_PORT}/ws_pcm 2>/dev/null
echo "   ✅ /ws_pcm"

# Configure frontend (root path last)
tailscale serve --bg http://localhost:${WEBUI_PORT} 2>/dev/null
echo "   ✅ / (frontend)"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Tailscale Serve Configured Successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🌐 Your service is now accessible at:"
echo "   https://${TAILSCALE_HOSTNAME}/"
echo ""
echo "📋 Current configuration:"
echo ""
tailscale serve status
echo ""
echo "💡 To reconfigure for a different environment:"
echo "   ./scripts/configure-tailscale-serve.sh <environment-name>"
echo ""
echo "💡 To stop Tailscale serve:"
echo "   tailscale serve off"
echo ""
