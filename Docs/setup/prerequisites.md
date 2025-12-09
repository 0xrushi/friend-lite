# Chronicle Prerequisites

This guide covers the software and accounts you need **before** installing Chronicle, regardless of your operating system.

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

## Required Software

Chronicle requires these tools to run. The installation process varies by platform (see platform-specific guides).

### 1. Docker & Docker Compose

**What it does**: Runs Chronicle's services in isolated containers (database, backend, web UI, etc.)

**Version required**:
- Docker 20.10.0 or higher
- Docker Compose v2.0.0 or higher (plugin version)

**Installation**: See your platform-specific guide
- [Windows with WSL2](windows-wsl2.md)
- [Windows with Git Bash](windows-gitbash.md)
- [macOS](macos.md)
- [Linux](linux.md)

### 2. Git

**What it does**: Downloads Chronicle code from GitHub

**Version required**: Git 2.0 or higher

**Verification**:
```bash
git --version
```

### 3. Make

**What it does**: Runs the setup wizard and management commands

**Version required**: Make 3.81 or higher

**Verification**:
```bash
make --version
```

### 4. Bash Shell

**What it does**: Runs Chronicle's setup scripts

**Required**: Bash 4.0 or higher

**Verification**:
```bash
bash --version
```

**Platform notes**:
- **macOS/Linux**: Pre-installed ✅
- **Windows**: Use WSL2 (recommended) or Git Bash

### 5. OpenSSL

**What it does**: Generates secure JWT tokens and SSL certificates

**Version required**: OpenSSL 1.1.1 or higher

**Verification**:
```bash
openssl version
```

---

## Required API Keys

You'll need these API keys to use Chronicle's core features. Have them ready before running the setup wizard.

### 1. OpenAI API Key (Required)

**Used for**: Extracting memories from your conversations

**Sign up**: https://platform.openai.com/signup

**Get your key**:
1. Go to https://platform.openai.com/api-keys
2. Click "+ Create new secret key"
3. Give it a name (e.g., "Chronicle")
4. Copy the key (starts with `sk-proj-...`)
5. **Save it securely** - you can only see it once!

**Cost**: Pay-as-you-go, typically $1-5/month for personal use

**Model used**: `gpt-4o-mini` (fast and affordable)

### 2. Deepgram API Key (Required)

**Used for**: Converting speech to text (transcription)

**Sign up**: https://console.deepgram.com/signup

**Get your key**:
1. Go to https://console.deepgram.com/
2. Click "API Keys" in left sidebar
3. You'll see a default API key already created
4. Click the 👁️ eye icon to reveal it
5. Copy the key

**Cost**: Free tier includes $200 credit (plenty for testing)

**Why Deepgram**: High-quality, real-time transcription with speaker diarization

---

## Optional API Keys

These enhance Chronicle but aren't required to get started.

### Mistral API Key (Optional)

**Used for**: Alternative transcription service (Voxtral models)

**Sign up**: https://console.mistral.ai/

**Get your key**:
1. Go to https://console.mistral.ai/api-keys
2. Create a new API key
3. Copy and save it

**When to use**: Alternative to Deepgram, supports Voxtral transcription models

### Hugging Face Token (Optional)

**Used for**: Speaker recognition models

**Sign up**: https://huggingface.co/join

**Get your token**:
1. Go to https://huggingface.co/settings/tokens
2. Click "New token"
3. Choose "Read" access
4. Copy the token (starts with `hf_...`)

**When to use**: If you want to identify different speakers in conversations

### Groq API Key (Optional)

**Used for**: Alternative LLM provider (faster inference)

**Sign up**: https://console.groq.com/

**When to use**: Alternative to OpenAI for memory extraction

---

## Optional Software

### Tailscale (Recommended)

**What it does**: Creates a secure network so you can access Chronicle remotely

**Why you want this**:
- Access your Chronicle dashboard from anywhere
- Connect your phone/OMI device when away from home
- No need to open firewall ports or configure port forwarding

**Sign up**: https://login.tailscale.com/start

**Installation**: See [Tailscale Setup Guide](tailscale.md)

**When to install**:
- **Windows/Linux**: Install before running `make wizard`
- **macOS**: Can install anytime

**Cost**: Free for personal use (up to 100 devices)

### Python 3.8+ (Optional)

**What it does**: Needed for development and testing outside Docker

