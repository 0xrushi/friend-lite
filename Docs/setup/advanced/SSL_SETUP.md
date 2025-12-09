# SSL/TLS Setup Guide for Friend-Lite

This guide explains how Friend-Lite handles SSL/TLS encryption for secure communication between services, with special focus on Tailscale integration.

## Overview

Friend-Lite uses SSL/TLS for:
1. **Browser → Backend/WebUI**: HTTPS for web interface and microphone access
2. **Mobile → Backend**: Secure API connections
3. **Service → Service**: Encrypted communication between distributed services (using Tailscale)

## SSL Architecture

### Development (Local)
```
Browser → Caddy (HTTPS) → Backend (HTTP internal)
                       → WebUI (HTTP internal)
```

### Production (Distributed with Tailscale)
```
Mobile → Backend (HTTPS via Tailscale)
Browser → Backend (HTTPS via Tailscale)
Speaker Service → Backend (HTTPS via Tailscale)
```

## Configuration Variables

Friend-Lite now includes SSL configuration in both Docker Compose and Kubernetes configs:

### Docker Compose (config-docker.env)
```bash
# SSL/TLS Configuration
HTTPS_ENABLED=false                           # Enable HTTPS mode
SSL_CERT_PATH=./ssl/server.crt              # Path to SSL certificate
SSL_KEY_PATH=./ssl/server.key               # Path to SSL private key
TAILSCALE_HOSTNAME=                          # Your Tailscale hostname (e.g., friend-lite.tailxxxxx.ts.net)
```

### Kubernetes (config-k8s.env)
```bash
# SSL/TLS Configuration
HTTPS_ENABLED=true                           # Always true for production
SSL_CERT_SECRET=friend-lite-tls              # K8s secret containing TLS cert
TAILSCALE_HOSTNAME=friend-lite.tailxxxxx.ts.net
```

## Setup Methods

### Method 1: Caddy for Development (Recommended for Local)

**Best for**: Local development with browser microphone access

**How it works**: Caddy automatically generates self-signed certificates for localhost

**Setup**:
```bash
# 1. Enable Caddy profile in start-env.sh
./start-env.sh dev --profile https

# 2. Access services
https://localhost/              # Web UI (accept self-signed cert warning)
wss://localhost/ws_pcm         # WebSocket audio streaming
```

**Caddy automatically handles**:
- SSL certificate generation (self-signed for localhost)
- HTTPS → HTTP proxying to internal services
- WebSocket upgrade handling
- CORS for secure origins

### Method 2: Self-Signed Certificates with Tailscale

**Best for**: Distributed deployments, testing mobile apps, service-to-service communication

**How it works**: Generate certificates for your Tailscale hostname, services communicate over Tailscale VPN

**Setup**:

1. **Get your Tailscale hostname**:
   ```bash
   tailscale status
   # Look for: friend-lite    100.x.x.x    yourname-friend-lite.tailxxxxx.ts.net
   ```

2. **Generate SSL certificates**:
   ```bash
   # For advanced backend
   cd backends/advanced
   ./ssl/generate-ssl.sh friend-lite.tailxxxxx.ts.net

   # For speaker recognition
   cd extras/speaker-recognition
   ./ssl/generate-ssl.sh speaker.tailxxxxx.ts.net
   ```

3. **Configure environment**:
   Edit `config-docker.env`:
   ```bash
   HTTPS_ENABLED=true
   SSL_CERT_PATH=./ssl/server.crt
   SSL_KEY_PATH=./ssl/server.key
   TAILSCALE_HOSTNAME=friend-lite.tailxxxxx.ts.net
   ```

4. **Update CORS origins**:
   The system automatically adds Tailscale hostname to CORS origins when `TAILSCALE_HOSTNAME` is set.

5. **Start services**:
   ```bash
   ./start-env.sh dev
   ```

6. **Access services**:
   ```
   https://friend-lite.tailxxxxx.ts.net:8000/    # Backend API
   https://friend-lite.tailxxxxx.ts.net:5173/    # Web UI
   ```

### Method 3: Tailscale HTTPS (Production)

**Best for**: Production deployments with automatic HTTPS

**How it works**: Tailscale can serve HTTPS endpoints with automatic certificate management

**Setup**:

1. **Enable Tailscale HTTPS** on your machine:
   ```bash
   tailscale serve https / http://localhost:8000
   tailscale serve https / http://localhost:5173
   ```

2. **Configure environment**:
   ```bash
   HTTPS_ENABLED=true
   TAILSCALE_HOSTNAME=friend-lite.tailxxxxx.ts.net
   ```

3. **Access services**:
   ```
   https://friend-lite.tailxxxxx.ts.net/         # Auto-managed HTTPS!
   ```

Tailscale automatically:
- Generates valid TLS certificates
- Handles certificate renewal
- Provides secure DNS names
- No browser warnings!

