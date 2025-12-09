# Chronicle Setup Guide - macOS

**Quick installation guide for macOS users.**

macOS has excellent support for Chronicle with native Docker and Unix tools.

---

## Prerequisites

Before starting:
- ✅ Read [Prerequisites Guide](prerequisites.md) and have your API keys ready
- ✅ **macOS 10.15 (Catalina) or higher**
- ✅ **At least 20GB free disk space**
- ✅ **8GB RAM** (4GB minimum)
- ✅ **Administrator access**

---

## Quick Install (TL;DR)

For experienced users:

```bash
# Install dependencies
curl -fsSL https://raw.githubusercontent.com/BasedHardware/Friend/main/scripts/install-deps.sh | bash

# Clone and setup
git clone https://github.com/BasedHardware/Friend.git chronicle
cd chronicle
make wizard

# Start Chronicle
./start-env.sh dev
```

Access at: http://localhost:3010

---

## Detailed Installation

### Step 1: Install Homebrew (if needed)

Homebrew is macOS's package manager. Check if you have it:

```bash
brew --version
```

**If you see a version number**, skip to Step 2.

**If "command not found"**, install Homebrew:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow the prompts:
- Press `Enter` to continue
- Enter your Mac password when asked
- Wait for installation (~5 minutes)

**After installation**, run the commands it shows to add Homebrew to your PATH.

⏱️ **Time: 5 minutes**

---

### Step 2: Install Dependencies Automatically

We have a script that installs everything you need:

```bash
curl -fsSL https://raw.githubusercontent.com/BasedHardware/Friend/main/scripts/install-deps.sh | bash
```

**What this installs:**
- Git (version control)
- Make (build tool)
- curl (HTTP client)
- Docker Desktop (container platform)

**Docker Desktop installation:**

The script will ask:
```
Install Docker Desktop via Homebrew? (y/N):
```

**Option 1: Type `y`** - Installs automatically via Homebrew
**Option 2: Type `N`** - Download manually from docker.com

**If you choose automatic install:**
- Wait for Homebrew to download and install Docker Desktop (~10 minutes)
- After install: Open Docker Desktop from Applications
- Accept the service agreement
- Docker will start (whale icon in menu bar)

**Verify installation:**
```bash
git --version
make --version
docker --version
docker compose version
```

All should show version numbers.

⏱️ **Time: 15 minutes**

---

### Step 3: Install Tailscale (Optional but Recommended)

Tailscale enables remote access to Chronicle from your phone or anywhere.

**Quick install:**
```bash
brew install tailscale
sudo brew services start tailscale
sudo tailscale up
```

Follow login prompts in your browser.

**Detailed instructions**: See [Tailscale Setup Guide](tailscale.md)

⏱️ **Time: 5 minutes**

---

### Step 4: Install Chronicle

#### 4.1 Clone the Repository

```bash
cd ~
git clone https://github.com/BasedHardware/Friend.git chronicle
cd chronicle
```

#### 4.2 Run Setup Wizard

```bash
make wizard
```

The wizard will ask you questions. **Have your API keys ready from the [Prerequisites Guide](prerequisites.md).**

**Secrets Configuration:**
- JWT secret: Press Enter (auto-generates)
- Admin email: Press Enter or enter your email
- Admin password: Enter a secure password
- OpenAI API key: Paste your key
- Deepgram API key: Paste your key
- Optional keys: Press Enter to skip

**Tailscale (if installed):**
- Configure Tailscale?: Type `y` if you installed it in Step 3
- Choose option 1 for automatic HTTPS

**Environment:**
- Environment name: Press Enter (use "dev")
- Port offset: Press Enter (use default)
- Database names: Press Enter for defaults
- Optional services: Type `N` for all (can enable later)

⏱️ **Time: 5 minutes**

---

### Step 5: Start Chronicle

```bash
./start-env.sh dev
```

**First-time startup:**
- Downloads Docker images (~5 minutes)
- Builds services
- Starts 5 containers

