# Chronicle Setup Guide - Windows with Git Bash

**Installation guide for Windows using Git Bash (no WSL2 required).**

This approach is **simpler** but has **some limitations** compared to WSL2. Good for quick testing or if WSL2 isn't available.

---

## When to Use Git Bash vs WSL2

### Use Git Bash if:
✅ You want the **easiest, fastest setup**
✅ You're just **testing** Chronicle
✅ WSL2 is **blocked** by IT policy
✅ You prefer **Windows-native** tools
✅ You want **minimal** learning curve

### Use WSL2 if:
🚀 You're a **developer** or power user
🚀 You want **best performance**
🚀 You need **100% script compatibility**
🚀 You plan to use Chronicle **long-term**

**For WSL2 setup**, see: [Windows with WSL2 Guide](windows-wsl2.md)

---

## Prerequisites

Before starting, make sure you have:
- ✅ Read [Prerequisites Guide](prerequisites.md) and have your API keys ready
- ✅ **Windows 10** or **Windows 11**
- ✅ **Administrator access** to your computer
- ✅ **At least 20GB free disk space**
- ✅ **8GB RAM** (4GB minimum)

---

## Installation Steps

### Step 1: Install Git for Windows

Git for Windows includes Git Bash - a bash shell for Windows.

#### 1.1 Download Git for Windows

1. Open your web browser
2. Go to: https://git-scm.com/download/win
3. Download should start automatically (~50MB)
4. Wait for download to complete

#### 1.2 Install Git for Windows

1. Open Downloads folder
2. Double-click `Git-<version>-64-bit.exe`
3. Click "Yes" when asked to allow changes

**Installation wizard settings:**

**Select Components:**
- ✅ Windows Explorer integration
- ✅ Git Bash Here
- ✅ Git GUI Here
- ✅ Associate .git* configuration files
- ✅ Associate .sh files to be run with Bash

**Adjusting PATH:**
- Select: **"Git from the command line and also from 3rd-party software"** (recommended)

**SSH executable:**
- Select: **"Use bundled OpenSSH"**

**HTTPS backend:**
- Select: **"Use the OpenSSL library"**

**Line ending conversions:**
- ⚠️ **IMPORTANT**: Select **"Checkout as-is, commit as-is"**
  - This prevents line ending issues with bash scripts

**Terminal emulator:**
- Select: **"Use MinTTY"** (better terminal)

**Default branch name:**
- Select: **"Let Git decide"** or "main"

**Other settings:**
- Keep all other defaults

Click "Install" and wait (~2 minutes).

Click "Finish" when done.

✅ **Git Bash is installed!**

⏱️ **Time: 5 minutes**

---

### Step 2: Install Docker Desktop

Docker Desktop runs Chronicle's containers.

#### 2.1 Download Docker Desktop

1. Go to: https://www.docker.com/products/docker-desktop
2. Click "Download for Windows"
3. Wait for download (~500MB)

#### 2.2 Install Docker Desktop

1. Open Downloads folder
2. Double-click `Docker Desktop Installer.exe`
3. Click "Yes" when asked to allow changes

