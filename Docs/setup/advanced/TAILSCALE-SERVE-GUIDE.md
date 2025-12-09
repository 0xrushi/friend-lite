# Tailscale Serve Setup Guide

This guide explains how to use Tailscale serve with Friend-Lite for simple, single-environment deployments.

## Overview

**Tailscale Serve** is perfect when you want:
- ✅ One environment (e.g., just "production" or "serve")
- ✅ Simple setup with automatic HTTPS
- ✅ Minimal resource usage (no Caddy container)
- ✅ Quick remote access from any device

**Use Caddy instead** if you need multiple environments (dev/test/prod) running simultaneously.

## Quick Setup

### Option 1: During Initial Setup (Wizard)

```bash
make wizard
```

When prompted for HTTPS configuration, choose **Option 1: Use 'tailscale serve'**.

The wizard will:
1. Detect your Tailscale hostname
2. Ask which environment to configure (default: `serve`)
3. Automatically configure all required routes
4. Display your service URL

### Option 2: Manual Setup (Existing Installation)

```bash
# Configure Tailscale serve for an environment
make configure-tailscale-serve

# Or run the script directly with environment name
./scripts/configure-tailscale-serve.sh serve
```

## What Gets Configured

Tailscale serve automatically sets up these routes:

```
https://your-hostname.ts.net/
├── /           → Frontend (WebUI)
├── /api        → Backend API routes
├── /auth       → Authentication endpoints
├── /users      → User management endpoints
├── /docs       → API documentation
├── /health     → Health check endpoint
├── /readiness  → Readiness probe
└── /ws_pcm     → WebSocket audio streaming
```

## Port Handling

The script automatically detects ports based on your environment's `PORT_OFFSET`:

**Example: `serve` environment with `PORT_OFFSET=10`**
- Backend: `8010` (8000 + 10)
- WebUI: `3020` (3010 + 10)

**Default environment (no offset)**
- Backend: `8000`
- WebUI: `3010`

## Checking Configuration

```bash
# View current Tailscale serve status
tailscale serve status

# Example output:
# https://orion.spangled-kettle.ts.net (tailnet only)
# |-- /         proxy http://localhost:3020
# |-- /api      proxy http://localhost:8010/api
# |-- /auth     proxy http://localhost:8010/auth
# ...
```

## Common Tasks

### Reconfigure for Different Environment

```bash
# Reconfigure for 'prod' environment
./scripts/configure-tailscale-serve.sh prod
```

### Stop Tailscale Serve

```bash
tailscale serve off
```

### Start Services with Tailscale Serve

```bash
# 1. Start your environment
./start-env.sh serve

# 2. Configure Tailscale serve (if not already configured)
make configure-tailscale-serve

# 3. Access from any device in your tailnet
# https://your-hostname.ts.net/
```

## Troubleshooting

### "Tailscale not found"

Install Tailscale:
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

### "Tailscale is not running"

Start Tailscale:
```bash
sudo tailscale up
```

### 405 Method Not Allowed / Routes Not Working

The root `.env` file may be interfering. Ensure you've removed it:
```bash
# Check if root .env exists
ls -la .env

# If it exists, back it up and remove
mv .env .env.old-backup

# Restart your environment
./start-env.sh serve
```

### Wrong Ports Being Used

Check your environment configuration:
```bash
# View environment settings
cat environments/serve.env | grep PORT_OFFSET

# Verify running services
docker ps --format "{{.Names}}: {{.Ports}}" | grep -E "(backend|webui)"
```

The ports should match: `8000 + PORT_OFFSET` for backend, `3010 + PORT_OFFSET` for webui.

## Comparison: Tailscale Serve vs Caddy

| Feature | Tailscale Serve | Caddy Reverse Proxy |
|---------|----------------|---------------------|
| **Setup** | ✅ Very simple | ⚠️ More complex |
| **Resource Usage** | ✅ Minimal | ⚠️ Extra container |
| **Multiple Envs** | ❌ One at a time | ✅ Simultaneous |
| **Path Routing** | ⚠️ Manual config | ✅ Automatic |
| **Production** | ⚠️ Basic | ✅ Production-grade |
| **Middleware** | ❌ None | ✅ Rate limiting, etc. |
| **Best For** | Personal/single env | Team/multiple envs |

## Files Modified

When you run the setup, these files are updated:

1. **`config-docker.env`**
   - `HTTPS_ENABLED=true`
   - `TAILSCALE_HOSTNAME=your-hostname.ts.net`

2. **Tailscale serve configuration** (persistent across reboots)
   - All routes configured via `tailscale serve` commands

## Security Notes

- ✅ All traffic is encrypted (HTTPS via Tailscale)
- ✅ Only accessible within your Tailscale network (tailnet)
- ✅ Tailscale handles authentication and certificates
- ⚠️ Not exposed to public internet unless you use `tailscale funnel`

## Next Steps

After configuring Tailscale serve:

1. **Test the connection**
   ```bash
   # From any device on your tailnet
   curl https://your-hostname.ts.net/health
   ```

2. **Access the web interface**
   - Open: `https://your-hostname.ts.net/`
   - Login with your credentials

3. **Connect mobile devices**
   - Install Tailscale on mobile device
   - Join your tailnet
   - Open: `https://your-hostname.ts.net/`

## Getting Help

- **View configuration**: `tailscale serve status`
- **View logs**: `docker compose -p friend-lite-serve logs -f`
- **Reconfigure**: `make configure-tailscale-serve`
- **Full setup guide**: See `TAILSCALE_GUIDE.md` for distributed deployments

## Related Documentation

- [Distributed Deployment Guide](docs/distributed-deployment.md)
- [Environment System](environments/README.md)
- [Wizard Setup](WIZARD.md)
