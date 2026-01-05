# Chronicle Initialization System

## Quick Links

- **👉 [Start Here: Quick Start Guide](../quickstart.md)** - Main setup path for new users
- **📚 [Full Documentation](../CLAUDE.md)** - Comprehensive reference  
- **🏗️ [Architecture Details](features.md)** - Technical deep dive

---

## Overview

Chronicle uses a unified initialization system with clean separation of concerns:

- **Configuration** (`wizard.py`) - Set up service configurations, API keys, and .env files
- **Service Management** (`services.py`) - Start, stop, and manage running services

The root orchestrator handles service selection and delegates configuration to individual service scripts. In general, setup scripts only configure and do not start services automatically. Exceptions: `extras/asr-services` and `extras/openmemory-mcp` are startup scripts. This prevents unnecessary resource usage and gives you control over when services actually run.

> **New to Chronicle?** Most users should start with the [Quick Start Guide](../quickstart.md) instead of this detailed reference.

## Architecture

### Root Orchestrator
- **Location**: `/wizard.py`
- **Purpose**: Service selection and delegation only
- **Does NOT**: Handle service-specific configuration or duplicate setup logic

### Service Scripts
- **Backend**: `backends/advanced/init.py` - Complete Python-based interactive setup
- **Speaker Recognition**: `extras/speaker-recognition/init.sh` - Python-based interactive setup
- **ASR Services**: `extras/asr-services/setup.sh` - Service startup script
- **OpenMemory MCP**: `extras/openmemory-mcp/setup.sh` - External server startup

## Usage

### Orchestrated Setup (Recommended)
Set up multiple services together with automatic URL coordination:

```bash
# From project root
uv run --with-requirements setup-requirements.txt python wizard.py
```

The orchestrator will:
1. Show service status and availability
2. Let you select which services to configure
3. Automatically pass service URLs between services
4. Display next steps for starting services

### Individual Service Setup
Each service can be configured independently:

```bash
# Advanced Backend only
cd backends/advanced
uv run --with-requirements setup-requirements.txt python init.py

# Speaker Recognition only  
cd extras/speaker-recognition
./setup.sh

# ASR Services only
cd extras/asr-services  
./setup.sh

# OpenMemory MCP only
cd extras/openmemory-mcp
./setup.sh
```

## Service Details

### Advanced Backend
- **Interactive setup** for authentication, LLM, transcription, and memory providers
- **Accepts arguments**: `--speaker-service-url`, `--parakeet-asr-url`
- **Generates**: Complete `.env` file with all required configuration
- **Default ports**: Backend (8000), WebUI (5173)

### Speaker Recognition  
- **Prompts for**: Hugging Face token, compute mode (cpu/gpu)
- **Service port**: 8085
- **WebUI port**: 5173
- **Requires**: HF_TOKEN for pyannote models

### ASR Services
- **Starts**: Parakeet ASR service via Docker Compose  
- **Service port**: 8767
- **Purpose**: Offline speech-to-text processing
- **No configuration required**

### OpenMemory MCP
- **Starts**: External OpenMemory MCP server
- **Service port**: 8765  
- **WebUI**: Available at http://localhost:8765
- **Purpose**: Cross-client memory compatibility

## Automatic URL Coordination

When using the orchestrated setup, service URLs are automatically configured:

| Service Selected     | Backend Gets Configured With                                     |
|----------------------|-------------------------------------------------------------------|
| Speaker Recognition  | `SPEAKER_SERVICE_URL=http://host.docker.internal:8085`           |
| ASR Services         | `PARAKEET_ASR_URL=http://host.docker.internal:8767`              |

This eliminates the need to manually configure service URLs when running services on the same machine.
Note (Linux): If `host.docker.internal` is unavailable, add `extra_hosts: - "host.docker.internal:host-gateway"` to the relevant services in `docker-compose.yml`.

## Key Benefits

✅ **No Unnecessary Building** - Services are only started when you explicitly request them  
✅ **Resource Efficient** - Parakeet ASR won't start if you're using cloud transcription  
✅ **Clean Separation** - Configuration vs service management are separate concerns  
✅ **Unified Control** - Single command to start/stop all services  
✅ **Selective Starting** - Choose which services to run based on your current needs

## Service URLs

### Default Service Endpoints
- **Backend API**: http://localhost:8000
- **Backend WebUI**: http://localhost:5173  
- **Speaker Recognition**: http://localhost:8085
- **Speaker Recognition WebUI**: http://localhost:5173
- **Parakeet ASR**: http://localhost:8767
- **OpenMemory MCP**: http://localhost:8765

### Container-to-Container Communication
Services use `host.docker.internal` for inter-container communication:
- `http://127.0.0.1:8085` - Speaker Recognition
- `http://host.docker.internal:8767` - Parakeet ASR  
- `http://host.docker.internal:8765` - OpenMemory MCP

## Service Management

Chronicle now separates **configuration** from **service lifecycle management**:

### Unified Service Management
Use the `services.py` script for all service operations:

```bash
# Start all configured services
uv run --with-requirements setup-requirements.txt python services.py start --all --build

# Start specific services
uv run --with-requirements setup-requirements.txt python services.py start backend speaker-recognition

# Check service status
uv run --with-requirements setup-requirements.txt python services.py status

# Restart all services
uv run --with-requirements setup-requirements.txt python services.py restart --all

# Restart specific services
uv run --with-requirements setup-requirements.txt python services.py restart backend

# Stop all services
uv run --with-requirements setup-requirements.txt python services.py stop --all

# Stop specific services
uv run --with-requirements setup-requirements.txt python services.py stop asr-services openmemory-mcp
```

