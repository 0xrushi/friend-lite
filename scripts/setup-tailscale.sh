#!/bin/bash
set -e

# Friend-Lite Tailscale Configuration Script
# This script handles interactive Tailscale setup for distributed deployment

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 Step 3: Tailscale Configuration (Optional)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Tailscale enables secure distributed deployments:"
echo "  • Run services on different machines"
echo "  • Secure service-to-service communication"
echo "  • Access from mobile devices"
echo "  • Automatic HTTPS with 'tailscale serve'"
echo ""

read -p "Do you want to configure Tailscale? (y/N): " use_tailscale
if [ "$use_tailscale" != "y" ] && [ "$use_tailscale" != "Y" ]; then
    echo ""
    echo "ℹ️  Skipping Tailscale setup"
    echo "   You can run this later with: make setup-tailscale"
    exit 0
fi

echo ""

# Check if Tailscale is installed
if ! command -v tailscale >/dev/null 2>&1; then
    echo "❌ Tailscale not found"
    echo ""
    echo "📦 Install Tailscale:"
    echo "   curl -fsSL https://tailscale.com/install.sh | sh"
    echo "   sudo tailscale up"
    echo ""
    echo "Then run this setup again: make setup-tailscale"
    exit 1
fi

echo "✅ Tailscale is installed"
echo ""

# Get Tailscale status
echo "📊 Checking Tailscale status..."
if ! tailscale status >/dev/null 2>&1; then
    echo "❌ Tailscale is not running"
    echo ""
    echo "🔧 Start Tailscale:"
    echo "   sudo tailscale up"
    echo ""
    exit 1
fi

echo "✅ Tailscale is running"
echo ""
echo "📋 Your Tailscale devices:"
echo ""
tailscale status | head -n 10
echo ""

# Get Tailscale hostname
echo "🏷️  Tailscale Hostname Configuration"
echo ""
echo "Your Tailscale hostname is the DNS name assigned to THIS machine."
echo "It's different from the IP address - it's a permanent name."
echo ""
echo "📋 To find your Tailscale hostname:"
echo "   1. Run: tailscale status"
echo "   2. Look for this machine's name in the first column"
echo "   3. The full hostname is shown on the right (ends in .ts.net)"
echo ""
echo "Example output:"
echo "   anubis    100.x.x.x   anubis.tail12345.ts.net   <-- Your hostname"
echo ""

default_hostname=$(tailscale status --json 2>/dev/null | grep -A 20 '"Self"' | grep '"DNSName"' | cut -d'"' -f4 | sed 's/\.$//')
if [ -n "$default_hostname" ]; then
    echo "💡 Auto-detected hostname for THIS machine: $default_hostname"
    echo ""
fi

read -p "Tailscale hostname [$default_hostname]: " tailscale_hostname
tailscale_hostname=${tailscale_hostname:-$default_hostname}

if [ -z "$tailscale_hostname" ]; then
    echo ""
    echo "❌ No hostname provided"
    exit 1
fi

export TAILSCALE_HOSTNAME=$tailscale_hostname
echo ""
echo "✅ Using Tailscale hostname: $tailscale_hostname"
echo ""

# Save Tailscale hostname to config-docker.env
echo "💾 Saving Tailscale hostname to config-docker.env..."
if [ -f "config-docker.env" ]; then
    # Update existing TAILSCALE_HOSTNAME value
    if grep -q "^TAILSCALE_HOSTNAME=" config-docker.env; then
        # Replace existing value (handles both empty and non-empty)
        sed -i.bak "s|^TAILSCALE_HOSTNAME=.*|TAILSCALE_HOSTNAME=$tailscale_hostname|" config-docker.env
        rm -f config-docker.env.bak
    else
        # Append if not found
        echo "TAILSCALE_HOSTNAME=$tailscale_hostname" >> config-docker.env
    fi
    echo "✅ Updated config-docker.env"
else
    echo "⚠️  config-docker.env not found - skipping save"
fi
echo ""

# SSL Setup
echo "🔐 SSL Certificate Configuration"
echo ""
echo "How do you want to handle HTTPS?"
echo ""
echo "  1) Use 'tailscale serve' (automatic HTTPS)"
echo "     → Use this if you will only have a single environment"
echo ""
echo "  2) Use Caddy reverse proxy (automatic HTTPS, multiple environments)"
echo "     → Subdomain routing: dev.${tailscale_hostname}, prod.${tailscale_hostname}"
echo "     → Recommended for running multiple environments simultaneously"
echo ""
echo "  3) HTTP only (no SSL)"
echo "     → Direct port access, no HTTPS"
echo ""

read -p "Choose option (1-3) [2]: " ssl_choice
ssl_choice=${ssl_choice:-2}