## Certificate Renewal

### Tailscale Certificates (Caddy Path-Based Routing)

**Certificate Lifecycle**: Tailscale certificates expire every **90 days**.

**Automatic Checking**: The `start-env.sh` script automatically checks certificate expiry when starting environments:
```bash
./start-env.sh prod
# Output:
# ✅ Tailscale certificates found at: certs/orion.spangled-kettle.ts.net.crt
#    Valid until: Mar 8 15:23:45 2025 GMT (87 days)
```

**Warning Indicators**:
- **< 30 days**: Warning shown with renewal reminder
- **Expired**: Error shown, environment won't start with HTTPS

**Manual Renewal**:
```bash
# Check current expiry
openssl x509 -enddate -noout -in certs/your-hostname.ts.net.crt

# Renew certificate
tailscale cert your-hostname.ts.net

# Move new certificates to certs directory
mv your-hostname.ts.net.crt certs/
mv your-hostname.ts.net.key certs/

# Restart Caddy to use new certificates
docker compose -p friend-lite-prod restart caddy
```

**Certificate Location**: `/Users/you/repos/friend-lite/certs/`

**Caddy Mount**: Certificates are mounted read-only in Caddy container:
```yaml
volumes:
  - ../../../certs:/certs:ro  # Read-only access
```

**No Downtime Renewal**:
1. Obtain new certificate with `tailscale cert`
2. Replace files in `certs/` directory
3. Reload Caddy: `docker compose exec caddy caddy reload`

**Production Best Practice**: Set a calendar reminder to renew certificates 2 weeks before expiry.

### Self-Signed Certificates

**Certificate Lifecycle**: Generated with 365-day validity by default.

**Renewal**:
```bash
# Regenerate certificate
cd backends/advanced
./ssl/generate-ssl.sh your-hostname.ts.net

# Restart services
docker compose restart
```

**Automated Checking**: Self-signed certificates are checked the same way as Tailscale certificates by `start-env.sh`.

## Service-Specific SSL Setup

### Advanced Backend + WebUI

**Option A: Caddy (Development)**
```bash
cd backends/advanced
docker compose --profile https up --build -d
```

**Option B: Direct HTTPS (Production)**
1. Generate certificates:
   ```bash
   ./ssl/generate-ssl.sh friend-lite.tailxxxxx.ts.net
   ```

2. Configure `.env`:
   ```bash
   HTTPS_ENABLED=true
   SSL_CERT_PATH=./ssl/server.crt
   SSL_KEY_PATH=./ssl/server.key
   ```

### Speaker Recognition

The speaker recognition service includes both backend and frontend:

1. **Generate certificates**:
   ```bash
   cd extras/speaker-recognition
   ./ssl/generate-ssl.sh speaker.tailxxxxx.ts.net
   ```

2. **Configure environment**:
   ```bash
   HTTPS_ENABLED=true
   SSL_CERT_PATH=./ssl/server.crt
   SSL_KEY_PATH=./ssl/server.key
   SPEAKER_BACKEND_URL=https://speaker.tailxxxxx.ts.net:8085
   ```

3. **Update Advanced Backend** to use HTTPS speaker service:
   In `config-docker.env`:
   ```bash
   SPEAKER_SERVICE_URL=https://speaker.tailxxxxx.ts.net:8085
   ```

### Mobile App

The mobile app needs to trust your SSL certificates:

**For self-signed certificates**:
1. Install Tailscale on mobile device
2. Access services via Tailscale hostname
3. Accept certificate warnings (development only)

**For production**:
Use Tailscale HTTPS (Method 3) - no warnings!

## Integration with start-env.sh

The `start-env.sh` script can automatically configure SSL based on environment:

### Example: SSL-enabled environment

Create `environments/prod.env`:
```bash
# Environment name
ENV_NAME=prod
PORT_OFFSET=0

# Database isolation
MONGODB_DATABASE=friend-lite-prod
MYCELIA_DB=mycelia-prod

# SSL Configuration
HTTPS_ENABLED=true
TAILSCALE_HOSTNAME=friend-lite.tailxxxxx.ts.net
```

Start with SSL:
```bash
./start-env.sh prod
```

The script will:
1. Load SSL configuration from environment file
2. Export `HTTPS_ENABLED` and `TAILSCALE_HOSTNAME`
3. Update CORS origins to include Tailscale hostname
4. Generate backend `.env` with SSL settings

## Certificate Generation Details

The `ssl/generate-ssl.sh` script creates certificates with:

**Subject Alternative Names (SANs)**:
- `localhost`
- `*.localhost`
- `127.0.0.1`
- Your Tailscale hostname or IP

**Usage**:
```bash
# IP address
./ssl/generate-ssl.sh 100.83.66.30

# Domain name
./ssl/generate-ssl.sh friend-lite.tailxxxxx.ts.net

# Dual (for Tailscale - both hostname and IP work)
./ssl/generate-ssl.sh friend-lite.tailxxxxx.ts.net
```

