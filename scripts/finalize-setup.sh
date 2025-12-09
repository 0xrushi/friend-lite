#!/bin/bash
# Friend-Lite Setup Finalization
# This script runs at the end of the wizard to:
# 1. Generate Caddyfile for all environments
# 2. Provision Tailscale certificates if Caddy is enabled

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 Step 4: Finalizing Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Load config to check for Caddy
if [ -f "config-docker.env" ]; then
    source config-docker.env
fi

# Check if Caddy proxy is enabled
if [ "$USE_CADDY_PROXY" = "true" ]; then
    echo "📝 Caddy reverse proxy is enabled"
    echo ""

    # Check if we have environments
    if [ ! -d "environments" ] || [ -z "$(ls -A environments/*.env 2>/dev/null)" ]; then
        echo "⚠️  No environments found - skipping Caddyfile generation"
        echo ""
    else
        # Generate Caddyfile for all environments
        echo "🔧 Generating Caddyfile for all environments..."
        ./scripts/generate-caddyfile.sh
        echo ""

        # Provision Tailscale certificates
        if [ -n "$TAILSCALE_HOSTNAME" ]; then
            # Create certs directory
            mkdir -p certs

            CERT_FILE="certs/${TAILSCALE_HOSTNAME}.crt"

            if [ ! -f "$CERT_FILE" ]; then
                echo "🔐 Provisioning Tailscale HTTPS certificates..."
                echo ""
                echo "   This enables HTTPS for all environment subdomains:"
                for env_file in environments/*.env; do
                    [ -f "$env_file" ] || continue
                    env_name=$(basename "$env_file" .env)
                    echo "      • https://${env_name}.${TAILSCALE_HOSTNAME}"
                done
                echo "      • https://${TAILSCALE_HOSTNAME} (default)"
                echo ""
                echo "   Running: tailscale cert ${TAILSCALE_HOSTNAME}"
                echo ""

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
                    echo "⚠️  Certificate provisioning failed."
                    echo ""
                    echo "   This may happen if:"
                    echo "   • Tailscale is not running (run: sudo tailscale up)"
                    echo "   • You don't have permission to provision certs"
                    echo ""
                    echo "   You can provision certificates manually later with:"
                    echo "      tailscale cert ${TAILSCALE_HOSTNAME}"
                    echo "      mv ${TAILSCALE_HOSTNAME}.* certs/"
                    echo ""
                    echo "   Note: Services will not start without certificates."
                    echo "   After provisioning, run: ./start-env.sh <env>"
                    echo ""
                fi
            else
                echo "✅ Tailscale certificates already exist at: $CERT_FILE"
                echo ""
            fi
        fi
    fi
else
    echo "ℹ️  Caddy reverse proxy not enabled - skipping certificate setup"
    echo ""
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Setup finalization complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
