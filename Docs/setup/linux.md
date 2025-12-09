# Chronicle Setup Guide - Linux

**Quick installation guide for Linux users (Ubuntu/Debian).**

Linux provides the best performance for Chronicle with native Docker support.

---

## Prerequisites

Before starting:
- ✅ Read [Prerequisites Guide](prerequisites.md) and have your API keys ready
- ✅ **Ubuntu 20.04+** or **Debian 11+** (or compatible distribution)
- ✅ **At least 20GB free disk space**
- ✅ **8GB RAM** (4GB minimum)
- ✅ **sudo access**

---

## Quick Install (TL;DR)

For experienced users:

```bash
# Install dependencies
curl -fsSL https://raw.githubusercontent.com/BasedHardware/Friend/main/scripts/install-deps.sh | bash

# Log out and back in (for docker group)
# Or run: newgrp docker

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

### Step 1: Install Dependencies Automatically

We provide a script that installs everything:

```bash
curl -fsSL https://raw.githubusercontent.com/BasedHardware/Friend/main/scripts/install-deps.sh | bash
```

**You'll be asked for your sudo password.**

**What this installs:**
- Git (version control)
- Make (build automation)
- curl, wget (download tools)
- Docker Engine (container runtime)
- Docker Compose (multi-container orchestration)

**Docker installation:**

The script will:
1. Add Docker's official GPG key
2. Set up Docker repository
3. Install Docker Engine and Docker Compose
4. Add you to the `docker` group
5. Start Docker service

**After installation:**

```
⚠️  IMPORTANT: You need to log out and log back in for group changes to take effect
   Or run: newgrp docker
```

**Option 1 (Recommended): Log out and back in**
- Click user menu → Log Out
- Log back in
- Your user now has docker permissions

**Option 2: Use newgrp (temporary)**
```bash
newgrp docker
```
- Only affects current terminal session
- Need to run in every new terminal

**Verify installation:**
```bash
git --version
make --version
docker --version
docker compose version
docker ps  # Should work without sudo
```

⏱️ **Time: 5 minutes**

---

### Step 2: Install Tailscale (Optional but Recommended)

Tailscale enables remote access from your phone or anywhere.

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Follow login prompts in your browser.

**Detailed instructions**: See [Tailscale Setup Guide](tailscale.md)

⏱️ **Time: 5 minutes**

---

### Step 3: Install Chronicle

#### 3.1 Clone the Repository

```bash
cd ~
git clone https://github.com/BasedHardware/Friend.git chronicle
cd chronicle
```

#### 3.2 Run Setup Wizard

```bash
make wizard
```

The wizard will guide you through configuration. **Have your API keys ready from the [Prerequisites Guide](prerequisites.md).**

**Secrets:**
- JWT secret: Press Enter (auto-generates)
- Admin email: Press Enter or type your email
- Admin password: Type a secure password
- OpenAI API key: Paste your key
- Deepgram API key: Paste your key
- Optional keys: Press Enter to skip

**Tailscale (if installed):**
- Configure Tailscale?: `y` if you installed in Step 2
- SSL option: Choose `1` for automatic HTTPS

**Environment:**
- Environment name: Press Enter (use "dev")
- Port offset: Press Enter
- Database names: Press Enter for defaults
- Optional services: `N` for all (enable later if needed)

⏱️ **Time: 5 minutes**

---

### Step 4: Start Chronicle

```bash
./start-env.sh dev
```

**First-time startup:**
- Downloads Docker images (~2GB, takes 5-10 minutes)
- Builds Chronicle services
- Starts 5 containers

**You'll see:**
```
✅ Services Started Successfully!

🌐 Access Your Services:

   📱 Web Dashboard:     http://localhost:3010
   🔌 Backend API:       http://localhost:8000
   📚 API Docs:          http://localhost:8000/docs
```

**Verify services are running:**
```bash
docker ps
```

Should show 5 containers in "Up" status.

⏱️ **Time: 10 minutes (first time)**

---

### Step 5: Access Chronicle

1. Open browser: **http://localhost:3010**
2. Log in with your admin credentials
3. Start using Chronicle!

**Check API docs:**
- http://localhost:8000/docs

🎉 **Installation complete!**

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
docker compose logs -f  # Press Ctrl+C to exit
```

### Check Status

```bash
# Service status
docker compose ps

# System resources
docker stats

# Disk usage
docker system df
```

### Update Chronicle

```bash
cd ~/chronicle
git pull
docker compose up -d --build
```

---

## Troubleshooting

### "Permission denied" when running docker

**You need to log out and back in** after installation.

Or temporarily:
```bash
newgrp docker
```

Or check if you're in docker group:
```bash
groups | grep docker
```

### "Cannot connect to Docker daemon"

**Start Docker service:**
```bash
sudo systemctl start docker
sudo systemctl enable docker  # Start on boot
```

