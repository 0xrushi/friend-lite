# Caddy Reverse Proxy Setup

Caddy provides a **shared reverse proxy** that serves multiple Friend-Lite environments from a single domain using path-based routing.

## Architecture

**One Caddy instance serves ALL environments:**
```
https://hostname/           → Environment list landing page
https://hostname/dev/       → Dev environment (WebUI + Backend)
https://hostname/test/      → Test environment (WebUI + Backend)
https://hostname/prod/      → Prod environment (WebUI + Backend)
https://hostname/dev/mycelia/   → Dev Mycelia (if enabled)
https://hostname/test/mycelia/  → Test Mycelia (if enabled)
```

**Why this architecture?**
- Single HTTPS endpoint (ports 80/443)
- No port conflicts between environments
- Automatic SSL with Tailscale certificates
- Clean URLs with path-based routing
- Easy to add/remove environments

## Quick Start

### 1. Enable Caddy in Configuration

Edit `config-docker.env`:
```bash
USE_CADDY_PROXY=true
TAILSCALE_HOSTNAME=your-hostname.ts.net
```

### 2. Start Caddy (Once)

```bash
# Start the shared Caddy instance
make caddy-start
```

Caddy will automatically:
- Generate the Caddyfile from your environments
- Provision Tailscale certificates (if needed)
- Start serving on ports 80 and 443

### 3. Start Your Environments

```bash
# Start as many environments as you want
./start-env.sh dev
./start-env.sh test
./start-env.sh prod
```

Each environment runs on unique ports (via `PORT_OFFSET`), and Caddy routes requests based on the URL path.

### 4. Access Your Environments

Open your browser to:
- `https://your-hostname.ts.net/` - See list of all environments
- `https://your-hostname.ts.net/dev/` - Access dev environment
- `https://your-hostname.ts.net/test/` - Access test environment

## Caddy Management Commands

```bash
# Start Caddy (once for all environments)
make caddy-start

# Check if Caddy is running
make caddy-status

# View Caddy logs
make caddy-logs

# Restart Caddy (after config changes)
make caddy-restart

# Stop Caddy
make caddy-stop

# Regenerate Caddyfile (after adding/removing environments)
make caddy-regenerate
```

## How It Works

### 1. Environment Startup

When you run `./start-env.sh <env>`:
1. Loads environment config from `environments/<env>.env`
2. Generates Caddyfile with routes for all environments
3. Checks if Caddy is running
4. **Does NOT start Caddy** (you manage it separately)
5. Starts the environment services

### 2. Caddyfile Generation

The `scripts/generate-caddyfile.sh` script:
1. Scans `environments/` directory
2. Creates route for each environment:
   ```
   /<env-name>/*     → environment WebUI and Backend
   /<env-name>/mycelia/*  → Mycelia (if enabled)
   ```
3. Generates landing page with links to all environments

### 3. Request Routing

When a request comes in:
```
https://hostname/dev/api/health
         ↓
    Caddy receives request
         ↓
    Matches route: /dev/*
         ↓
    Strips /dev/ prefix
         ↓
    Forwards to: friend-lite-dev-friend-backend-1:8000/api/health
```

## Directory Structure

```
friend-lite/
├── compose/
│   └── caddy.yml               # Shared Caddy compose file
├── caddy/
│   └── Caddyfile               # Auto-generated routing config
├── certs/
│   ├── hostname.crt            # Tailscale SSL certificate
│   └── hostname.key            # Tailscale SSL key
├── environments/
│   ├── dev.env                 # Dev environment config
│   ├── test.env                # Test environment config
│   └── prod.env                # Prod environment config
└── scripts/
    └── generate-caddyfile.sh   # Caddyfile generator
```

## Common Workflows

### Adding a New Environment

```bash
# 1. Create environment config
make setup-environment
# (Creates environments/feature-123.env)

# 2. Start the environment
./start-env.sh feature-123

# 3. Regenerate Caddyfile and restart Caddy
make caddy-regenerate
make caddy-restart
```

