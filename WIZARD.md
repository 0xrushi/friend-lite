# Friend-Lite Setup Wizard

The Friend-Lite setup wizard provides an interactive, step-by-step guide to configure your Friend-Lite instance.

## Quick Start

```bash
make wizard
```

This single command will guide you through:
1. 🔐 **Secrets Configuration** - API keys and passwords
2. 🌐 **Tailscale Setup** - Distributed deployment (optional)
3. 📦 **Environment Creation** - Custom isolated environment
4. 🚀 **Start Instructions** - How to launch your instance

## What Gets Configured

### 1. Secrets (.env.secrets)

The wizard creates and configures `.env.secrets` with:

**Required:**
- `AUTH_SECRET_KEY` - JWT signing key (auto-generated if not provided)
- `ADMIN_EMAIL` - Admin account email
- `ADMIN_PASSWORD` - Admin account password
- `OPENAI_API_KEY` - For memory extraction and LLM features

**Recommended:**
- `DEEPGRAM_API_KEY` - For speech-to-text transcription

**Optional:**
- `MISTRAL_API_KEY` - Alternative transcription provider
- `HF_TOKEN` - Hugging Face token for speaker recognition models

**Security:**
- File is automatically gitignored
- Backups created before modifications
- Sensitive data never committed to repository

### 2. Tailscale Configuration (Optional)

If you choose to configure Tailscale:

**Checks performed:**
- ✅ Tailscale is installed
- ✅ Tailscale is running
- ✅ Your Tailscale devices are listed

**Configuration:**
- Auto-detects your Tailscale hostname
- Offers three SSL/TLS options:
  1. **Tailscale Serve** - Automatic HTTPS (recommended)
  2. **Self-signed certificates** - Generated for your hostname
  3. **Skip SSL** - HTTP only (development)

**SSL Certificate Generation:**
- Creates certificates with SANs for your Tailscale hostname
- Certificates valid for 365 days
- Stored in `backends/advanced/ssl/`

### 3. Environment Creation

Creates isolated environment in `environments/<name>.env` with:

**Environment Settings:**
- `ENV_NAME` - Unique identifier
- `COMPOSE_PROJECT_NAME` - Docker Compose project name
- `PORT_OFFSET` - Unique port offset to avoid conflicts

**Database Isolation:**
- `MONGODB_DATABASE` - Separate MongoDB database
- `MYCELIA_DB` - Separate Mycelia database

**Optional Services:**
- Mycelia (memory management UI)
- Speaker Recognition
- OpenMemory MCP
- Parakeet ASR (offline transcription)

**Tailscale Integration:**
- `TAILSCALE_HOSTNAME` - Your Tailscale hostname
- `HTTPS_ENABLED` - SSL/TLS enabled flag

## Individual Setup Commands

You can run each step independently:

### Configure Secrets

```bash
make setup-secrets
```

**Interactive prompts for:**
- JWT secret key (or auto-generate)
- Admin email and password
- API keys (OpenAI, Deepgram, Mistral, HF)

**Handles existing files:**
- Detects existing `.env.secrets`
- Offers to reconfigure or keep existing
- Creates timestamped backups

### Configure Tailscale

```bash
make setup-tailscale
```

**Validates:**
- Tailscale installation
- Tailscale running status
- Available devices

**Configures:**
- Hostname detection and confirmation
- SSL/TLS method selection
- Certificate generation (if option 2 selected)

### Create Environment

```bash
make setup-environment
```

**Prompts for:**
- Environment name (default: dev)
- Port offset (default: 0)
- Database names (defaults: `friend-lite-<env>`, `mycelia-<env>`)
- Optional services to enable
- Tailscale hostname (if not already set)

**Creates:**
- Environment file in `environments/<name>.env`
- Timestamped backups of existing environments

## Example Workflows

### Workflow 1: Local Development (No Tailscale)

```bash
make wizard
```

**Choices:**
1. Configure secrets → Yes (provide API keys)
2. Configure Tailscale → No
3. Environment name → `dev`
4. Port offset → `0`
5. Optional services → None

**Result:**
```bash
./start-env.sh dev
# Services available at http://localhost:8000 and http://localhost:5173
```

