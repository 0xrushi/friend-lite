# Chronicle Installation Guide

Choose your operating system to get started with Chronicle:

## 🪟 Windows

**Complete step-by-step guide for Windows users (including WSL2 setup)**

👉 **[Windows Setup Guide](Docs/setup/windows-wsl2.md)**

- Fresh Windows install instructions
- Automated dependency installation
- Docker Desktop + WSL2 setup
- Everything explained in detail

**Quick Install (if you already have WSL2):**
```bash
# In WSL2 Ubuntu terminal
curl -fsSL https://raw.githubusercontent.com/BasedHardware/Friend/main/scripts/install-deps.sh | bash
cd ~
git clone https://github.com/BasedHardware/Friend.git chronicle
cd chronicle
make wizard
```

---

## 🍎 macOS

**Installation for Mac users**

### Prerequisites

Install Homebrew (if not already installed):
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Quick Install

```bash
# Install dependencies automatically
curl -fsSL https://raw.githubusercontent.com/BasedHardware/Friend/main/scripts/install-deps.sh | bash

# Clone and setup
git clone https://github.com/BasedHardware/Friend.git chronicle
cd chronicle
make wizard
```

The dependency installer will:
- Install Git, Make, curl via Homebrew
- Install Docker Desktop (or prompt you to install manually)
- Verify everything is working

---

## 🐧 Linux

**Installation for Linux users (Ubuntu/Debian)**

### Quick Install

```bash
# Install dependencies automatically
curl -fsSL https://raw.githubusercontent.com/BasedHardware/Friend/main/scripts/install-deps.sh | bash

# Clone and setup
git clone https://github.com/BasedHardware/Friend.git chronicle
cd chronicle
make wizard
```

The dependency installer will:
- Install Git, Make, curl, wget
- Install Docker Engine and Docker Compose
- Add you to the docker group
- Start Docker service

**Manual Installation (if you prefer)**

```bash
# Update package lists
sudo apt-get update

# Install basic tools
sudo apt-get install -y git make curl wget ca-certificates gnupg

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# Clone and setup Chronicle
git clone https://github.com/BasedHardware/Friend.git friend-lite
cd friend-lite
make wizard
```

---

## What the Dependency Installer Does

The `install-deps.sh` script automatically:

✅ **Detects your operating system** (Ubuntu, Debian, macOS, or WSL2)

✅ **Installs required tools:**
- Git (version control)
- Make (build automation)
- curl (HTTP client)
- Docker & Docker Compose (container platform)

✅ **Verifies everything works** and shows you the versions

✅ **Provides guidance** for Docker Desktop on WSL2/macOS

✅ **Smart about Docker:**
- On **WSL2**: Recommends Docker Desktop, or offers to install Docker Engine
- On **Linux**: Installs Docker Engine directly
- On **macOS**: Offers to install Docker Desktop via Homebrew

---

## After Installation

Once dependencies are installed, run the setup wizard:

```bash
cd chronicle
make wizard
```

The wizard will guide you through:
1. 🔐 Configuring API keys and passwords
2. 🌐 Optional Tailscale setup (for remote access)
3. 📦 Creating your environment configuration
4. 🚀 Starting Chronicle

---

## What You'll Need

Before running `make wizard`, have these ready:

### Required
- **OpenAI API Key** (for memory extraction): https://platform.openai.com/api-keys
- **Deepgram API Key** (for transcription): https://console.deepgram.com/
- **Admin password** (choose a secure password for your Chronicle account)

### Optional
- **Mistral API Key** (alternative transcription): https://console.mistral.ai/
- **Hugging Face Token** (speaker recognition): https://huggingface.co/settings/tokens
- **Tailscale account** (remote access): https://login.tailscale.com/start

---

## System Requirements

### Minimum
- **CPU**: 2 cores
- **RAM**: 4GB
- **Disk**: 10GB free space
- **OS**:
  - Windows 10 (version 2004+) or Windows 11
  - macOS 10.15 (Catalina) or higher
  - Ubuntu 20.04+ or Debian 11+

### Recommended
- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Disk**: 20GB+ free space
- **SSD** for better Docker performance

### For Speaker Recognition (Optional)
- **RAM**: 8GB+ recommended
- **GPU**: NVIDIA GPU with CUDA support (optional, improves performance)

---

## Troubleshooting

### "curl: command not found"

**Linux/WSL2:**
```bash
sudo apt-get update
sudo apt-get install curl
```

**macOS:**
```bash
# curl is pre-installed, but if missing:
brew install curl
```

### "Permission denied" when running docker

**You need to log out and back in** after the installer adds you to the docker group.

Or run:
```bash
newgrp docker
```

### Docker Desktop not starting on Windows

1. Enable virtualization in BIOS
2. Enable WSL2: `wsl --install`
3. Restart computer
4. Start Docker Desktop

### Docker not found in WSL2

Make sure Docker Desktop has WSL2 integration enabled:
1. Open Docker Desktop
2. Settings → Resources → WSL Integration
3. Enable "Ubuntu-22.04"
4. Click "Apply & Restart"

---

## Advanced: Manual Dependency Installation

If you prefer not to use the automated script, see:
- **Windows**: [Docs/setup/windows-wsl2.md](Docs/setup/windows-wsl2.md) - Step-by-step manual instructions
- **Windows (Git Bash)**: [Docs/setup/windows-gitbash.md](Docs/setup/windows-gitbash.md) - Alternative setup
- **Linux**: [Docs/setup/linux.md](Docs/setup/linux.md) - Linux manual setup
- **macOS**: [Docs/setup/macos.md](Docs/setup/macos.md) - macOS manual setup

---

## Getting Help

- **GitHub Issues**: https://github.com/BasedHardware/Friend/issues
- **Documentation**: Check `CLAUDE.md` for comprehensive docs
- **Setup Wizard Issues**: See `WIZARD.md` for wizard-specific help

---

## Next Steps

After installation:

1. **Start Chronicle**: `./start-env.sh dev`
2. **Access Web Dashboard**: http://localhost:5173
3. **Check API Docs**: http://localhost:8000/docs
4. **Connect Your Device**: Follow the mobile app setup guide

Welcome to Chronicle! 🚀
