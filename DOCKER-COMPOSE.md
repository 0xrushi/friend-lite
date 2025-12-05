# Friend-Lite Docker Compose Guide

Friend-Lite uses a **unified root-level Docker Compose** structure that makes it easy to start all services from one place.

## Quick Start

```bash
# From project root
cd /path/to/friend-lite

# Create shared network (first time only)
docker network create chronicle-network

# Start core services
docker compose up

# Start with optional services
docker compose --profile mycelia up              # With Mycelia memory service
docker compose --profile speaker up              # With speaker recognition
docker compose --profile asr up                  # With offline ASR (Parakeet)
docker compose --profile observability up        # With Langfuse monitoring

# Multiple profiles
docker compose --profile mycelia --profile speaker up
```

## Project Structure

```
friend-lite/                          # PROJECT ROOT
├── docker-compose.yml                # Root compose file (YOU START HERE)
├── compose/
│   ├── advanced-backend.yml          # Includes backends/advanced/
│   ├── asr-services.yml              # Offline ASR (Parakeet)
│   ├── speaker-recognition.yml       # Voice identification
│   ├── openmemory.yml                # OpenMemory MCP server
│   └── observability.yml             # Langfuse monitoring
├── backends/
│   └── advanced/
│       ├── docker-compose.yml        # Advanced backend (included by root)
│       ├── compose/
│       │   ├── infrastructure.yml    # Mongo, Redis, Qdrant
│       │   ├── backend.yml           # Friend-backend, Workers
│       │   ├── frontend.yml          # WebUI
│       │   ├── mycelia.yml           # Mycelia (--profile mycelia)
│       │   ├── optional-services.yml # Caddy, Ollama, etc.
│       │   └── overrides/
│       │       ├── dev.yml           # Development settings
│       │       ├── test.yml          # Test environment
│       │       └── prod.yml          # Production config
│       └── .env                      # Backend configuration
└── extras/
    ├── asr-services/                 # ASR services
    ├── speaker-recognition/          # Speaker identification
    ├── mycelia/                      # Memory service
    └── openmemory-mcp/               # OpenMemory server
```

## Service Profiles

| Profile | Services | When to Use |
|---------|----------|-------------|
| **(none)** | Core backend, WebUI, databases | Default development |
| `mycelia` | + Mycelia memory service | Advanced memory features |
| `speaker` | + Speaker recognition | Voice identification |
| `asr` | + Parakeet offline ASR | Offline transcription |
| `openmemory` | + OpenMemory MCP server | Cross-client memory |
| `observability` | + Langfuse monitoring | LLM tracing/debugging |
| `https` | + Caddy reverse proxy | HTTPS for microphone access |

## Usage Examples

### Development (Default)

```bash
# Start from project root
docker compose up

# Services started:
# - mongo (27017)
# - redis (6379)
# - qdrant (6033/6034)
# - friend-backend (8000)
# - workers
# - webui (3010)
```

### With Mycelia

```bash
docker compose --profile mycelia up

# Additional services:
# - mycelia-backend (5100)
# - mycelia-frontend (3003)
```

### With Speaker Recognition

```bash
docker compose --profile speaker up

# Additional services:
# - speaker-recognition (8085)
```

### With Offline ASR

```bash
docker compose --profile asr up

# Additional services:
# - parakeet-asr (8767)
```

### Everything

```bash
docker compose --profile mycelia --profile speaker --profile asr up

# Starts all available services
```

### Testing Environment

```bash
# Uses isolated test databases and ports
docker compose -f docker-compose.yml -f backends/advanced/compose/overrides/test.yml up

# Test services use different ports:
# - Backend: 8001 (dev: 8000)
# - WebUI: 3001 (dev: 3010)
# - Mongo: 27018 (dev: 27017)
# - Redis: 6380 (dev: 6379)
```

### Production

```bash
# From project root
docker compose -f docker-compose.yml -f backends/advanced/compose/overrides/prod.yml up -d

# Production changes:
# - No source code mounting
# - Resource limits applied
# - Always restart policy
```

## Environment Configuration

### backends/advanced/.env

This is the main configuration file for the backend:

```bash
# Authentication
AUTH_SECRET_KEY=your-super-secret-jwt-key
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=your-secure-password

# LLM Configuration
LLM_PROVIDER=openai
OPENAI_API_KEY=your-openai-key
OPENAI_MODEL=gpt-4o-mini

# Speech-to-Text
DEEPGRAM_API_KEY=your-deepgram-key
TRANSCRIPTION_PROVIDER=deepgram

# Memory Provider
MEMORY_PROVIDER=friend_lite  # or: mycelia, openmemory_mcp

# Optional: Speaker Recognition
SPEAKER_SERVICE_URL=http://speaker-recognition:8085

# Optional: Offline ASR
PARAKEET_ASR_URL=http://parakeet-asr:8767
```

### Port Customization

Override default ports via environment variables:

```bash
# In your shell or .env file
export BACKEND_PORT=9000
export WEBUI_PORT=3015
export MONGO_PORT=27018

docker compose up
```

## Common Commands

```bash
# View merged configuration
docker compose config

# List all services
docker compose config --services

# List services with profiles
docker compose --profile mycelia config --services

# Start specific services only
docker compose up mongo redis qdrant

# View logs
docker compose logs -f friend-backend
docker compose logs -f  # All services

# Stop everything
docker compose down

# Stop and remove volumes (⚠️ DELETES DATA!)
docker compose down -v

# Rebuild and restart
docker compose build
docker compose up --build

# Restart single service
docker compose restart friend-backend
```

