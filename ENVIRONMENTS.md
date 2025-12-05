# Multi-Environment Management

Friend-Lite supports running multiple environments simultaneously with isolated databases and different ports. This is perfect for:
- **Git worktrees** - Work on multiple branches simultaneously
- **Feature development** - Isolated testing environments
- **Parallel testing** - Run tests while developing

## Prerequisites

### 1. Set Up Secrets (First Time Only)

Before starting any environment, create your secrets file:

```bash
# Copy the template
cp .env.secrets.template .env.secrets

# Edit with your actual credentials
nano .env.secrets
```

Required secrets:
- `AUTH_SECRET_KEY` - JWT secret for authentication
- `ADMIN_EMAIL` / `ADMIN_PASSWORD` - Admin account credentials
- `OPENAI_API_KEY` - For LLM memory extraction
- `DEEPGRAM_API_KEY` - For transcription
- `HF_TOKEN` - For speaker recognition (if using)

**⚠️ Important**: `.env.secrets` is gitignored and will never be committed. Each developer needs their own copy.

## Quick Start

### Option 1: Using start-env.sh (Recommended)

```bash
# Start development environment
./start-env.sh dev

# Start feature branch environment
./start-env.sh feature-123

# Start with additional profiles
./start-env.sh dev --profile mycelia
./start-env.sh feature-123 --profile mycelia --profile speaker
```

### Option 2: Using Makefile

```bash
# List available environments
make env-list

# Start environment
make env-start ENV=dev
make env-start ENV=feature-123 OPTS="--profile mycelia"

# Stop environment
make env-stop ENV=dev

# Clean environment data
make env-clean ENV=dev

# Show status of all environments
make env-status
```

## How It Works

### 1. Shared Infrastructure

All environments share the same infrastructure services (defined at root level):
- MongoDB (single instance, multiple databases)
- Redis (single instance)
- Qdrant (single instance)

### 2. Environment-Specific

Each environment gets:
- **Different ports** (via PORT_OFFSET)
- **Different database names** (e.g., `friend-lite-dev`, `friend-lite-feature-123`)
- **Isolated data directories** (e.g., `data-dev/`, `data-feature-123/`)
- **Separate containers** (via COMPOSE_PROJECT_NAME)

### 3. Configuration Structure

```
environments/
├── dev.env              # Development environment
├── test.env             # Test environment
├── feature-123.env      # Feature branch
└── your-branch.env      # Create your own!
```

## Creating a New Environment

Create a new file in `environments/`:

```bash
# environments/my-feature.env
# My Feature Environment

ENV_NAME=my-feature

# Port offset (1000 = ports 9000, 4010, 28017, etc.)
PORT_OFFSET=1000

# Database names (must be unique per environment)
MONGODB_DATABASE=friend-lite-my-feature
MYCELIA_DB=mycelia-my-feature

# Data directory (must be unique per environment)
DATA_DIR=backends/advanced/data-my-feature

# Container prefix (must be unique per environment)
COMPOSE_PROJECT_NAME=friend-lite-my-feature

# Services to enable
SERVICES=backend,webui,mycelia
```

Then start it:

```bash
./start-env.sh my-feature
```

## Port Allocation

Environments automatically calculate ports based on `PORT_OFFSET`:

| Service | Base Port | Offset 0 (dev) | Offset 1000 (feature) | Offset 2000 |
|---------|-----------|----------------|-----------------------|-------------|
| Backend | 8000 | 8000 | 9000 | 10000 |
| WebUI | 3010 | 3010 | 4010 | 5010 |
| MongoDB | 27017 | 27017 | 28017 | 29017 |
| Redis | 6379 | 6379 | 7379 | 8379 |
| Qdrant HTTP | 6034 | 6034 | 7034 | 8034 |
| Mycelia Backend | 5100 | 5100 | 6100 | 7100 |

**Pro tip:** Use PORT_OFFSET in multiples of 1000 to avoid conflicts.

## Database Isolation

Each environment has its own database:

