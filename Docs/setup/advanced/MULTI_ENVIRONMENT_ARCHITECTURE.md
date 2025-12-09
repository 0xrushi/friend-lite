# Multi-Environment Architecture

This document explains the Chronicle multi-environment architecture with shared services.

## Overview

Chronicle uses a **shared services** architecture that allows you to run multiple isolated environments simultaneously without port conflicts or resource duplication.

### Shared Services (One Instance for All Environments)

1. **Infrastructure** (MongoDB, Redis, Qdrant)
2. **Caddy Reverse Proxy** (HTTPS with path-based routing)

### Per-Environment Services

1. **Backend API** (unique port per environment)
2. **Web UI** (unique port per environment)
3. **Workers** (background jobs)
4. **Mycelia** (optional, unique ports)

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Shared Services                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │  MongoDB   │  │   Redis    │  │   Qdrant   │            │
│  │  :27017    │  │   :6379    │  │  :6034     │            │
│  └────────────┘  └────────────┘  └────────────┘            │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Caddy Reverse Proxy                     │   │
│  │         :80 (HTTP)    :443 (HTTPS)                   │   │
│  │   Path-based routing to all environments             │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────── ┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼────────┐  ┌────────▼───────┐  ┌────────▼────────┐
│ Dev Environment│  │Test Environment│  │Prod Environment │
│                │  │                │  │                 │
│ Backend :8000  │  │ Backend :8010  │  │ Backend :8020   │
│ WebUI   :3010  │  │ WebUI   :3020  │  │ WebUI   :3030   │
│ Workers        │  │ Workers        │  │ Workers         │
│ DB: dev        │  │ DB: test       │  │ DB: prod        │
└────────────────┘  └────────────────┘  └─────────────────┘
```

## Data Isolation

Even though infrastructure is shared, each environment is completely isolated:

### MongoDB Isolation
- Each environment uses a unique database name
- `dev` → `friend-lite-dev` database
- `test` → `friend-lite-test` database
- `prod` → `friend-lite-prod` database

### Redis Isolation
- Each environment can use a different Redis database number (0-15)
- Or use key prefixes: `env:dev:*`, `env:test:*`, `env:prod:*`

### Qdrant Isolation
- Each environment uses a different data path or collection prefix
- Collections are scoped per environment

## Quick Start Guide

### 1. First-Time Setup

```bash
# Create the shared network
docker network create chronicle-network

# Start shared infrastructure (once)
make infra-start

# Start shared Caddy (once, if using Caddy)
make caddy-start
```

### 2. Create and Start Environments

```bash
# Create environments
make wizard  # Create dev environment
make wizard  # Create test environment

# Start environments
./start-env.sh dev
./start-env.sh test

# Both environments now running on unique ports!
```

### 3. Access Your Environments

**Direct Access (via localhost ports):**
- Dev: http://localhost:3010
- Test: http://localhost:3020

**Caddy Access (via shared HTTPS):**
- Dev: https://your-hostname.ts.net/dev/
- Test: https://your-hostname.ts.net/test/
- Environment list: https://your-hostname.ts.net/

## Management Commands

### Infrastructure Management

```bash
make infra-start      # Start shared infrastructure
make infra-status     # Check infrastructure status
make infra-logs       # View infrastructure logs
make infra-restart    # Restart infrastructure
make infra-stop       # Stop infrastructure (affects all environments!)
make infra-clean      # Delete ALL data (DANGER!)
```

### Caddy Management

```bash
make caddy-start         # Start shared Caddy
make caddy-status        # Check Caddy status
make caddy-logs          # View Caddy logs
make caddy-restart       # Restart Caddy
make caddy-regenerate    # Regenerate Caddyfile after adding environments
make caddy-stop          # Stop Caddy
```

### Environment Management

```bash
make env-list            # List all environments
make env-start ENV=dev   # Start specific environment
make env-stop ENV=dev    # Stop specific environment
make env-status          # Show status of all environments
make env-clean ENV=dev   # Clean specific environment data

# Or use the script directly
./start-env.sh dev       # Start dev environment
./start-env.sh test      # Start test environment
```

## Typical Workflows

### Starting Everything from Scratch

```bash
# 1. Start shared infrastructure
make infra-start

# 2. Start shared Caddy (optional, for HTTPS)
make caddy-start

# 3. Start your environments
./start-env.sh dev
./start-env.sh test
./start-env.sh prod
```

### Adding a New Environment

```bash
# 1. Create environment config
make wizard
# (Configure: name=staging, PORT_OFFSET=30, etc.)

# 2. Start the environment
./start-env.sh staging

# 3. If using Caddy, regenerate routes
make caddy-regenerate
make caddy-restart
```

Now accessible at:
- Direct: http://localhost:3040
- Caddy: https://hostname/staging/

### Removing an Environment

```bash
# 1. Stop the environment
make env-stop ENV=staging

# 2. Delete environment config
rm environments/staging.env

# 3. If using Caddy, regenerate routes
make caddy-regenerate
make caddy-restart

# 4. Optional: Clean environment data
make env-clean ENV=staging
```

### Daily Development

```bash
# Check what's running
make env-status
make infra-status
make caddy-status

# Start working
./start-env.sh dev

# View logs
docker compose -p friend-lite-dev logs -f

