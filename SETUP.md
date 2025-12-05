# Friend-Lite Setup Guide

Quick setup guide for getting Friend-Lite running with Docker Compose.

## Prerequisites

- Docker and Docker Compose installed
- Git (if cloning from repository)

## Initial Setup

### 1. Set Up Secrets

Copy the secrets template and add your credentials:

```bash
cp .env.secrets.template .env.secrets
nano .env.secrets  # or use your preferred editor
```

**Required secrets:**

```bash
# Authentication
AUTH_SECRET_KEY=your-super-secret-jwt-key-change-this
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=your-secure-password

# LLM (for memory extraction)
OPENAI_API_KEY=sk-your-openai-key-here

# Transcription
DEEPGRAM_API_KEY=your-deepgram-key-here

# Optional: Speaker Recognition
HF_TOKEN=hf_your_huggingface_token
```

**⚠️ Important**: Never commit `.env.secrets` - it's gitignored for security.

### 2. Review Configuration (Optional)

Configuration is split into two files:

**`config-docker.env`** - User settings (what you change):
```bash
# LLM provider (openai, ollama, groq)
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4o-mini

# Transcription provider (deepgram, mistral, parakeet)
TRANSCRIPTION_PROVIDER=deepgram

# Memory provider (friend_lite, openmemory_mcp)
MEMORY_PROVIDER=friend_lite
```

**`docker-defaults.env`** - System constants (rarely change):
- Infrastructure URLs (`mongodb://mongo:27017`)
- Service names and ports
- Only edit if using external services

## Starting Friend-Lite

### Single Environment (Default)

Start the default development environment:

```bash
./start-env.sh dev
```

Access at:
- **Web UI**: http://localhost:3010
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### With Optional Services

Start with Mycelia memory interface:

```bash
./start-env.sh dev --profile mycelia
```

Start with speaker recognition:

```bash
./start-env.sh dev --profile speaker
```

Combine multiple profiles:

```bash
./start-env.sh dev --profile mycelia --profile speaker
```

### Multiple Environments Simultaneously

See [ENVIRONMENTS.md](ENVIRONMENTS.md) for detailed multi-environment setup.

Quick example:

```bash
# Terminal 1: Dev environment
./start-env.sh dev

# Terminal 2: Test environment (different ports/database)
./start-env.sh test
```

## Stopping Services

Press `Ctrl+C` in the terminal running the services, or:

```bash
make env-stop ENV=dev
```

## Verifying Installation

### Check Services

```bash
# Health check
curl http://localhost:8000/health

# Readiness (checks all dependencies)
curl http://localhost:8000/readiness
```

### Check Logs

```bash
# All services
docker compose logs

# Specific service
docker compose logs friend-backend

# Follow logs
docker compose logs -f friend-backend
```

### Login to Web UI

1. Open http://localhost:3010
2. Use credentials from `.env.secrets`:
   - Email: `ADMIN_EMAIL`
   - Password: `ADMIN_PASSWORD`

## Troubleshooting

### "env.secrets not found" Warning

Create the secrets file:

```bash
cp .env.secrets.template .env.secrets
nano .env.secrets  # Add your credentials
```

### Port Conflicts

If ports are already in use, edit `environments/dev.env`:

```bash
PORT_OFFSET=1000  # Changes ports to 9000, 4010, etc.
```

### Service Won't Start

Check logs:

```bash
docker compose logs <service-name>
```

Common issues:
- Missing secrets in `.env.secrets`
- Invalid API keys
- Insufficient Docker resources (increase memory limit)

### Database Issues

Reset the database (⚠️ deletes all data):

```bash
make env-clean ENV=dev
./start-env.sh dev
```

## Next Steps

- **[ENVIRONMENTS.md](ENVIRONMENTS.md)** - Multi-environment management
- **[CLAUDE.md](CLAUDE.md)** - Complete project documentation
- **Backend Docs**: http://localhost:8000/docs (when running)
- **API Reference**: [docs/api-reference.md](docs/api-reference.md)

## Configuration Files Reference

| File | Purpose | You Edit? | Git? |
|------|---------|-----------|------|
| `.env.secrets` | **Your API keys and passwords** | ✅ Always | ❌ No |
| `.env.secrets.template` | Template for secrets | No | ✅ Yes |
| `config-docker.env` | **User settings** (providers, models) | ✅ Often | ✅ Yes |
| `docker-defaults.env` | System infrastructure URLs | Rarely | ✅ Yes |
| `config-k8s.env` | Kubernetes configuration | As needed | ✅ Yes |
| `config.env` | Config router (documentation) | No | ✅ Yes |
| `environments/dev.env` | Environment overrides | As needed | ✅ Yes |
| `docker-compose.yml` | Service definitions | No | ✅ Yes |

## Support

For issues and questions:
- Check logs: `docker compose logs <service>`
- Review [CLAUDE.md](CLAUDE.md) for detailed documentation
- Check [ENVIRONMENTS.md](ENVIRONMENTS.md) for environment setup