```
MongoDB Instance (shared)
├── friend-lite-dev      # Dev environment
├── friend-lite-test     # Test environment
├── friend-lite-feature-123  # Feature branch
├── mycelia-dev          # Dev mycelia
├── mycelia-test         # Test mycelia
└── mycelia-feature-123  # Feature mycelia
```

**Why this works:**
- ✅ Shared MongoDB instance (efficient)
- ✅ Isolated databases per environment (no conflicts)
- ✅ Easy cleanup (drop database when done)

## Example Workflows

### Working on Multiple Feature Branches

```bash
# Terminal 1: Main development
cd ~/projects/friend-lite
./start-env.sh dev

# Terminal 2: Feature branch (git worktree)
cd ~/projects/friend-lite-feature-auth
./start-env.sh feature-auth

# Terminal 3: Another feature
cd ~/projects/friend-lite-feature-ui
./start-env.sh feature-ui

# Now you have 3 environments running simultaneously:
# - Dev: http://localhost:8000
# - Feature-auth: http://localhost:9000
# - Feature-ui: http://localhost:10000
```

### Testing While Developing

```bash
# Terminal 1: Development environment
./start-env.sh dev

# Terminal 2: Run tests in isolated environment
./start-env.sh test
# Tests run on ports 9000, 4010, etc. - no conflict with dev!
```

### Quick Feature Testing

```bash
# Create environment config
cat > environments/quick-test.env <<EOF
ENV_NAME=quick-test
PORT_OFFSET=3000
MONGODB_DATABASE=friend-lite-quick-test
MYCELIA_DB=mycelia-quick-test
DATA_DIR=backends/advanced/data-quick-test
COMPOSE_PROJECT_NAME=friend-lite-quick-test
SERVICES=backend,webui
EOF

# Start it
./start-env.sh quick-test

# Access at http://localhost:11000

# Done? Clean up
make env-clean ENV=quick-test
```

## Configuration Layers

Friend-Lite uses a layered configuration system for **Docker Compose** deployments:

### 1. `docker-defaults.env` - System Constants
Infrastructure URLs and defaults (rarely changed):
- Service URLs: `mongodb://mongo:27017`, `redis://redis:6379`
- System paths and default ports
- CORS and networking defaults

**Change this only if**: Using external services or distributed deployment

### 2. `config-docker.env` - User Settings
Settings you actually change:
- Provider choices: `LLM_PROVIDER`, `TRANSCRIPTION_PROVIDER`, `MEMORY_PROVIDER`
- Model selections: `OPENAI_MODEL`, `OLLAMA_MODEL`
- Feature flags: `AUDIO_CROPPING_ENABLED`
- Thresholds: `SPEECH_INACTIVITY_THRESHOLD_SECONDS`

**This is what you edit** to configure application behavior

### 3. `.env.secrets` - Sensitive Credentials (Gitignored)
API keys and passwords:
- `AUTH_SECRET_KEY`, `ADMIN_PASSWORD`
- `OPENAI_API_KEY`, `DEEPGRAM_API_KEY`
- `HF_TOKEN` for speaker recognition

**Never committed to git** - each developer maintains their own copy

### 4. `environments/{name}.env` - Environment Overrides
Environment-specific settings:
- `PORT_OFFSET` - Automatic port calculation
- `MONGODB_DATABASE` - Isolated database name
- `DATA_DIR` - Separate data directory
- Any config-docker.env setting you want to override per environment

**Note**: For Kubernetes deployments, use `config-k8s.env` instead (see production deployment docs)

## Environment Variables

Each environment file can override any variable from `config-docker.env`:

```bash
# environments/custom.env

# Base settings
ENV_NAME=custom
PORT_OFFSET=2000
MONGODB_DATABASE=friend-lite-custom
DATA_DIR=backends/advanced/data-custom
COMPOSE_PROJECT_NAME=friend-lite-custom

# Override LLM settings
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2

# Override transcription
TRANSCRIPTION_PROVIDER=parakeet

# Override any config.env variable
SPEECH_INACTIVITY_THRESHOLD_SECONDS=30
```

## Cleanup

### Stop Environment

```bash
# Using script
./start-env.sh dev
# Press Ctrl+C

# Using make
make env-stop ENV=dev
```

### Clean Environment Data