The new environment is now accessible at `https://hostname/feature-123/`

### Removing an Environment

```bash
# 1. Stop the environment
make env-stop ENV=feature-123

# 2. Delete environment config
rm environments/feature-123.env

# 3. Regenerate Caddyfile and restart Caddy
make caddy-regenerate
make caddy-restart
```

### Updating Caddy Configuration

```bash
# 1. Make changes (add/remove environments, modify routes)
vim scripts/generate-caddyfile.sh

# 2. Regenerate and restart
make caddy-regenerate
make caddy-restart
```

## Troubleshooting

### Port Already Allocated

**Error**: `Bind for 0.0.0.0:80 failed: port is already allocated`

**Cause**: Multiple Caddy instances trying to bind to ports 80/443

**Solution**:
```bash
# Stop all Caddy containers
docker ps -a | grep caddy | awk '{print $1}' | xargs docker stop
docker ps -a | grep caddy | awk '{print $1}' | xargs docker rm

# Start the shared Caddy instance
make caddy-start
```

### Caddy Not Routing Requests

**Check Caddyfile**:
```bash
cat caddy/Caddyfile
```

**Regenerate if outdated**:
```bash
make caddy-regenerate
make caddy-restart
```

### Certificate Issues

**Check certificate status**:
```bash
ls -la certs/
openssl x509 -enddate -noout -in certs/your-hostname.crt
```

**Regenerate certificates**:
```bash
tailscale cert your-hostname.ts.net
mv your-hostname.* certs/
make caddy-restart
```

### Environment Not Found

**Error**: `404` when accessing `https://hostname/dev/`

**Cause**: Environment not running or not in Caddyfile

**Solution**:
```bash
# Check if environment is running
docker compose -p friend-lite-dev ps

# Check if Caddyfile has the route
grep "/dev/" caddy/Caddyfile

# If missing, regenerate
make caddy-regenerate
make caddy-restart
```

## Advanced Configuration

### Custom Routes

Edit `scripts/generate-caddyfile.sh` to add custom routes:

```bash
# Add custom backend route
handle_path /${env_name}/custom/* {
    reverse_proxy custom-service:8080
}
```

### Multiple Domains

To serve different environments on different domains:

```caddyfile
# In generate-caddyfile.sh, create multiple server blocks
https://dev.example.com {
    reverse_proxy friend-lite-dev-webui-1:80
}

https://prod.example.com {
    reverse_proxy friend-lite-prod-webui-1:80
}
```

### Load Balancing

For high availability, use Caddy's load balancing:

```caddyfile
reverse_proxy friend-lite-dev-backend-1:8000 friend-lite-dev-backend-2:8000 {
    lb_policy round_robin
    health_uri /health
}
```

## Migration from Per-Environment Caddy

If you previously had Caddy running per-environment:

```bash
# 1. Stop all environments
docker compose -p friend-lite-dev down
docker compose -p friend-lite-test down

# 2. Remove old Caddy containers
docker ps -a | grep caddy | awk '{print $1}' | xargs docker rm

# 3. Start shared Caddy
make caddy-start

# 4. Restart environments (without Caddy)
./start-env.sh dev
./start-env.sh test
```

## Summary

**Key Points:**
- ✅ One Caddy instance for all environments
- ✅ Caddy is managed separately from environments
- ✅ Use `make caddy-start` once, then start environments normally
- ✅ Path-based routing: `https://hostname/<env-name>/`
- ✅ Automatic certificate provisioning with Tailscale
- ✅ No port conflicts between environments

**Quick Reference:**
```bash
make caddy-start              # Start Caddy (once)
./start-env.sh dev            # Start dev environment
./start-env.sh test           # Start test environment
make caddy-status             # Check if Caddy is running
make caddy-regenerate         # Update routes after adding environments
make caddy-restart            # Apply configuration changes
```
