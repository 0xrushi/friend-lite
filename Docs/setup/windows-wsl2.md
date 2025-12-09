# Chronicle Setup Guide - Windows with WSL2

**Complete installation guide for Windows using WSL2 (Windows Subsystem for Linux).**

This is the **recommended approach** for Windows users - it provides the best performance and compatibility.

---

## Why WSL2?

✅ **Best performance** - Docker runs natively in Linux kernel (no VM overhead)
✅ **Perfect compatibility** - All Chronicle bash scripts work exactly as intended
✅ **Native Docker** - Can use Docker Desktop or native Docker engine
✅ **Industry standard** - Most developers on Windows use WSL2
✅ **Future-proof** - Microsoft's recommended way to run Linux on Windows

---

## Prerequisites

Before starting, make sure you have:
- ✅ Read [Prerequisites Guide](prerequisites.md) and have your API keys ready
- ✅ **Windows 10 version 2004+** (Build 19041+) or **Windows 11**
- ✅ **Administrator access** to your computer
- ✅ **At least 20GB free disk space**
- ✅ **8GB RAM** (4GB minimum)

**Check your Windows version:**
1. Press `Win + R`
2. Type `winver` and press Enter
3. Check the version number

If your version is older than 2004, run Windows Update first.

---

## Installation Steps

### Step 1: Install WSL2 with Ubuntu

WSL2 gives you a real Linux environment inside Windows.

#### 1.1 Open PowerShell as Administrator

**Method 1:**
1. Click Start button
2. Type `powershell`
3. Right-click "Windows PowerShell"
4. Click "Run as administrator"
5. Click "Yes" when asked

**Method 2:**
1. Press `Win + X`
2. Click "Windows PowerShell (Admin)" or "Terminal (Admin)"

You should see a blue window with: `PS C:\Windows\system32>`

#### 1.2 Install WSL2 with Ubuntu

**Copy and paste this command:**

```powershell
wsl --install -d Ubuntu-22.04
```

Press `Enter`.

**What you'll see:**
```
Installing: Windows Subsystem for Linux
Installing: Ubuntu-22.04
The requested operation is successful. Changes will not be effective until the system is rebooted.
```

#### 1.3 Restart Your Computer

**You MUST restart** for WSL2 to work.

1. Close PowerShell
2. Save any open work
3. Restart Windows (Start → Power → Restart)

⏱️ **Time: 5 minutes**

---

### Step 2: Set Up Ubuntu

After restarting, Ubuntu will finish installing.

#### 2.1 Wait for Ubuntu Setup

1. A window titled "Ubuntu" will open automatically
2. You'll see: `Installing, this may take a few minutes...`
3. **Be patient** - this can take 5-10 minutes

#### 2.2 Create Your Ubuntu Username

When you see `Enter new UNIX username:`:

1. Type a username (lowercase, no spaces)
   - Example: `john` or `yourname`
   - ⚠️ This is NOT your Windows username
2. Press `Enter`

#### 2.3 Create Your Ubuntu Password

When you see `New password:`:

1. Type a password
   - **The cursor won't move** - this is normal Linux security!
   - Use something you'll remember
2. Press `Enter`
3. Type the same password again
4. Press `Enter`

**⚠️ Important**: Remember this password! You'll need it throughout setup.

#### 2.4 Verify Ubuntu is Working

You should now see:
```
yourname@DESKTOP-XXXXX:~$
```

This is your **terminal prompt** - you're now inside Linux!

**Test it:**
```bash
pwd
```

Press `Enter`. You should see:
```
/home/yourname
```

✅ **Ubuntu is installed and working!**

⏱️ **Time: 10 minutes**

---

### Step 3: Install Docker Desktop

Docker Desktop lets you run Chronicle's containers and automatically integrates with WSL2.

#### 3.1 Download Docker Desktop

1. Open your web browser (Edge, Chrome, Firefox)
2. Go to: https://www.docker.com/products/docker-desktop
3. Click "Download for Windows"
4. Wait for download (file is ~500MB)

#### 3.2 Install Docker Desktop

1. Open your Downloads folder
2. Double-click `Docker Desktop Installer.exe`
3. Click "Yes" when asked to allow changes
4. **Important checkboxes:**
   - ✅ "Use WSL 2 instead of Hyper-V" (should be checked by default)
   - ✅ "Add shortcut to desktop" (optional but helpful)