**When you need it**:
- Running tests locally
- Backend development without Docker
- Using management scripts

**Most users don't need this** - Chronicle runs in Docker containers.

---

## Account Setup Summary

Before running `make wizard`, have these ready:

### Required ✅
- [ ] OpenAI API key
- [ ] Deepgram API key
- [ ] Admin password (choose a secure password)

### Recommended 🌟
- [ ] Tailscale account (for remote access)

### Optional 🔧
- [ ] Mistral API key (alternative transcription)
- [ ] Hugging Face token (speaker recognition)
- [ ] Groq API key (alternative LLM)

---

## Cost Breakdown

### One-Time Costs
- **$0** - All required software is free and open source

### Ongoing Costs (Pay-as-you-go)

**OpenAI (Required)**:
- ~$1-5/month for typical personal use
- Depends on number of conversations and memory processing

**Deepgram (Required)**:
- $200 free credit (lasts months for personal use)
- After credit: ~$0.0043/minute of audio
- Example: 1 hour of audio/day = ~$7.74/month

**Tailscale (Recommended)**:
- **Free** for personal use (up to 100 devices)

**Total typical monthly cost**: $1-12/month depending on usage

### Free Alternative

You can run completely free using:
- **Parakeet ASR** (offline transcription, runs on your computer)
- **Ollama** (local LLM, runs on your computer)

**Trade-off**: Requires more powerful hardware and longer processing times.

---

## Network Requirements

### Ports Used (Local Network Only)

By default, Chronicle uses these ports on `localhost`:
- **8000** - Backend API
- **5173** - Web dashboard
- **27017** - MongoDB
- **6379** - Redis
- **6333/6334** - Qdrant vector database

**Firewall**: No incoming port forwarding needed if using Tailscale

### Internet Bandwidth

**Minimal** - Most processing happens locally:
- API calls to OpenAI/Deepgram (small data transfers)
- Audio upload from devices (depends on recording frequency)
- Typical usage: <100MB/day

---

## Verification Checklist

Before proceeding to installation, verify you have:

### Software (will install in next steps)
- [ ] Docker installation method chosen
- [ ] Know how to open terminal/command prompt on your OS
- [ ] Have administrator/sudo access on your computer

### Accounts & Keys
- [ ] OpenAI account created and API key saved
- [ ] Deepgram account created and API key saved
- [ ] Admin password chosen (8+ characters, secure)
- [ ] (Optional) Tailscale account created

### System
- [ ] 20GB+ free disk space
- [ ] 8GB+ RAM (4GB minimum)
- [ ] Internet connection working

---

## Next Steps

Once you have all prerequisites:

1. Choose your platform-specific guide:
   - **Windows**: [WSL2 Setup](windows-wsl2.md) or [Git Bash Setup](windows-gitbash.md)
   - **macOS**: [macOS Setup](macos.md)
   - **Linux**: [Linux Setup](linux.md)

2. (Optional) Install Tailscale: [Tailscale Setup Guide](tailscale.md)

3. Install Chronicle dependencies and run the wizard

4. Start using Chronicle!

---

## Getting Help

### Can't get an API key?

**OpenAI requires a credit card** - If this is an issue:
- Consider using the free local alternative (Ollama)
- Share an account with a friend/family member

**Deepgram free credit** - Should be automatically applied on signup:
- Check your console dashboard at https://console.deepgram.com/
- Contact Deepgram support if credit not showing

### Don't have the hardware?

**Minimum 4GB RAM** might not be enough for all features:
- Start with cloud services (OpenAI + Deepgram)
- Disable optional services (speaker recognition, Mycelia)
- Consider a cloud VPS (Digital Ocean, Linode) for $10-20/month

### Questions?

- **GitHub Issues**: https://github.com/BasedHardware/Friend/issues
- **Documentation**: Check other guides in `docs/`
- **Community**: (Add Discord/community link if available)

---

## Summary

**Minimum to get started**:
1. A computer with 4GB+ RAM and 10GB+ disk space
2. OpenAI API key (~$1-5/month)
3. Deepgram API key (free $200 credit)
4. 30-60 minutes for installation

**Recommended setup**:
1. A computer with 8GB+ RAM and 20GB+ disk space
2. OpenAI and Deepgram API keys
3. Tailscale for remote access (free)
4. 60-90 minutes for full installation including Tailscale

Ready to install? Choose your platform guide and let's go! 🚀
