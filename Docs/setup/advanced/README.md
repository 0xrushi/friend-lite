# Advanced Setup Guides

This directory contains advanced and optional setup guides for Chronicle.

## Available Guides

### Multi-Environment Setup

- **[ENVIRONMENTS.md](ENVIRONMENTS.md)** - Multi-environment management
  - Running multiple environments simultaneously
  - Git worktree integration
  - Isolated databases per environment
  - Port offset configuration

- **[MULTI_ENVIRONMENT_ARCHITECTURE.md](MULTI_ENVIRONMENT_ARCHITECTURE.md)** - Architecture deep dive
  - Shared vs per-environment services
  - Data isolation strategies
  - Resource optimization
  - Production deployment patterns

### Network & Access

- **[CADDY_SETUP.md](CADDY_SETUP.md)** - Caddy reverse proxy setup
  - Multi-environment path-based routing
  - Shared HTTPS endpoint
  - Automatic SSL with Tailscale

- **[SSL_SETUP.md](SSL_SETUP.md)** - SSL/TLS certificate configuration
  - Self-signed certificates
  - Let's Encrypt setup
  - Certificate management

- **[TAILSCALE-SERVE-GUIDE.md](TAILSCALE-SERVE-GUIDE.md)** - Tailscale serve detailed guide
  - Advanced `tailscale serve` configuration
  - Custom port mapping
  - Multiple service setup

- **[TAILSCALE_GUIDE.md](TAILSCALE_GUIDE.md)** - Technical Tailscale reference
  - Hostname vs IP concepts
  - Finding your Tailscale hostname
  - Network configuration details

## When to Use These Guides

These guides are **optional** and intended for:

- **Advanced users** who need specific features
- **Production deployments** requiring SSL/TLS
- **Multi-environment setups** with Caddy proxy
- **Power users** customizing Tailscale configuration

## For Beginners

If you're just getting started, you **don't need** these guides. Follow the main setup:

1. Start with **[INSTALL.md](../../../INSTALL.md)** for your operating system
2. Follow the **setup wizard** (`make wizard`)
3. Complete **basic Tailscale setup** in [Docs/setup/tailscale.md](../tailscale.md)

Come back to these advanced guides when you need specific features!

---

**Need help?** See the main [Chronicle Documentation](../../../CLAUDE.md)