## CORS Configuration

SSL affects CORS origins. The system automatically handles this:

### Development (HTTP)
```bash
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### Development (HTTPS via Caddy)
```bash
CORS_ORIGINS=https://localhost,https://localhost:5173
```

### Production (HTTPS via Tailscale)
```bash
CORS_ORIGINS=https://friend-lite.tailxxxxx.ts.net,https://friend-lite.tailxxxxx.ts.net:8000,https://friend-lite.tailxxxxx.ts.net:5173
```

The configuration system automatically updates CORS when `TAILSCALE_HOSTNAME` is set.

## Troubleshooting

### Issue: "Certificate not valid for hostname"

**Cause**: Certificate SAN doesn't include your Tailscale hostname

**Solution**: Regenerate certificate with correct hostname:
```bash
./ssl/generate-ssl.sh your-correct-hostname.tailxxxxx.ts.net
```

### Issue: Browser shows "NET::ERR_CERT_AUTHORITY_INVALID"

**Cause**: Self-signed certificate not trusted by browser

**Solutions**:
1. **Development**: Accept the warning (click "Advanced" → "Proceed")
2. **Production**: Use Tailscale HTTPS (automatic trust)
3. **Advanced**: Install certificate in system trust store

### Issue: Mobile app can't connect

**Cause**: Mobile OS doesn't trust self-signed certificate

**Solutions**:
1. **Recommended**: Use Tailscale HTTPS (Method 3)
2. **Development**: Install Tailscale on mobile device, access via Tailscale network
3. **Testing only**: Disable SSL verification in app (NOT for production)

### Issue: Service-to-service SSL errors

**Cause**: Services can't verify each other's certificates

**Solution**: Use Tailscale network - all services can communicate securely:
```bash
# In config-docker.env
SPEAKER_SERVICE_URL=https://speaker.tailxxxxx.ts.net:8085
PARAKEET_ASR_URL=https://parakeet.tailxxxxx.ts.net:8767
```

### Issue: WebSocket connections fail over HTTPS

**Cause**: WebSocket upgrade headers not properly proxied

**Solutions**:
1. **Caddy**: Already handles WebSocket upgrades automatically
2. **Direct HTTPS**: Ensure WebSocket endpoint uses `wss://` scheme
3. **Check CORS**: WebSocket origins must be in CORS_ORIGINS

## Security Best Practices

### Development
✅ Self-signed certificates are fine
✅ Caddy with automatic localhost certs
✅ Accept browser warnings

### Production
✅ Use Tailscale HTTPS (automatic cert management)
✅ Or: Use Let's Encrypt certificates (if publicly accessible)
✅ Never commit certificates to git
✅ Rotate certificates regularly (365 days for self-signed)
✅ Use strong private keys (2048-bit RSA minimum)

### Network Security
✅ Use Tailscale for service-to-service communication
✅ Restrict Tailscale ACLs to necessary services
✅ Keep services on private networks (not public internet)
✅ Use HTTPS for all external endpoints

## Quick Reference

| Use Case | Method | Setup Command |
|----------|--------|---------------|
| Local development | Caddy | `./start-env.sh dev --profile https` |
| Tailscale testing | Self-signed | `./ssl/generate-ssl.sh <tailscale-host>` |
| Production | Tailscale HTTPS | `tailscale serve https / http://localhost:8000` |
| Distributed services | Tailscale VPN | Configure service URLs with Tailscale hostnames |

## Advanced: Distributed Deployment

For distributed deployments (e.g., backend on one machine, speaker service on another):

1. **Install Tailscale on all machines**:
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up
   ```

2. **Generate certificates on each machine**:
   ```bash
   # Machine 1 (backend)
   ./ssl/generate-ssl.sh backend.tailxxxxx.ts.net

   # Machine 2 (speaker)
   ./ssl/generate-ssl.sh speaker.tailxxxxx.ts.net
   ```

3. **Configure cross-service communication**:
   ```bash
   # On backend machine - config-docker.env
   SPEAKER_SERVICE_URL=https://speaker.tailxxxxx.ts.net:8085

   # On speaker machine - config-docker.env
   BACKEND_URL=https://backend.tailxxxxx.ts.net:8000
   ```

4. **Services automatically discover each other via Tailscale**!

## Summary

SSL/TLS configuration in Friend-Lite is flexible and adapts to your deployment:

- **Local development**: Caddy with automatic self-signed certs
- **Testing**: Self-signed certs for Tailscale hostnames
- **Production**: Tailscale HTTPS for automatic certificate management
- **Distributed**: Tailscale VPN for secure service-to-service communication

The configuration system automatically handles CORS, certificate paths, and service URLs based on your settings in `config-docker.env` or `config-k8s.env`.