**Important settings:**
- The installer will detect if WSL2 is available
- If prompted, choose: **"Use Hyper-V"** (not WSL2, since we're not using WSL2)
- ✅ "Add shortcut to desktop" (optional)

Click "OK" to install (5-10 minutes).

When finished: Click "Close and restart"

**Your computer will restart.**

#### 2.3 Start Docker Desktop

After restart:

1. Docker Desktop should start automatically (whale icon in system tray)
2. If not: Start → type "Docker Desktop" → press Enter

**First-time setup:**
1. Accept "Docker Subscription Service Agreement" (free for personal use)
2. Skip tutorial or close welcome window

#### 2.4 Wait for Docker to Start

Look at the Docker Desktop icon in system tray:
- 🟢 **Solid whale** = Docker is running (good!)
- 🟠 **Animated whale** = Docker is starting (wait)
- 🔴 **Whale with X** = Docker has a problem (see troubleshooting)

**Wait until the whale icon is solid** (can take 2-3 minutes first time).

#### 2.5 Verify Docker Works

1. Right-click Start button
2. Click "Windows PowerShell" (or "Terminal")
3. Type:
   ```powershell
   docker --version
   ```
4. Press Enter

**You should see:**
```
Docker version 24.x.x, build xxxxxxx
```

✅ **Docker is working!**

⏱️ **Time: 15 minutes**

---

### Step 3: Install Chronicle Dependencies

Git for Windows includes most tools we need, but let's verify.

#### 3.1 Open Git Bash

**Method 1:**
1. Click Start
2. Type "git bash"
3. Press Enter

**Method 2:**
1. Right-click on Desktop or in any folder
2. Click "Git Bash Here"

You should see a terminal window with:
```
yourname@DESKTOP-XXXXX MINGW64 ~
$
```

#### 3.2 Verify Tools

**Test each tool:**

```bash
git --version
```
Should show: `git version 2.x.x`

```bash
make --version
```
Should show: `GNU Make 4.x` or error (we'll fix if missing)

```bash
docker --version
```
Should show: `Docker version 24.x.x`

```bash
docker compose version
```
Should show: `Docker Compose version v2.x.x`

#### 3.3 Install Make (if missing)

If `make --version` gave an error, install it:

**In Git Bash:**
```bash
# Download and install make
curl -L https://github.com/mstorsjo/llvm-mingw/releases/download/20231128/llvm-mingw-20231128-ucrt-x86_64.zip -o /tmp/mingw.zip
unzip /tmp/mingw.zip -d /tmp/
cp /tmp/llvm-mingw*/bin/mingw32-make.exe /usr/bin/make.exe
```

Then verify:
```bash
make --version
```

✅ **All tools verified!**

⏱️ **Time: 5 minutes**

---

### Step 4: Install Tailscale (Optional but Recommended)

Tailscale lets you access Chronicle remotely from your phone or other devices.

**Skip this if you only want local access.**

#### 4.1 Download Tailscale for Windows

1. Go to: https://tailscale.com/download/windows
2. Click "Download Tailscale for Windows"
3. Wait for download (~20MB)

#### 4.2 Install Tailscale

1. Open Downloads folder
2. Double-click `tailscale-setup-<version>.exe`
3. Click "Yes" when asked
4. Click "Install"
5. Wait for installation (~1 minute)
6. Click "Finish"

#### 4.3 Connect to Tailscale

1. Tailscale icon appears in system tray (near clock)
2. Click the Tailscale icon
3. Click "Log in"
4. Browser opens - log in with:
   - Google account
   - Microsoft account
   - Email (create new account)
5. After logging in, close browser
6. Tailscale icon should turn green ✅

#### 4.4 Get Your Tailscale Hostname

1. Click Tailscale icon in system tray
2. Your hostname is shown (e.g., `my-computer.tail12345.ts.net`)
3. **Write this down** - you'll need it in setup

For detailed instructions, see: **[Tailscale Setup Guide](tailscale.md)**

⏱️ **Time: 5 minutes**

---

### Step 5: Install Chronicle

Now for the main installation!

#### 5.1 Choose Installation Directory

**In Git Bash, decide where to install:**

**Option A: In your home directory (recommended)**
```bash
cd ~
```

**Option B: In a specific folder**
```bash
cd /c/Users/YourUsername/Projects
```

**⚠️ Important**: Avoid paths with spaces!
- ✅ Good: `/c/Users/John/code`
- ❌ Bad: `/c/Users/John Smith/My Projects`

#### 5.2 Clone Chronicle Repository

```bash
git clone https://github.com/BasedHardware/Friend.git chronicle
cd chronicle
```

**What this does:**
- Downloads Chronicle code
- Creates `chronicle` folder
- Enters the folder

You should see:
```
yourname@DESKTOP-XXXXX MINGW64 ~/chronicle (main)
$
```

#### 5.3 Run the Setup Wizard

```bash
make wizard
```

Press `Enter`.

**You'll see:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧙 Chronicle Setup Wizard
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Press `Enter` to continue.

#### 5.4 Configure Secrets

The wizard asks several questions. **Have your API keys ready from the [Prerequisites Guide](prerequisites.md).**

**Enter when prompted:**
- **JWT Secret Key**: Press Enter (auto-generates)
- **Admin Email**: Press Enter (use default) or type your email
- **Admin Password**: Type a secure password
- **OpenAI API Key**: Paste your key (Right-click or Shift+Insert to paste in Git Bash)
- **Deepgram API Key**: Paste your key
- **Optional keys**: Press Enter to skip (Mistral, Hugging Face, etc.)

#### 5.5 Tailscale Configuration

```
Do you want to configure Tailscale? (y/N):
```

- If you installed Tailscale in Step 4: Type `y`
- If you skipped Tailscale: Type `N`

**If you said yes:**
```
Tailscale hostname [auto-detected]:
```
👉 Press Enter (should auto-detect)

**SSL Options:**
```
1) Use 'tailscale serve' (automatic HTTPS, recommended)
2) Generate self-signed certificates
3) Skip SSL setup

Choose option (1-3) [1]:
```
👉 Type `1` and press Enter

#### 5.6 Environment Setup

```
Environment name [dev]:
```
👉 Press Enter

```
Port offset [0]:
```
👉 Press Enter

```
MongoDB database name [chronicle-dev]:
```
👉 Press Enter

```
Mycelia database name [mycelia-dev]:
```
👉 Press Enter

**Optional services - type N for all:**
- Enable Mycelia?: `N`
- Enable Speaker Recognition?: `N`
- Enable OpenMemory MCP?: `N`
- Enable Parakeet ASR?: `N`

#### 5.7 Wizard Complete

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

### Step 6: Start Chronicle

#### 6.1 Start the Services

**In Git Bash:**

```bash
./start-env.sh dev
```

Press `Enter`.

**What happens:**

1. Docker downloads images (first time - ~5 minutes)
2. Docker builds services
3. Services start

**You'll see:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 Starting Chronicle: dev
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[+] Building 123.4s (15/15) FINISHED
[+] Running 5/5
 ✔ Container chronicle-dev-mongo-1          Started
 ✔ Container chronicle-dev-redis-1          Started
 ✔ Container chronicle-dev-qdrant-1         Started
 ✔ Container chronicle-dev-friend-backend-1 Started
 ✔ Container chronicle-dev-webui-1          Started

✅ Services Started Successfully!
```

**First-time startup: 5-10 minutes**
**Subsequent starts: ~30 seconds**

#### 6.2 Verify in Docker Desktop

1. Open Docker Desktop
2. Click "Containers"
3. You should see 5 containers with green "Running" status

⏱️ **Time: 10 minutes (first time)**

---

### Step 7: Access Chronicle

#### 7.1 Open the Web Dashboard

1. Open your web browser
2. Go to: **http://localhost:3010**

You should see the Chronicle login page!

#### 7.2 Log In

**Enter your credentials:**
- Email: `admin@example.com` (or what you chose)
- Password: (your admin password)

Click "Sign In"

🎉 **You're in!** Welcome to Chronicle!

#### 7.3 Explore

You should see:
- 📊 Dashboard
- 💬 Conversations
- 🧠 Memories
- ⚙️ Settings

**Check API docs:**
- Go to: **http://localhost:8000/docs**

⏱️ **Time: 2 minutes**

---

## Managing Chronicle

### Starting Chronicle (after stopping)

```bash
# In Git Bash
cd ~/chronicle  # or wherever you installed
./start-env.sh dev
```

### Stopping Chronicle

```bash
cd ~/chronicle
docker compose down
```

**Or use Docker Desktop:**
1. Click "Containers"
2. Click stop button

### Viewing Logs

**In Docker Desktop:**
1. Click "Containers"
2. Click container name
3. Click "Logs"

**Or in Git Bash:**
```bash
cd ~/chronicle
docker compose logs -f
```

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

## Limitations of Git Bash Setup

### Known Issues

❌ **Some bash scripts may not work perfectly**
- Git Bash is not full Linux
- Some Unix tools are limited or missing
- Path conversions can cause issues

❌ **Performance slightly slower**
- Docker Desktop uses Hyper-V virtualization
- Not as fast as native Linux (WSL2)

❌ **File permissions can be tricky**
- Windows vs Linux file permissions differ
- May see warnings about file modes

### Workarounds

**Script doesn't work?**
Try running in PowerShell or modify for Windows:
```powershell
# PowerShell equivalent commands often available
```

**Path issues?**
Use forward slashes: `/c/Users/...` not `C:\Users\...`

**Line ending errors?**
Configure Git:
```bash
git config --global core.autocrlf false
```

---

## When to Switch to WSL2

Consider switching to [WSL2 setup](windows-wsl2.md) if:
- 🚀 You use Chronicle **regularly**
- 🐛 You encounter **script compatibility issues**
- ⚡ You want **better performance**
- 👨‍💻 You're doing **development** work

Switching is easy - your API keys and settings can be reused!

---

## Common Issues

### "docker: command not found"

**Solution:**
1. Make sure Docker Desktop is running
2. Restart Git Bash
3. Verify: `docker --version`

### "Permission denied" when starting services

**Solution - Run Git Bash as Administrator:**
1. Right-click "Git Bash"
2. Click "Run as administrator"

### Port conflicts (8000, 3010 in use)

**Solution - Use different ports:**
Edit `environments/dev.env`:
```bash
PORT_OFFSET=100
```

### Scripts fail with "bad interpreter"

**Solution - Check line endings:**
```bash
cd ~/chronicle
git config core.autocrlf false
git checkout -- .
```

### "make: command not found"

**Solution - Install make:**
Follow Step 3.3 above to install make manually.

---

## Next Steps

Now that Chronicle is running:

1. **Connect a device** - Set up mobile app or OMI device
2. **Configure settings** - Check Settings → Memory Provider
3. **Test with audio** - Upload a test audio file
4. **Read docs** - Check `CLAUDE.md` for full guide
5. **Explore API** - Visit http://localhost:8000/docs

---

## Advanced Tips

### Better Terminal

**Windows Terminal** is better than Git Bash:
1. Microsoft Store → "Windows Terminal"
2. Install it
3. Open new "Git Bash" tab

### IDE Integration

**VS Code works great with Git Bash:**
1. Install VS Code
2. Open folder: `File → Open Folder → chronicle`
3. Terminal automatically uses Git Bash

### PATH Configuration

Add Git Bash tools to Windows PATH for PowerShell access:
1. Start → "Environment Variables"
2. Edit PATH
3. Add: `C:\Program Files\Git\usr\bin`

---

## Getting Help

- **GitHub Issues**: https://github.com/BasedHardware/Friend/issues
- **Git Bash Docs**: https://git-scm.com/doc
- **Docker Docs**: https://docs.docker.com/desktop/windows/

---

## Summary

✅ **What you installed:**
- Git for Windows (includes Git Bash)
- Docker Desktop for Windows
- Chronicle and all dependencies
- (Optional) Tailscale

✅ **What you can do:**
- Access dashboard: http://localhost:3010
- Access API: http://localhost:8000
- Manage containers via Docker Desktop GUI
- Use Windows tools natively

✅ **Trade-offs:**
- ✅ Easiest setup
- ✅ Windows-native experience
- ⚠️ Some script compatibility limitations
- ⚠️ Slightly slower performance than WSL2

**This setup is perfect for:**
- 🧪 Testing Chronicle
- 📱 Quick installations
- 🪟 Windows-native workflows

**Consider upgrading to [WSL2](windows-wsl2.md) for:**
- 🚀 Best performance
- 💯 Full compatibility
- 👨‍💻 Serious development work

Welcome to Chronicle! 🎉