**Convenience Scripts:**
```bash
# Quick start (from project root)
./start.sh

# Quick restart (from project root)
./restart.sh
```

**Important Notes:**
- **Restart** restarts containers without rebuilding - use for configuration changes (.env updates)
- **For code changes**, use `stop` + `start --build` to rebuild images
- Example: `uv run --with-requirements setup-requirements.txt python services.py stop --all && uv run --with-requirements setup-requirements.txt python services.py start --all --build`

### Manual Service Management
You can also manage services individually:

```bash
# Advanced Backend
cd backends/advanced && docker compose up --build -d

# Speaker Recognition  
cd extras/speaker-recognition && docker compose up --build -d

# ASR Services (only if using offline transcription)
cd extras/asr-services && docker compose up --build -d

# OpenMemory MCP (only if using openmemory_mcp provider)
cd extras/openmemory-mcp && docker compose up --build -d
```

## Startup Flow (Mermaid) diagram

Chronicle has two layers:
- **Setup** (`wizard.sh` / `wizard.py`) writes config (`.env`, `config/config.yml`, optional SSL/nginx config).
- **Run** (`start.sh` / `services.py`) starts the configured services via `docker compose`.

```mermaid
flowchart TD
  A[wizard.sh] --> B[uv run --with-requirements setup-requirements.txt wizard.py]
  B --> C{Select services}
  C --> D[backends/advanced/init.py\nwrites backends/advanced/.env + config/config.yml]
  C --> E[extras/speaker-recognition/init.py\nwrites extras/speaker-recognition/.env\noptionally ssl/* + nginx.conf]
  C --> F[extras/asr-services/init.py\nwrites extras/asr-services/.env]
  C --> G[extras/openmemory-mcp/setup.sh]

  A2[start.sh] --> B2[uv run --with-requirements setup-requirements.txt python services.py start ...]
  B2 --> H{For each service:\n.env exists?}
  H -->|yes| I[services.py runs docker compose\nin each service directory]
  H -->|no| J[Skip (not configured)]
```

### How `services.py` picks Speaker Recognition variants

`services.py` reads `extras/speaker-recognition/.env` and decides:
- `COMPUTE_MODE=cpu|gpu|strixhalo` → choose compose profile
- `REACT_UI_HTTPS=true|false` → include `nginx` (HTTPS) vs run only API+UI (HTTP)

```mermaid
flowchart TD
  S[start.sh] --> P[services.py]
  P --> R[Read extras/speaker-recognition/.env]
  R --> M{COMPUTE_MODE}
  M -->|cpu| C1[docker compose --profile cpu up ...]
  M -->|gpu| C2[docker compose --profile gpu up ...]
  M -->|strixhalo| C3[docker compose --profile strixhalo up ...]
  R --> H{REACT_UI_HTTPS}
  H -->|true| N1[Start profile default set:\nAPI + web-ui + nginx]
  H -->|false| N2[Start only:\nAPI + web-ui (no nginx)]
```

### CPU + NVIDIA share the same `Dockerfile` + `pyproject.toml`

Speaker recognition uses a single dependency definition with per-accelerator “extras”:
- `extras/speaker-recognition/pyproject.toml` defines extras like `cpu`, `cu121`, `cu126`, `cu128`, `strixhalo`.
- `extras/speaker-recognition/Dockerfile` takes `ARG PYTORCH_CUDA_VERSION` and runs:
  - `uv sync --extra ${PYTORCH_CUDA_VERSION}`
  - `uv run --extra ${PYTORCH_CUDA_VERSION} ...`
- `extras/speaker-recognition/docker-compose.yml` sets that build arg per profile:
  - CPU profile defaults to `PYTORCH_CUDA_VERSION=cpu`
  - GPU profile defaults to `PYTORCH_CUDA_VERSION=cu126` and reserves NVIDIA GPUs

AMD/ROCm (Strix Halo) uses the same `pyproject.toml` interface (the `strixhalo` extra), but a different build recipe (`extras/speaker-recognition/Dockerfile.strixhalo`) and ROCm device mappings, because the base image provides the torch stack.

## Configuration Files

### Generated Files
- `backends/advanced/.env` - Backend configuration with all services
- `extras/speaker-recognition/.env` - Speaker service configuration
- All services backup existing `.env` files automatically

### Required Dependencies
- **Root**: `setup-requirements.txt` (rich>=13.0.0)
- **Backend**: `setup-requirements.txt` (rich>=13.0.0, pyyaml>=6.0.0)
- **Extras**: No additional setup dependencies required

## Troubleshooting

### Common Issues
- **Port conflicts**: Check if services are already running on default ports
- **Permission errors**: Ensure scripts are executable (`chmod +x setup.sh`)
- **Missing dependencies**: Install uv and ensure setup-requirements.txt dependencies available
- **Service startup failures**: Check Docker is running and has sufficient resources

### Service Health Checks
```bash
# Backend health
curl http://localhost:8000/health

# Speaker Recognition health  
curl http://localhost:8085/health

# ASR service health
curl http://localhost:8767/health
```

### Logs and Debugging
```bash
# View service logs
docker compose logs [service-name]

# Backend logs
cd backends/advanced && docker compose logs chronicle-backend

# Speaker Recognition logs
cd extras/speaker-recognition && docker compose logs speaker-service
```