```bash
# Remove all data for environment
make env-clean ENV=dev

# This deletes:
# - Data directory (backends/advanced/data-dev/)
# - Docker volumes for that environment
# - Containers for that environment
```

### Clean All Environments

```bash
# Manual cleanup
for env in dev test feature-123; do
    make env-stop ENV=$env
    make env-clean ENV=$env
done
```

## Integration with Git Worktrees

Perfect for working on multiple branches:

```bash
# Create worktrees
git worktree add ../friend-lite-feature-a feature-a
git worktree add ../friend-lite-feature-b feature-b

# In worktree A
cd ../friend-lite-feature-a
./start-env.sh feature-a
# Access at http://localhost:9000

# In worktree B
cd ../friend-lite-feature-b
./start-env.sh feature-b
# Access at http://localhost:10000

# Both run simultaneously with isolated databases!
```

## Troubleshooting

### Port Conflicts

If you get port conflicts, increase PORT_OFFSET:

```bash
# environments/my-env.env
PORT_OFFSET=5000  # Much higher offset
```

### Database Name Conflicts

Ensure each environment has unique database names:

```bash
# Check what databases exist
docker exec -it friend-lite-dev-mongo-1 mongosh --eval "show dbs"

# If conflict, rename in environment file
MONGODB_DATABASE=friend-lite-my-unique-name
```

### Container Name Conflicts

Ensure each environment has unique COMPOSE_PROJECT_NAME:

```bash
# environments/my-env.env
COMPOSE_PROJECT_NAME=friend-lite-my-unique-env

# Check running projects
docker compose ls
```

### Check Environment Status

```bash
# See all running environments
make env-status

# See specific environment
COMPOSE_PROJECT_NAME=friend-lite-dev docker compose ps
```

## Best Practices

1. **Use descriptive ENV_NAME**: `feature-auth` not `f1`
2. **Use PORT_OFFSET in thousands**: 0, 1000, 2000, etc.
3. **Clean up when done**: `make env-clean ENV=old-feature`
4. **Document custom environments**: Add comment to environment file
5. **Commit environment templates**: Share with team via git

## Advanced: Shared Infrastructure

If you want truly isolated infrastructure per environment (separate MongoDB, Redis instances), modify the PORT_OFFSET to affect infrastructure ports and use different compose profiles.

For most use cases, **shared infrastructure with isolated databases** (current approach) is the best balance of:
- ✅ Resource efficiency
- ✅ Quick startup
- ✅ Data isolation
- ✅ Easy management

## Summary

- **Simple**: `./start-env.sh <name>`
- **Isolated**: Different databases, ports, data dirs
- **Efficient**: Shared infrastructure
- **Flexible**: Override any config variable
- **Secure**: Secrets separated and gitignored
- **Git-friendly**: Perfect for worktrees
- **Clean**: Easy cleanup with `make env-clean`

Start using it:

```bash
# One-time setup: Create secrets file
cp .env.secrets.template .env.secrets
nano .env.secrets  # Add your API keys

# Create your environment
cp environments/dev.env environments/my-work.env
# Edit my-work.env with your settings

# Start it
./start-env.sh my-work

# Work on it
# http://localhost:<your-port>

# Clean up when done
make env-clean ENV=my-work
```

## Files Reference

| File | Purpose | Edit? | Git? |
|------|---------|-------|------|
| `docker-defaults.env` | System infrastructure URLs | Rarely | ✅ Yes |
| `config-docker.env` | **User settings** (what you change) | **Often** | ✅ Yes |
| `config-k8s.env` | Kubernetes configuration | As needed | ✅ Yes |
| `config.env` | Config router / documentation | No | ✅ Yes |
| `.env.secrets` | **API keys and passwords** | **Always** | ❌ No |
| `.env.secrets.template` | Template for secrets | No | ✅ Yes |
| `environments/dev.env` | Dev environment overrides | As needed | ✅ Yes |
| `environments/test.env` | Test environment overrides | As needed | ✅ Yes |
| `environments/*.env` | Custom environment overrides | As needed | ✅ Yes |
| `backends/advanced/.env.{name}` | Generated backend config | Never | ❌ No |