### Workflow 2: Distributed Deployment with Tailscale

```bash
make wizard
```

**Choices:**
1. Configure secrets → Yes (provide API keys)
2. Configure Tailscale → Yes
   - SSL option → 1 (Tailscale Serve)
3. Environment name → `prod`
4. Port offset → `0`
5. Optional services → Mycelia, Speaker Recognition

**Result:**
```bash
./start-env.sh prod

# After services start:
tailscale serve https / http://localhost:8000
tailscale serve https / http://localhost:5173

# Services available at https://your-hostname.tailxxxxx.ts.net
```

### Workflow 3: Multiple Environments

```bash
# Create dev environment
make wizard
# Choose: dev, port offset 0

# Create staging environment
make setup-environment
# Choose: staging, port offset 100

# Create prod environment
make setup-environment
# Choose: prod, port offset 200

# Run multiple environments simultaneously
./start-env.sh dev &
./start-env.sh staging &
./start-env.sh prod &
```

## Port Allocation

Each environment uses a unique port offset:

| Environment | Offset | Backend | WebUI | MongoDB | Redis | Qdrant |
|-------------|--------|---------|-------|---------|-------|--------|
| dev         | 0      | 8000    | 5173  | 27017   | 6379  | 6333   |
| staging     | 100    | 8100    | 5273  | 27117   | 6479  | 6433   |
| prod        | 200    | 8200    | 5373  | 27217   | 6579  | 6533   |

## Environment File Structure

Generated environment file (`environments/<name>.env`):

```bash
# ========================================
# Friend-Lite Environment: dev
# ========================================
# Generated: 2025-01-23 10:30:00

# Environment identification
ENV_NAME=dev
COMPOSE_PROJECT_NAME=friend-lite-dev

# Port offset (each environment needs unique ports)
PORT_OFFSET=0

# Data directory (isolated per environment)
DATA_DIR=./data/dev

# Database names (isolated per environment)
MONGODB_DATABASE=friend-lite-dev
MYCELIA_DB=mycelia-dev

# Optional services
SERVICES=mycelia speaker

# Tailscale configuration (if configured)
TAILSCALE_HOSTNAME=friend-lite.tailxxxxx.ts.net
HTTPS_ENABLED=true
```

## Configuration Files Overview

After running the wizard, your configuration structure:

```
friend-lite/
├── .env.secrets                    # Secrets (gitignored)
├── .env.secrets.template           # Template for secrets
├── config-docker.env               # Docker Compose user settings
├── docker-defaults.env             # Docker Compose system defaults
├── config-k8s.env                  # Kubernetes configuration
├── environments/                   # Environment-specific configs
│   ├── dev.env                    # Development environment
│   ├── staging.env                # Staging environment
│   └── prod.env                   # Production environment
└── backends/advanced/
    ├── ssl/                       # SSL certificates (if generated)
    │   ├── server.crt
    │   └── server.key
    └── .env -> .env.dev           # Symlink to active environment
```

## Checking Configuration Status

```bash
# Check if secrets are configured
make check-secrets

# View wizard help
make help | grep -A 20 "SETUP WIZARD"

# List existing environments
ls -1 environments/*.env | sed 's|environments/||;s|.env$||'
```

## Tailscale Hostname Confusion?

If you're confused about what to enter for "Tailscale hostname", see **[`TAILSCALE_GUIDE.md`](TAILSCALE_GUIDE.md)** for a detailed explanation.

**Quick answer:** Run `tailscale status` and use the **third column** (ends in `.ts.net`)

Example:
```
anubis    100.83.66.30   anubis.tail12345.ts.net   linux   -
                         ^^^^^^^^^^^^^^^^^^^^^^^^
                         Use this!
```

## Troubleshooting

### Issue: "openssl: command not found"

**Cause:** OpenSSL not installed (needed for JWT key generation)

**Solution:**
```bash
# macOS
brew install openssl

# Ubuntu/Debian
sudo apt-get install openssl

# Or provide your own JWT key when prompted
```

### Issue: "tailscale: command not found"

**Cause:** Tailscale not installed

**Solution:**
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

### Issue: "Tailscale is not running"

