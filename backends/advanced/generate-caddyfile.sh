#!/bin/bash
# Generate Caddyfile from template with Tailscale hostname support

set -e

TAILSCALE_HOSTNAME="${TAILSCALE_HOSTNAME:-}"

if [ -z "$TAILSCALE_HOSTNAME" ]; then
    # No Tailscale hostname - use localhost only
    echo "🔧 Generating Caddyfile for localhost only"
    sed 's/ TAILSCALE_IP//' Caddyfile.template > Caddyfile
else
    # Include Tailscale hostname
    echo "🔧 Generating Caddyfile for localhost and $TAILSCALE_HOSTNAME"
    sed "s/TAILSCALE_IP/$TAILSCALE_HOSTNAME/" Caddyfile.template > Caddyfile
fi

echo "✅ Caddyfile generated successfully"