**Check status:**
```bash
sudo systemctl status docker
```

### Port conflicts (8000, 3010 in use)

**Find process using port:**
```bash
sudo lsof -i :8000
sudo lsof -i :3010
```

**Kill process:**
```bash
sudo kill -9 <PID>
```

**Or use different ports:**
Edit `environments/dev.env`:
```bash
PORT_OFFSET=100
```

### Docker installation failed

**Manual installation:**
```bash
# Remove any old versions
sudo apt-get remove docker docker-engine docker.io containerd runc

# Install dependencies
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release

# Add Docker GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker
```

Then log out and back in.

---

## Distribution-Specific Notes

### Ubuntu 22.04 LTS (Recommended)

Works perfectly out of the box. This is our primary test platform.

### Ubuntu 20.04 LTS

Fully supported. May need to update Docker Compose:
```bash
sudo apt-get update
sudo apt-get install docker-compose-plugin
```

### Debian 11/12

Fully supported. Use the install script or follow manual installation.

### Fedora/RHEL/CentOS

**Install script:**
```bash
curl -fsSL https://raw.githubusercontent.com/BasedHardware/Friend/main/scripts/install-deps.sh | bash
```

**Or manual:**
```bash
sudo dnf install -y git make docker docker-compose
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

### Arch Linux

```bash
sudo pacman -S git make docker docker-compose
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

---

## Performance Optimization

### Increase Docker Performance

**Use overlay2 storage driver** (default on modern systems):
```bash
docker info | grep "Storage Driver"
```

Should show `overlay2`.

**Limit Docker log size** (prevents disk filling):
```bash
sudo nano /etc/docker/daemon.json
```

Add:
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

Restart Docker:
```bash
sudo systemctl restart docker
```

### System Resources

**Check available resources:**
```bash
# RAM
free -h

# Disk space
df -h

# CPU
nproc
```

**Recommended for Chronicle:**
- 8GB RAM (4GB minimum)
- 4 CPU cores (2 minimum)
- 20GB disk space

---

## Security Notes

### Firewall Configuration

If you have a firewall enabled:

```bash
# Allow Chronicle ports (local access only)
sudo ufw allow from 127.0.0.1 to any port 8000
sudo ufw allow from 127.0.0.1 to any port 3010

# For Tailscale remote access, no firewall rules needed
# Tailscale handles secure connections
```

### Keep System Updated

```bash
# Update system packages
sudo apt-get update
sudo apt-get upgrade

# Update Docker
sudo apt-get upgrade docker-ce docker-ce-cli containerd.io
```

---

## Advanced Tips

### Run Chronicle on Boot

**Create systemd service:**
```bash
sudo nano /etc/systemd/system/chronicle.service
```

Add:
```ini
[Unit]
Description=Chronicle
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/yourusername/chronicle
ExecStart=/home/yourusername/chronicle/start-env.sh dev
ExecStop=/usr/bin/docker compose down
User=yourusername

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable chronicle
sudo systemctl start chronicle
```

### Monitor Resource Usage

```bash
# Real-time container stats
docker stats

# System monitoring
htop  # Install with: sudo apt-get install htop

# Disk usage by container
docker system df -v
```

### Remote Server Setup

If running on a VPS/cloud server:

1. **Install Tailscale** for secure access (recommended)
2. **Or configure firewall** for specific IP access:
   ```bash
   sudo ufw allow from YOUR_IP to any port 8000
   sudo ufw allow from YOUR_IP to any port 3010
   ```
3. **Use HTTPS** (Tailscale provides this automatically)

---

## Next Steps

1. **Configure mobile app** - Connect your phone/OMI device
2. **Test audio upload** - Try uploading test audio
3. **Explore API** - Visit http://localhost:8000/docs
4. **Read documentation** - Check `CLAUDE.md`
5. **Set up Tailscale** - For remote access (if not done)

---

## Getting Help

- **GitHub Issues**: https://github.com/BasedHardware/Friend/issues
- **Docker Docs**: https://docs.docker.com/engine/install/
- **Ubuntu Help**: https://help.ubuntu.com/

---

## Summary

✅ **What you installed:**
- Docker Engine (native, no Desktop needed)
- Docker Compose plugin
- Chronicle and all dependencies
- (Optional) Tailscale

✅ **Linux advantages:**
- **Best performance** - Native Docker, no virtualization
- **Lightest weight** - No GUI overhead
- **Most stable** - Industry-standard deployment platform
- **Free forever** - No licensing concerns
- **Server-ready** - Perfect for VPS/cloud deployment

✅ **What you can do:**
- Access dashboard: http://localhost:3010
- Access API: http://localhost:8000
- Run as system service (auto-start on boot)
- Deploy to production servers

**Total setup time: ~20-30 minutes**

Welcome to Chronicle on Linux! 🐧🚀