# Stop when done
make env-stop ENV=dev
```

## Port Allocation

### Shared Services (Fixed Ports)

| Service | Port | Description |
|---------|------|-------------|
| MongoDB | 27017 | Database (shared) |
| Redis | 6379 | Cache (shared) |
| Qdrant HTTP | 6034 | Vector DB HTTP (shared) |
| Qdrant gRPC | 6033 | Vector DB gRPC (shared) |
| Caddy HTTP | 80 | Reverse proxy HTTP (shared) |
| Caddy HTTPS | 443 | Reverse proxy HTTPS (shared) |

### Environment-Specific Ports (Base + PORT_OFFSET)

| Service | Port Calculation | Example (offset=0) | Example (offset=10) |
|---------|-----------------|-------------------|---------------------|
| Backend | 8000 + offset | 8000 | 8010 |
| WebUI | 3010 + offset | 3010 | 3020 |
| Mycelia Backend | 5100 + offset | 5100 | 5110 |
| Mycelia Frontend | 3003 + offset | 3003 | 3013 |

## Troubleshooting

### Infrastructure Not Running

**Error**: "❌ Shared infrastructure services are not running!"

**Solution**:
```bash
make infra-start
```

### Port Conflict on Infrastructure

**Error**: "Bind for 0.0.0.0:27017 failed: port is already allocated"

**Cause**: Old per-environment infrastructure containers still running

**Solution**:
```bash
# Stop all environments
docker compose -p friend-lite-dev down
docker compose -p friend-lite-test down

# Remove old infrastructure containers
docker ps -a | grep -E "(mongo|redis|qdrant)" | grep -v "friend-lite-" | awk '{print $1}' | xargs docker rm

# Start shared infrastructure
make infra-start

# Restart environments
./start-env.sh dev
./start-env.sh test
```

### Caddy Port Conflict

**Error**: "Bind for 0.0.0.0:80 failed: port is already allocated"

**Cause**: Multiple Caddy instances or old Caddy containers

**Solution**:
```bash
# Stop all Caddy containers except the shared one
docker ps -a | grep caddy | grep -v "friend-lite-caddy" | awk '{print $1}' | xargs docker rm

# Or restart the shared Caddy
make caddy-restart
```

### Environment Can't Connect to Database

**Symptoms**: Backend shows connection errors

**Check**:
```bash
# Verify infrastructure is running
make infra-status

# Check environment variables
docker compose -p friend-lite-dev exec friend-backend env | grep MONGODB_URI

# Test connection
docker compose -p friend-lite-dev exec friend-backend bash -c "mongosh \$MONGODB_URI --eval 'db.stats()'"
```

### Data From Different Environments Mixed

**Cause**: Environment using wrong database name

**Check**:
```bash
# Check environment .env file
cat backends/advanced/.env.dev | grep MONGODB_DATABASE

# Should show: MONGODB_DATABASE=friend-lite-dev
```

## Migration from Old Architecture

If you previously had per-environment infrastructure:

### Step 1: Stop All Environments

```bash
# Stop all running environments
docker compose -p friend-lite-dev down
docker compose -p friend-lite-test down
docker compose -p friend-lite-prod down
```

### Step 2: Remove Old Infrastructure Containers

```bash
# List all infrastructure containers
docker ps -a | grep -E "(mongo|redis|qdrant|caddy)"

# Remove old per-environment infrastructure
docker ps -a | grep "friend-lite-.*-mongo" | awk '{print $1}' | xargs docker rm
docker ps -a | grep "friend-lite-.*-redis" | awk '{print $1}' | xargs docker rm
docker ps -a | grep "friend-lite-.*-qdrant" | awk '{print $1}' | xargs docker rm
docker ps -a | grep "friend-lite-.*-caddy" | awk '{print $1}' | xargs docker rm
```

### Step 3: Start Shared Services

```bash
# Start shared infrastructure
make infra-start

# Start shared Caddy (if using)
make caddy-start
```

### Step 4: Restart Environments

```bash
./start-env.sh dev
./start-env.sh test
./start-env.sh prod
```

## Benefits of This Architecture

### Resource Efficiency
- ✅ Only one MongoDB, Redis, Qdrant instance
- ✅ Reduced memory usage (shared infrastructure)
- ✅ Faster environment startup (no infrastructure initialization)

### No Port Conflicts
- ✅ Infrastructure uses fixed ports (shared)
- ✅ Environments use offset ports (isolated)
- ✅ Can run unlimited environments simultaneously

### Data Isolation
- ✅ Each environment has unique database names
- ✅ No risk of data cross-contamination
- ✅ Easy to backup/restore per-environment

### Simplified Management
- ✅ Single Caddyfile for all environments
- ✅ Unified infrastructure management
- ✅ Consistent networking (chronicle-network)

### Easy Development
- ✅ Start any number of feature branches
- ✅ Test multiple versions side-by-side
- ✅ Production-like setup on local machine

## Summary

**Key Concepts:**
- **Shared Infrastructure**: MongoDB, Redis, Qdrant (one instance, all environments)
- **Shared Caddy**: Reverse proxy with path-based routing (one instance, all environments)
- **Isolated Environments**: Unique ports, unique database names (complete isolation)
- **Simple Workflow**: `make infra-start` once, then `./start-env.sh <name>` for each environment

**Commands to Remember:**
```bash
make infra-start         # Start infrastructure (once)
make caddy-start         # Start Caddy (once)
./start-env.sh dev       # Start dev environment
./start-env.sh test      # Start test environment
make env-status          # Check what's running
```

**URLs:**
- Localhost: `http://localhost:<PORT>`
- Caddy: `https://hostname/<env-name>/`