5. Click "OK"
6. Wait for installation (5-10 minutes)
7. When you see "Installation succeeded", click "Close and restart"

**Your computer will restart again.**

#### 3.3 Start Docker Desktop

After restart:

1. Docker Desktop should start automatically (whale icon in system tray)
2. If not: Start → type "Docker Desktop" → press Enter

**First-time setup:**
1. Accept "Docker Subscription Service Agreement" (free for personal use)
2. Skip tutorial or close welcome window

#### 3.4 Enable WSL2 Integration

**This step is CRITICAL:**

1. Click the ⚙️ gear icon (Settings) in Docker Desktop
2. Click "Resources" in left menu
3. Click "WSL Integration"
4. Enable:
   - ✅ "Enable integration with my default WSL distro"
   - ✅ Toggle for "Ubuntu-22.04" (turn ON/blue)
5. Click "Apply & Restart"
6. Wait for Docker to restart (~30 seconds)

#### 3.5 Verify Docker Works in WSL2

1. Open Ubuntu (Start → type "Ubuntu" → press Enter)
2. Type:
   ```bash
   docker --version
   ```
3. Press Enter

**You should see:**
```
Docker version 24.x.x, build xxxxxxx
```

**Also test Docker Compose:**
```bash
docker compose version
```

**You should see:**
```
Docker Compose version v2.x.x
```

✅ **Docker is working in WSL2!**

⏱️ **Time: 15 minutes**

---

### Step 4: Install Chronicle Dependencies

Now we'll install the tools Chronicle needs using an automated script.

#### 4.1 Open Ubuntu Terminal

1. Click Start
2. Type `ubuntu`
3. Press Enter

You should see: `yourname@DESKTOP-XXXXX:~$`

#### 4.2 Run the Dependency Installer

**Copy and paste this command:**

```bash
curl -fsSL https://raw.githubusercontent.com/BasedHardware/Friend/main/scripts/install-deps.sh | bash
```

Press `Enter`.