**You'll see:**
```
✅ Services Started Successfully!

🌐 Access Your Services:

   📱 Web Dashboard:     http://localhost:3010
   🔌 Backend API:       http://localhost:8000
   📚 API Docs:          http://localhost:8000/docs
```

⏱️ **Time: 10 minutes (first time)**

---

### Step 6: Access Chronicle

1. Open browser: **http://localhost:3010**
2. Log in with your admin credentials
3. Explore the dashboard!

**Check API documentation:**
- http://localhost:8000/docs

🎉 **You're all set!**

⏱️ **Time: 2 minutes**

---

## Managing Chronicle

### Start/Stop/Restart

```bash
cd ~/chronicle

# Start
./start-env.sh dev

# Stop
docker compose down

# Restart
docker compose restart

# View logs
docker compose logs -f
```

### Update Chronicle

```bash
cd ~/chronicle
git pull
docker compose up -d --build
```

### Check Status

```bash
docker compose ps
```

---

## Troubleshooting

### "docker: command not found"

**Make sure Docker Desktop is running:**
1. Open Spotlight (Cmd+Space)
2. Type "Docker"
3. Press Enter
4. Wait for whale icon in menu bar

### "Permission denied" when running docker

**Add yourself to docker group:**
```bash
sudo dscl . append /Groups/docker GroupMembership $USER
```

Then log out and back in.

### Port conflicts (8000, 3010 in use)

**Find what's using the port:**
```bash
lsof -i :8000
```

**Kill the process:**
```bash
kill -9 <PID>
```

**Or use different ports:**
Edit `environments/dev.env`:
```bash
PORT_OFFSET=100
```

### Homebrew installation fails

**Update Command Line Tools:**
```bash
xcode-select --install
```

Then retry Homebrew installation.

---

## macOS-Specific Tips

### Use iTerm2 for Better Terminal

```bash
brew install --cask iterm2
```

iTerm2 has better features than default Terminal.

### Keyboard Shortcuts

- `Cmd+Space`: Open Spotlight (quick app launcher)
- `Cmd+Tab`: Switch between apps
- `Cmd+Shift+.`: Show hidden files in Finder

### Access Chronicle Files in Finder

```bash
open ~/chronicle
```

Opens the folder in Finder.

### VS Code Integration

```bash
brew install --cask visual-studio-code
cd ~/chronicle
code .
```

Opens Chronicle in VS Code.

---

## Performance Notes

### Apple Silicon (M1/M2/M3)

Docker Desktop has **excellent performance** on Apple Silicon:
- ✅ Native ARM support
- ✅ Fast container startup
- ✅ Low resource usage

### Intel Macs

Docker Desktop uses virtualization:
- Still good performance
- May use more RAM
- Consider closing other apps during heavy use

---

## Next Steps

1. **Configure mobile app** - Connect your phone or OMI device
2. **Test with audio** - Upload test audio file
3. **Explore settings** - Check Settings → Memory Provider
4. **Read documentation** - Check `CLAUDE.md`
5. **Set up Tailscale** - For remote access (if not done yet)

---

## Getting Help

- **GitHub Issues**: https://github.com/BasedHardware/Friend/issues
- **Docker for Mac**: https://docs.docker.com/desktop/mac/
- **Homebrew Docs**: https://docs.brew.sh/

---

## Summary

✅ **What you installed:**
- Homebrew (package manager)
- Docker Desktop for Mac
- Chronicle and dependencies
- (Optional) Tailscale

✅ **What you can do:**
- Access dashboard: http://localhost:3010
- Access API: http://localhost:8000
- Manage containers via Docker Desktop GUI
- Use native macOS tools

✅ **macOS advantages:**
- Native Unix environment (no WSL needed)
- Excellent Docker Desktop support
- Great performance (especially on Apple Silicon)
- Easy package management with Homebrew

**Total setup time: ~30-45 minutes**

Welcome to Chronicle on macOS! 🍎🚀