**Cause:** Tailscale installed but not started

**Solution:**
```bash
sudo tailscale up
```

### Issue: "Cannot create .env.secrets: Permission denied"

**Cause:** Insufficient permissions

**Solution:**
```bash
# Ensure you're in the project root
cd /path/to/friend-lite

# Check file permissions
ls -la .env.secrets.template

# Fix if needed
chmod 644 .env.secrets.template
```

### Issue: "Port already in use"

**Cause:** Another environment or service using the same ports

**Solution:**
- Use a different port offset (100, 200, etc.)
- Stop conflicting services
- Check running environments: `docker ps`

## Advanced Usage

### Running Wizard Non-Interactively

While the wizard is designed to be interactive, you can prepare files ahead of time:

```bash
# 1. Create .env.secrets manually
cp .env.secrets.template .env.secrets
# Edit .env.secrets with your values

# 2. Create environment file manually
mkdir -p environments
cat > environments/dev.env <<EOF
ENV_NAME=dev
COMPOSE_PROJECT_NAME=friend-lite-dev
PORT_OFFSET=0
DATA_DIR=./data/dev
MONGODB_DATABASE=friend-lite-dev
MYCELIA_DB=mycelia-dev
SERVICES=
EOF

# 3. Start services directly
./start-env.sh dev
```

### Customizing Generated Environments

After wizard creates an environment, you can edit it:

```bash
# Edit environment file
nano environments/dev.env

# Add custom variables
echo "CUSTOM_FEATURE_FLAG=true" >> environments/dev.env

# Restart environment to apply changes
./start-env.sh dev
```

### Regenerating SSL Certificates

```bash
# For a specific Tailscale hostname
cd backends/advanced
./ssl/generate-ssl.sh your-hostname.tailxxxxx.ts.net

# Or run Tailscale setup again
cd ../..
make setup-tailscale
```

## Integration with Existing Setup

The wizard works alongside existing configuration:

**Preserves:**
- Existing `.env.secrets` (asks before overwriting)
- Existing environments (asks before overwriting)
- `config-docker.env` and `config-k8s.env` (not modified)

**Creates:**
- `.env.secrets` (if missing)
- Environment-specific configs in `environments/`
- SSL certificates in `backends/advanced/ssl/` (if requested)

**Does not modify:**
- `config-docker.env` - Manual user settings
- `docker-defaults.env` - System defaults
- `config-k8s.env` - Kubernetes configuration

## Next Steps After Wizard

1. **Start your environment:**
   ```bash
   ./start-env.sh <env-name>
   ```

2. **Access services:**
   - Backend API: `http://localhost:8000` (or your Tailscale URL)
   - Web UI: `http://localhost:5173` (or your Tailscale URL)

3. **If using Tailscale Serve:**
   ```bash
   tailscale serve https / http://localhost:8000
   tailscale serve https / http://localhost:5173
   ```

4. **Check service health:**
   ```bash
   curl http://localhost:8000/health
   ```

5. **View logs:**
   ```bash
   docker compose logs -f friend-backend
   ```

6. **Explore documentation:**
   - `ENVIRONMENTS.md` - Environment system details
   - `SSL_SETUP.md` - SSL/TLS configuration
   - `SETUP.md` - Complete setup guide

## Wizard vs Manual Setup

| Aspect | Wizard (`make wizard`) | Manual Setup |
|--------|----------------------|--------------|
| Speed | 🟢 5-10 minutes | 🟡 15-30 minutes |
| Errors | 🟢 Guided validation | 🔴 Manual validation needed |
| Documentation | 🟢 Auto-generates configs | 🟡 Must read docs |
| Flexibility | 🟡 Standard options | 🟢 Full customization |
| Best For | First-time setup, quick start | Advanced users, custom needs |

## Summary

The Friend-Lite wizard provides a streamlined, interactive setup experience:

✅ Guides through all configuration steps
✅ Validates inputs and system requirements
✅ Creates timestamped backups
✅ Supports both local and distributed deployments
✅ Integrates with Tailscale for secure networking
✅ Can be run in parts or as a complete flow
✅ Preserves existing configurations

Run `make wizard` to get started in minutes!