**You'll be asked for your Ubuntu password:**
- Type your password (cursor won't move - normal!)
- Press Enter

**What the script does:**
- Updates Ubuntu's package lists
- Installs git, make, curl, and other tools
- Detects you're in WSL2
- Asks about Docker installation

**Docker Installation Prompt:**

The script will detect WSL2 and ask:
```
Install Docker Engine in WSL? (y/N):
```

**Type `N` and press Enter** - you already installed Docker Desktop!

The script will show:
```
ℹ️  Skipping Docker installation
   Please install Docker Desktop for Windows, then:
   1. Open Docker Desktop Settings
   2. Go to Resources → WSL Integration
   3. Enable integration with Ubuntu
```

✅ You already did this in Step 3.4!

#### 4.3 Verify Installation

The script automatically verifies everything:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Dependency Installation Complete!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 Installed tools:

  ✅ Git:            2.34.1
  ✅ Make:           4.3
  ✅ curl:           7.81.0
  ✅ Docker:         24.0.5
  ✅ Docker Compose: v2.20.2

✅ Docker is running and accessible
```

⏱️ **Time: 3 minutes**

---

### Step 5: Install Tailscale (Optional but Recommended)

Tailscale lets you access Chronicle from anywhere - your phone, other computers, etc.

**Skip this if you only want local access** (same WiFi network only).

See: **[Tailscale Setup Guide](tailscale.md)** for detailed instructions.

**Quick install:**
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Follow the login prompts to connect your device.

⏱️ **Time: 5 minutes**

---

### Step 6: Install Chronicle

Now for the main installation!

#### 6.1 Clone Chronicle Repository

**In Ubuntu terminal:**

```bash
cd ~
git clone https://github.com/BasedHardware/Friend.git chronicle
cd chronicle
```

**What this does:**
- `cd ~` - Go to your home directory
- `git clone` - Download Chronicle code
- `cd chronicle` - Enter the Chronicle folder

You should now see:
```
yourname@DESKTOP-XXXXX:~/chronicle$
```

#### 6.2 Run the Setup Wizard

**Copy and paste:**

```bash
make wizard
```

Press `Enter`.

You'll see:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧙 Chronicle Setup Wizard
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Press `Enter` to continue.

#### 6.3 Configure Secrets

The wizard will ask you several questions. **Have your API keys ready from the [Prerequisites Guide](prerequisites.md).**

**Enter when prompted:**
- **JWT Secret Key**: Press Enter (auto-generates)
- **Admin Email**: Press Enter (use default) or type your email
- **Admin Password**: Type a secure password (cursor won't move - normal!)
- **OpenAI API Key**: Paste your key (from Prerequisites guide)
- **Deepgram API Key**: Paste your key (from Prerequisites guide)
- **Optional keys**: Press Enter to skip (Mistral, Hugging Face, etc.)

#### 6.4 Tailscale Configuration

```
Do you want to configure Tailscale? (y/N):
```

- If you installed Tailscale in Step 5: Type `y`
- If you skipped Tailscale: Type `N`

#### 6.5 Environment Setup

```
Environment name [dev]:
```
👉 Press Enter (use "dev")

```
Port offset [0]:
```
👉 Press Enter (use default ports)

```
MongoDB database name [chronicle-dev]:
```
👉 Press Enter

```
Mycelia database name [mycelia-dev]:
```
👉 Press Enter

**Optional services - type N for all (can enable later):**
```
Enable Mycelia? (y/N):
```
👉 Type `N`

```
Enable Speaker Recognition? (y/N):
```
👉 Type `N`

```
Enable OpenMemory MCP? (y/N):
```
👉 Type `N`

```
Enable Parakeet ASR? (y/N):
```
👉 Type `N`

#### 6.6 Wizard Complete

You should see:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Setup Complete!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 Next Steps:

  Start your environment:
    ./start-env.sh dev
```

⏱️ **Time: 5 minutes**

---

### Step 7: Start Chronicle

#### 7.1 Start the Services

**In Ubuntu terminal:**

```bash
./start-env.sh dev
```

Press `Enter`.

**What happens:**

1. Docker downloads container images (first time only - ~5 minutes)
2. Docker builds the Chronicle services
3. Services start in the background

**You'll see:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 Starting Chronicle: dev
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📦 Project:          chronicle-dev
🗄️  MongoDB Database: chronicle-dev
💾 Data Directory:   ./data/dev

🌐 Service URLs:
   Backend:          http://localhost:8000
   Web UI:           http://localhost:3010
   MongoDB:          mongodb://localhost:27017
...

[+] Building 123.4s (15/15) FINISHED
[+] Running 5/5
 ✔ Container chronicle-dev-mongo-1          Started
 ✔ Container chronicle-dev-redis-1          Started
 ✔ Container chronicle-dev-qdrant-1         Started
 ✔ Container chronicle-dev-friend-backend-1 Started
 ✔ Container chronicle-dev-webui-1          Started

✅ Services Started Successfully!
```

**First-time startup takes 5-10 minutes.** Subsequent starts are much faster (~30 seconds).

#### 7.2 Verify Services

**Open Docker Desktop:**
1. Click the whale icon in system tray
2. Click "Containers"
3. You should see 5 containers running with green status

⏱️ **Time: 10 minutes (first time)**

---

### Step 8: Access Chronicle

#### 8.1 Open the Web Dashboard

1. Open your web browser (Chrome, Edge, Firefox)
2. Go to: **http://localhost:3010**

You should see the Chronicle login page!

#### 8.2 Log In

**Enter your credentials:**
- Email: `admin@example.com` (or what you chose)
- Password: (your admin password from Step 6.3)

Click "Sign In"

🎉 **You're in!** Welcome to Chronicle!

#### 8.3 Explore

You should see:
- 📊 Dashboard with stats
- 💬 Conversations tab
- 🧠 Memories tab
- ⚙️ Settings

**Check the API docs:**
- Go to: **http://localhost:8000/docs**
- This shows all available API endpoints

⏱️ **Time: 2 minutes**

---

## Managing Chronicle

### Starting Chronicle (after stopping)

```bash
# Open Ubuntu terminal
cd ~/chronicle
./start-env.sh dev
```

### Stopping Chronicle

```bash
cd ~/chronicle
docker compose down
```

**Or use Docker Desktop:**
1. Open Docker Desktop
2. Click "Containers"
3. Click stop button next to `chronicle-dev`

### Viewing Logs

**In Docker Desktop:**
1. Click "Containers"
2. Click container name
3. Click "Logs" tab

**Or in terminal:**
```bash
cd ~/chronicle
docker compose logs -f
```

Press `Ctrl+C` to stop following logs.

### Restarting Services

```bash
cd ~/chronicle
docker compose restart
```

### Updating Chronicle

```bash
cd ~/chronicle
git pull
docker compose up -d --build
```

---

## Accessing WSL2 Files from Windows

Your Chronicle files live in Ubuntu (WSL2), but you can access them from Windows:

**In Windows File Explorer:**
1. Open File Explorer
2. Type in address bar: `\\wsl$\Ubuntu-22.04\home\yourname\chronicle`
3. Press Enter

You can now browse Chronicle files like normal Windows folders!

**Or access from Ubuntu:**
- Windows `C:\` drive is at: `/mnt/c/`
- Your Windows user folder: `/mnt/c/Users/YourWindowsUsername/`

---

## Common Issues

### "wsl --install" doesn't work

**Solution - Enable WSL manually:**
```powershell
# In PowerShell as Administrator
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# Restart computer, then:
wsl --set-default-version 2
wsl --install -d Ubuntu-22.04
```

### Docker Desktop says "WSL 2 installation is incomplete"

**Solution:**
1. Download WSL2 kernel update: https://aka.ms/wsl2kernel
2. Install it
3. Restart Docker Desktop

### "Cannot connect to Docker daemon"

**Solution:**
1. Make sure Docker Desktop is running (whale icon in system tray should be present)
2. In Docker Desktop Settings → Resources → WSL Integration
3. Enable "Ubuntu-22.04"
4. Click "Apply & Restart"

### Port 8000 or 3010 already in use

**Solution - Find and kill the process:**
```powershell
# In PowerShell as Administrator
netstat -ano | findstr :8000
taskkill /PID <PID_NUMBER> /F
```

**Or use different ports:**
Edit `environments/dev.env` and change `PORT_OFFSET=100`

### Ubuntu terminal closes immediately

**Solution - Reinstall Ubuntu:**
```powershell
# In PowerShell as Administrator
wsl --unregister Ubuntu-22.04
wsl --install -d Ubuntu-22.04
```
Then go through Ubuntu setup again.

### "Permission denied" errors

**Solution:**
```bash
# Make sure you own the chronicle folder
sudo chown -R $USER:$USER ~/chronicle
cd ~/chronicle
```

---

## Next Steps

Now that Chronicle is running:

1. **Connect a device** - Set up the mobile app or OMI device
2. **Configure settings** - Check Settings → Memory Provider
3. **Test audio upload** - Try uploading a test audio file
4. **Read the docs** - Check `CLAUDE.md` for comprehensive guide
5. **Explore the API** - Visit http://localhost:8000/docs

---

## Advanced Tips

### Using VS Code with WSL2

VS Code can edit files directly in WSL2:

1. Install "Remote - WSL" extension in VS Code
2. In Ubuntu terminal: `code ~/chronicle`
3. VS Code opens with WSL2 integration!

### Better Terminal

Install Windows Terminal for better experience:
1. Microsoft Store → search "Windows Terminal"
2. Install and set as default
3. Opens Ubuntu tabs easily

### Docker Desktop Alternatives

You can skip Docker Desktop and use native Docker in WSL2:
- Lighter weight (no GUI)
- Completely free (no licensing)
- Runs `./scripts/install-deps.sh` and choose "y" to install Docker Engine

---

## Getting Help

- **GitHub Issues**: https://github.com/BasedHardware/Friend/issues
- **WSL2 Docs**: https://docs.microsoft.com/en-us/windows/wsl/
- **Docker Docs**: https://docs.docker.com/desktop/windows/

---

## Summary

✅ **What you installed:**
- WSL2 with Ubuntu 22.04
- Docker Desktop with WSL2 backend
- Chronicle and all dependencies
- (Optional) Tailscale

✅ **What you can do:**
- Access dashboard: http://localhost:3010
- Access API: http://localhost:8000
- Manage containers via Docker Desktop GUI
- Edit files from Windows File Explorer
- Everything "just works" together!

**Your WSL2 setup gives you:**
- 🚀 Best performance (native Linux kernel)
- 🔧 Perfect compatibility (all scripts work)
- 🪟 Windows integration (GUI tools available)
- 💪 Professional dev environment

Welcome to Chronicle! 🎉