## Service Access

| Service | URL | Default Port |
|---------|-----|--------------|
| Backend API | http://localhost:8000 | 8000 |
| Backend Health | http://localhost:8000/readiness | 8000 |
| Web UI | http://localhost:3010 | 3010 |
| Mycelia Backend | http://localhost:5100 | 5100 |
| Mycelia Frontend | http://localhost:3003 | 3003 |
| Speaker Recognition | http://localhost:8085 | 8085 |
| Parakeet ASR | http://localhost:8767 | 8767 |
| OpenMemory API | http://localhost:8765 | 8765 |
| Langfuse | http://localhost:3000 | 3000 |
| MongoDB | mongodb://localhost:27017 | 27017 |
| Redis | redis://localhost:6379 | 6379 |
| Qdrant HTTP | http://localhost:6034 | 6034 |
| Qdrant gRPC | http://localhost:6033 | 6033 |

## Architecture Benefits

### Before: Multiple Compose Files

```bash
# Had to remember which directory to cd into
cd backends/advanced && docker compose up
cd extras/speaker-recognition && docker compose up
cd extras/asr-services && docker compose up
# ... manage multiple compose instances separately
```

### After: Unified Root Compose

```bash
# Start everything from project root
docker compose --profile speaker --profile asr up

# Services coordinate automatically
# Shared network, unified management
```

### Why This Is Better

1. **Single Entry Point**: Always start from project root
2. **Unified Control**: One command starts all related services
3. **Modular**: Include only what you need via profiles
4. **Environment Switching**: Easy dev/test/prod switching
5. **Clean Configs**: No redundant environment variables

## Environment Switching

### Development (Default)

```bash
# From project root
docker compose up

# Uses:
# - backends/advanced/docker-compose.yml (includes dev.yml)
# - Source code mounted for hot reload
# - Development-friendly settings
```

### Testing

```bash
# Isolated test environment
docker compose -f docker-compose.yml \
  -f backends/advanced/compose/overrides/test.yml up

# Uses:
# - Different ports (no conflicts)
# - Test database (test_db)
# - Test credentials
# - Fast timeouts for testing
```

### Production

```bash
# Production configuration
docker compose -f docker-compose.yml \
  -f backends/advanced/compose/overrides/prod.yml up -d

# Uses:
# - No source mounting
# - Resource limits
# - Always restart policy
# - Production-ready settings
```

## Advanced: Selective Service Management

### Start Only Infrastructure

```bash
docker compose up mongo redis qdrant -d
```

### Start Only Backend (assumes infra running)

```bash
docker compose up friend-backend workers
```

### Add Services Incrementally

```bash
# Start core
docker compose up -d

# Later, add speaker recognition
docker compose --profile speaker up -d

# Even later, add mycelia
docker compose --profile mycelia up -d
```

## Troubleshooting

### "Network chronicle-network not found"

```bash
# Create the shared network
docker network create chronicle-network

# Then retry
docker compose up
```

### Port Conflicts

```bash
# Check what's using ports
lsof -i :8000
lsof -i :27017

# Stop conflicting services
docker compose down

# Or use custom ports
BACKEND_PORT=9000 docker compose up
```

### "Service conflicts with imported resource"

This means a service is defined in multiple compose files. Check:
- Are you accidentally including the same compose file twice?
- Do you have duplicate service names?

### Services Not Starting with Profile

Ensure you use `--profile`:

```bash
# ❌ Wrong - mycelia won't start
docker compose up

# ✅ Correct - mycelia starts
docker compose --profile mycelia up
```

### View Merged Configuration

```bash
# See final merged config
docker compose config

# With profiles
docker compose --profile mycelia --profile speaker config

# Save to file
docker compose config > merged-config.yml
```

## Migration from Old Structure

If you were previously running services from individual directories:

### Old Way

```bash
# Multiple terminals, multiple directories
cd backends/advanced && docker compose up
cd extras/speaker-recognition && docker compose up
```

### New Way

```bash
# Single command from project root
cd /path/to/friend-lite
docker compose --profile speaker up
```

## Next Steps

1. **First Time Setup**:
   ```bash
   cd /path/to/friend-lite
   docker network create chronicle-network
   cp backends/advanced/.env.template backends/advanced/.env
   # Edit .env with your API keys
   ```

2. **Start Development**:
   ```bash
   docker compose up
   ```

3. **Access Services**:
   - Backend: http://localhost:8000
   - Web UI: http://localhost:3010
   - Backend Health: http://localhost:8000/readiness

4. **Enable Optional Services**:
   ```bash
   # Add services as needed
   docker compose --profile mycelia up
   docker compose --profile speaker up
   ```

## Additional Resources

- [Backend Compose Guide](backends/advanced/DOCKER-COMPOSE-GUIDE.md) - Detailed backend-specific docs
- [Docker Compose Include Documentation](https://docs.docker.com/compose/how-tos/multiple-compose-files/include/)
- [Docker Compose Profiles](https://docs.docker.com/compose/how-tos/profiles/)

## Summary

**Root Docker Compose** gives you:
- ✅ Single entry point for all services
- ✅ Unified service management
- ✅ Profile-based optional services
- ✅ Easy environment switching
- ✅ Clean, modular configuration

Always start from **project root** (`/path/to/friend-lite/`) and use `docker compose` commands!