case $ssl_choice in
    1)
        echo ""
        echo "✅ Will use 'tailscale serve' for automatic HTTPS"
        echo ""

        # Auto-detect most recently created environment
        LATEST_ENV_FILE=$(ls -t environments/*.env 2>/dev/null | head -1)
        if [ -n "$LATEST_ENV_FILE" ]; then
            serve_env=$(basename "$LATEST_ENV_FILE" .env)
            echo "📋 Using environment: $serve_env"
            echo ""
        else
            echo "⚠️  No environments found"
            read -p "Environment name [serve]: " serve_env
            serve_env=${serve_env:-serve}
        fi

        # Calculate ports based on environment
        if [ -f "environments/${serve_env}.env" ]; then
            # Source the environment file to get PORT_OFFSET
            source "environments/${serve_env}.env"
            BACKEND_PORT=$((8000 + ${PORT_OFFSET:-0}))
            WEBUI_PORT=$((3010 + ${PORT_OFFSET:-0}))
        else
            # Use defaults if environment doesn't exist yet
            echo "⚠️  Environment file not found: environments/${serve_env}.env"
            echo "   Using default ports"
            BACKEND_PORT=8000
            WEBUI_PORT=3010
        fi

        echo ""
        echo "📝 Configuring tailscale serve automatically..."
        echo ""
        echo "   Using ports:"
        echo "   • Backend: $BACKEND_PORT"
        echo "   • WebUI:   $WEBUI_PORT"
        echo ""

        # Stop any existing serve configuration
        tailscale serve off 2>/dev/null || true

        # Configure all routes
        echo "   Setting up routes..."
        tailscale serve --bg --set-path /api http://localhost:${BACKEND_PORT}/api
        tailscale serve --bg --set-path /auth http://localhost:${BACKEND_PORT}/auth
        tailscale serve --bg --set-path /users http://localhost:${BACKEND_PORT}/users
        tailscale serve --bg --set-path /docs http://localhost:${BACKEND_PORT}/docs
        tailscale serve --bg --set-path /health http://localhost:${BACKEND_PORT}/health
        tailscale serve --bg --set-path /readiness http://localhost:${BACKEND_PORT}/readiness
        tailscale serve --bg --set-path /ws_pcm http://localhost:${BACKEND_PORT}/ws_pcm
        tailscale serve --bg http://localhost:${WEBUI_PORT}  # Root path (frontend)

        echo ""
        echo "✅ Tailscale serve configured!"
        echo ""
        echo "📋 Your service is now accessible at:"
        echo "   https://${tailscale_hostname}/"
        echo ""
        echo "📝 Configured routes:"
        tailscale serve status
        echo ""

        export HTTPS_ENABLED=true
        # Save to config-docker.env and disable Caddy
        if [ -f "config-docker.env" ]; then
            if grep -q "^HTTPS_ENABLED=" config-docker.env; then
                sed -i.bak "s|^HTTPS_ENABLED=.*|HTTPS_ENABLED=true|" config-docker.env
                rm -f config-docker.env.bak
            else
                echo "HTTPS_ENABLED=true" >> config-docker.env
            fi

            # Disable Caddy proxy when using tailscale serve
            if grep -q "^USE_CADDY_PROXY=" config-docker.env; then
                sed -i.bak "s|^USE_CADDY_PROXY=.*|USE_CADDY_PROXY=false|" config-docker.env
                rm -f config-docker.env.bak
            else
                echo "USE_CADDY_PROXY=false" >> config-docker.env
            fi
        fi

        # Remove VITE_BASE_PATH from the environment file (not needed for tailscale serve)
        if [ -n "$serve_env" ] && [ -f "environments/${serve_env}.env" ]; then
            if grep -q "^VITE_BASE_PATH=" "environments/${serve_env}.env"; then
                sed -i.bak '/^VITE_BASE_PATH=/d' "environments/${serve_env}.env"
                rm -f "environments/${serve_env}.env.bak"

                # Add comment explaining root path deployment
                if ! grep -q "WebUI base path for root deployment" "environments/${serve_env}.env"; then
                    echo "" >> "environments/${serve_env}.env"
                    echo "# WebUI base path for root deployment (no Caddy, direct Tailscale serve)" >> "environments/${serve_env}.env"
                    echo "VITE_BASE_PATH=/" >> "environments/${serve_env}.env"
                fi
            fi
        fi
        ;;
    2)
        echo ""
        echo "✅ Caddy reverse proxy with subdomain routing"
        echo ""
        echo "📝 Your environments will be accessible at:"
        echo "   https://dev.${tailscale_hostname}/     (dev environment)"
        echo "   https://test.${tailscale_hostname}/    (test environment)"
        echo "   https://prod.${tailscale_hostname}/    (prod environment)"
        echo ""
        echo "ℹ️  Caddy will:"
        echo "   • Automatically handle HTTPS certificates via Tailscale"
        echo "   • Route to the correct environment based on subdomain"
        echo "   • Enable microphone access (requires HTTPS)"
        echo "   • Support multiple environments simultaneously"
        echo ""
        echo "📋 After starting services, you need to configure Tailscale:"
        echo "   tailscale serve https:443 http://localhost:443"
        echo ""

        export HTTPS_ENABLED=true
        export USE_CADDY_PROXY=true

        # Save to config-docker.env
        if [ -f "config-docker.env" ]; then
            if grep -q "^HTTPS_ENABLED=" config-docker.env; then
                sed -i.bak "s|^HTTPS_ENABLED=.*|HTTPS_ENABLED=true|" config-docker.env
                rm -f config-docker.env.bak
            else
                echo "HTTPS_ENABLED=true" >> config-docker.env
            fi

            if grep -q "^USE_CADDY_PROXY=" config-docker.env; then
                sed -i.bak "s|^USE_CADDY_PROXY=.*|USE_CADDY_PROXY=true|" config-docker.env
                rm -f config-docker.env.bak
            else
                echo "USE_CADDY_PROXY=true" >> config-docker.env
            fi
        fi
        ;;
    3)
        echo ""
        echo "ℹ️  Skipping SSL setup"
        export HTTPS_ENABLED=false
        # Save to config-docker.env
        if [ -f "config-docker.env" ]; then
            if grep -q "^HTTPS_ENABLED=" config-docker.env; then
                sed -i.bak "s|^HTTPS_ENABLED=.*|HTTPS_ENABLED=false|" config-docker.env
                rm -f config-docker.env.bak
            else
                echo "HTTPS_ENABLED=false" >> config-docker.env
            fi
        fi
        ;;
    *)
        echo ""
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Tailscale configuration complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
