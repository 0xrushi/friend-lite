# Tailscale Setup for Chronicle

**Complete guide to setting up Tailscale for remote access to Chronicle.**

Tailscale creates a secure private network so you can access Chronicle from anywhere - your phone, other computers, even when away from home.

---

## What is Tailscale?

**Tailscale** is a zero-config VPN that creates a secure network between your devices.

### Why Use Tailscale with Chronicle?

✅ **Access from anywhere** - Use Chronicle from your phone when away from home
✅ **No port forwarding** - No need to open firewall ports or configure your router
✅ **Automatic HTTPS** - Built-in SSL certificates with `tailscale serve`
✅ **Zero configuration** - Works automatically once installed
✅ **Free for personal use** - Up to 100 devices
✅ **Secure** - End-to-end encrypted connections

### How It Works

```
Your Phone (anywhere)
        ↓
   Tailscale Network (secure tunnel)
        ↓
Your Home Computer (Chronicle)
```

Instead of `http://localhost:3010`, you access:
`https://your-computer.tail12345.ts.net`

---

## ⚠️ Important: You Need Tailscale on BOTH Devices

To access Chronicle remotely, you must install Tailscale on:

1. **Your Computer** - Where Chronicle is running (Step 2)
2. **Your Phone/Tablet** - The device you'll use to access Chronicle remotely (Step 5)

Both devices must be connected to the same Tailscale account to communicate securely.

---

## Prerequisites

- ✅ Chronicle installed (or in process of installing)
- ✅ Internet connection
- ✅ A phone/tablet to access Chronicle from (iPhone, iPad, or Android)
- ✅ Your computer where Chronicle runs

---

## Quick Setup Overview

**Here's what you'll do:**

1. ✅ Create ONE Tailscale account
2. ✅ Install Tailscale on your **computer** (where Chronicle runs)
3. ✅ Install Tailscale on your **phone/tablet** (to access Chronicle remotely)
4. ✅ Connect both devices to your Tailscale account
5. ✅ Configure Chronicle to use Tailscale
6. ✅ Test access from your phone

**Total time:** ~20 minutes

---

## Step 1: Create Tailscale Account

### 1.1 Sign Up

1. Go to: https://login.tailscale.com/start
2. Choose sign-up method:
   - **Google** account (easiest)
   - **Microsoft** account
   - **GitHub** account
   - **Email** (create new Tailscale account)
3. Complete sign-up process

✅ **Account created!**

---

## Step 2: Install on Your Computer

Choose your operating system:

### For Windows (WSL2 or Native)

**If using WSL2 (recommended):**

Open Ubuntu terminal and run:
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

**If using native Windows:**

1. Download: https://tailscale.com/download/windows
2. Run `tailscale-setup-<version>.exe`
3. Click "Install"
4. Log in when prompted

### For macOS

**Option 1: Graphical installer (recommended)**
1. Download: https://tailscale.com/download/mac
2. Open `Tailscale-<version>.pkg`
3. Click through installer
4. Launch Tailscale from Applications
5. Click "Log in" in menu bar

**Option 2: Homebrew**
```bash
brew install tailscale
sudo brew services start tailscale
sudo tailscale up
```

### For Linux

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

**Or for specific distros:**

**Ubuntu/Debian:**
```bash
curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/jammy.noarmor.gpg | sudo tee /usr/share/keyrings/tailscale-archive-keyring.gpg >/dev/null
curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/jammy.tailscale-keyring.list | sudo tee /etc/apt/sources.list.d/tailscale.list
sudo apt-get update
sudo apt-get install tailscale
sudo tailscale up
```

**Fedora/RHEL:**
```bash
sudo dnf config-manager --add-repo https://pkgs.tailscale.com/stable/fedora/tailscale.repo
sudo dnf install tailscale
sudo systemctl enable --now tailscaled
sudo tailscale up
```

---

## Step 3: Connect Your Computer

### 3.1 Start Tailscale

When you run `sudo tailscale up`, you'll see:

```
To authenticate, visit:

  https://login.tailscale.com/a/1234567890

```

### 3.2 Authenticate

1. **Copy the URL** shown in terminal
2. **Paste in your browser**
3. **Log in** with the account you created in Step 1
4. **Click "Connect"** or "Authorize"

You should see:
```
Success.
```

### 3.3 Verify Connection

**Check status:**
```bash
tailscale status
```

You should see:
```
# Tailscale status:
my-computer   100.x.x.x    my-computer.tail12345.ts.net
```

✅ **Your computer is now on Tailscale!**

---

## Step 4: Get Your Tailscale Hostname

You'll need this for Chronicle configuration.

### 4.1 Find Your Hostname

**Method 1: Command line**
```bash
tailscale status --json | grep DNSName
```

**Method 2: Web dashboard**
1. Go to: https://login.tailscale.com/admin/machines
2. Find your computer in the list
3. The hostname is shown (e.g., `my-computer.tail12345.ts.net`)

**Method 3: Simple command**
```bash
tailscale status | head -1 | awk '{print $3}'
```

**Example hostnames:**
- `laptop.tail12345.ts.net`
- `desktop-pc.tail67890.ts.net`
- `my-server.tailabcde.ts.net`

**Write this down!** You'll need it for Chronicle setup.

---

## Step 5: Install Tailscale on Your Phone/Tablet

**⚠️ REQUIRED: You must install Tailscale on your phone/tablet to access Chronicle remotely.**

Without Tailscale on your mobile device, you won't be able to connect to Chronicle when away from home.

### For iPhone/iPad

1. **Open App Store**
2. **Search "Tailscale"**
3. **Install** the Tailscale app (free)
4. **Open** the app
5. **Tap "Log in"**
6. **Log in with the SAME account** you used in Step 1 (very important!)
7. ✅ Your device is now connected!

**App Store link**: https://apps.apple.com/app/tailscale/id1470499037

### For Android

1. **Open Google Play Store**
2. **Search "Tailscale"**
3. **Install** the Tailscale app (free)
4. **Open** the app
5. **Tap "Sign in"**
6. **Log in with the SAME account** you used in Step 1 (very important!)
7. ✅ Your device is now connected!

**Play Store link**: https://play.google.com/store/apps/details?id=com.tailscale.ipn

### ✅ Verify Both Devices Are Connected

**On your phone's Tailscale app:**
1. You should see **your computer listed** (e.g., "my-laptop")
2. It should show as **"connected"** with a **green dot** ✅

**On your computer:**
```bash
tailscale status
```
You should see **your phone listed** in the output.

**Both devices must be connected for remote access to work!**

---

## Step 6: Configure Chronicle for Tailscale

Now we need to tell Chronicle about your Tailscale hostname.

### Option A: During Initial Setup (Recommended)

When running `make wizard`, you'll be asked:

```
Do you want to configure Tailscale? (y/N):
```

Type `y` and press Enter.

```
Tailscale hostname [auto-detected-hostname]:
```

It should auto-detect. Press Enter to accept, or type your hostname.

```
How do you want to handle HTTPS?
  1) Use 'tailscale serve' (automatic HTTPS, recommended)
  2) Generate self-signed certificates
  3) Skip SSL setup

Choose option (1-3) [1]:
```

Type `1` for automatic HTTPS (recommended).

### Option B: After Installation

If you already installed Chronicle, you can add Tailscale configuration:

**Edit your environment file:**
```bash
nano environments/dev.env
```

**Add these lines:**
```bash
TAILSCALE_HOSTNAME=your-computer.tail12345.ts.net
HTTPS_ENABLED=true
```

**Save and restart:**
```bash
./start-env.sh dev
```

---

## Step 7: Set Up `tailscale serve` (HTTPS)

Tailscale can automatically provide HTTPS for your Chronicle instance.

### 7.1 Expose Chronicle Backend

After Chronicle is running, run:

```bash
sudo tailscale serve https / http://localhost:8000
```

This maps:
- `https://your-computer.tail12345.ts.net/` → `http://localhost:8000`

### 7.2 Expose Chronicle Web UI

For the web dashboard:

```bash
sudo tailscale serve --bg https:443 / http://localhost:3010
```

Or use a different port for frontend:

```bash
sudo tailscale serve https:8443 / http://localhost:3010
```

### 7.3 Check What's Served

```bash
tailscale serve status
```

You should see:
```
https://your-computer.tail12345.ts.net (tailnet only)
|-- / proxy http://127.0.0.1:8000
```

---

## Step 8: Test Remote Access

### 8.1 Test from Your Phone

1. Make sure Tailscale app is running on phone
2. Make sure you're connected (green status)
3. Open web browser on phone
4. Go to: `https://your-computer.tail12345.ts.net`

You should see Chronicle dashboard! 🎉

### 8.2 Test API Access

From your phone browser, try:
`https://your-computer.tail12345.ts.net/health`

You should see:
```json
{"status": "healthy"}
```

---

## Managing Tailscale

### Check Connection Status

```bash
tailscale status
```

Shows all connected devices.

### Disconnect

```bash
sudo tailscale down
```

### Reconnect

```bash
sudo tailscale up
```

### View Logs

```bash
tailscale status --json
```

### Remove Device

1. Go to: https://login.tailscale.com/admin/machines
2. Click device name
3. Click "..." menu
4. Click "Remove device"

---

## Security Best Practices

### 1. Enable Key Expiry

By default, device keys don't expire. Enable expiry for better security:

1. Go to: https://login.tailscale.com/admin/settings/keys
2. Set "Key expiry" to 90 or 180 days
3. You'll need to re-authenticate periodically

### 2. Use Tailscale ACLs

Control which devices can access which services:

1. Go to: https://login.tailscale.com/admin/acls
2. Edit policy to restrict access
3. Example: Only allow your phone to access Chronicle

```json
{
  "acls": [
    {
      "action": "accept",
      "src": ["tag:phone"],
      "dst": ["tag:server:8000,3010"]
    }
  ]
}
```

### 3. Don't Share Your Hostname Publicly

Your Tailscale hostname is private - only devices on your Tailnet can access it.

❌ **Don't**: Post your `.ts.net` hostname on social media
✅ **Do**: Share it only with trusted devices you own

### 4. Keep Tailscale Updated

```bash
# Update on Linux
sudo apt-get update && sudo apt-get upgrade tailscale

# Update on macOS
brew upgrade tailscale

# Windows/Mobile: Update from app store
```

---

## Troubleshooting

### Can't connect from phone

**Most common issue:** Not logged into the same Tailscale account on both devices!

**Check Tailscale status on both devices:**

**On your computer:**
```bash
tailscale status
# Should show your phone in the list
```

**On your phone:**
- Open Tailscale app
- Check for green "Connected" status
- Verify it shows your computer in the device list

**If devices don't see each other:**
1. Make sure BOTH devices are logged into the **SAME** Tailscale account
2. Check that Tailscale is actually running on both devices
3. Try logging out and back in on both devices
4. Wait 30 seconds for devices to discover each other

### "tailscale serve" not working

**Check if serve is configured:**
```bash
tailscale serve status
```

**Restart tailscale serve:**
```bash
sudo tailscale serve reset
sudo tailscale serve https / http://localhost:8000
```

### Connection works locally but not remotely

**Firewall might be blocking:**
- Check if chronicle services are running
- Verify ports 8000 and 3010 are accessible locally
- Check Docker containers are running: `docker ps`

**Tailscale might need restart:**
```bash
sudo tailscale down
sudo tailscale up
```

### "Certificate error" or "Not secure"

**Use `tailscale serve` for automatic HTTPS:**
```bash
sudo tailscale serve https / http://localhost:8000
```

This provides automatic valid SSL certificates.

### Hostname not resolving

**Check DNS configuration:**
```bash
tailscale status
```

Look for your computer's DNS name (ends in `.ts.net`).

**Try using IP address instead:**
```bash
tailscale status  # Shows 100.x.x.x IP
```

Use `http://100.x.x.x:8000` instead of hostname.

---

## Advanced Configuration

### Custom Port Mapping

Serve on different ports:

```bash
# Backend on default HTTPS (443)
sudo tailscale serve https / http://localhost:8000

# Frontend on port 8443
sudo tailscale serve https:8443 / http://localhost:3010
```

Access:
- Backend: `https://your-computer.tail12345.ts.net`
- Frontend: `https://your-computer.tail12345.ts.net:8443`

### Multiple Services

Serve multiple Chronicle environments:

```bash
# Dev environment
sudo tailscale serve https:8000 / http://localhost:8000

# Staging environment
sudo tailscale serve https:8100 / http://localhost:8100
```

### Tailscale SSH

Access your computer's terminal remotely:

```bash
# Enable SSH on server
sudo tailscale up --ssh

# Connect from another device
ssh your-computer.tail12345.ts.net
```

### Exit Nodes

Route all internet traffic through your home computer:

```bash
# On home computer
sudo tailscale up --advertise-exit-node

# On phone/laptop
# Tailscale app → Use exit node → Select home computer
```

---

## Cost & Limits

### Free Tier (Personal)
- ✅ Up to **100 devices**
- ✅ Up to **3 users**
- ✅ Unlimited data transfer
- ✅ All core features
- ✅ Perfect for Chronicle personal use

### Paid Tiers
Only needed for:
- More than 100 devices
- Business/team use
- Advanced ACLs
- Custom DNS

**For Chronicle personal use, free tier is more than enough!**

---

## Alternative: Tailscale Funnel

**Tailscale Funnel** allows public internet access (not just your Tailnet).

⚠️ **Not recommended for Chronicle** - security risk!

But if you need it:

```bash
sudo tailscale funnel https / http://localhost:8000
```

This exposes your Chronicle to the **entire internet**. Use with caution!

---

## Summary

✅ **What you installed:**
1. **Tailscale on your computer** - Where Chronicle runs
2. **Tailscale on your phone** - To access Chronicle remotely
3. **Both logged into the same Tailscale account** - Required for devices to see each other

✅ **What you configured:**
- Chronicle knows your Tailscale hostname
- `tailscale serve` provides automatic HTTPS
- Both devices can see each other on your private network

✅ **What you can do now:**
- Access Chronicle from anywhere in the world
- Secure HTTPS connections automatically
- No port forwarding or firewall config needed
- Connect OMI device from anywhere with internet

✅ **Security:**
- End-to-end encrypted between your devices
- Only devices on YOUR Tailscale account can access
- No public exposure to the internet
- Free for personal use (up to 100 devices)

**Remember:** Keep the Tailscale app running on both your computer and phone for remote access to work!

---

## Next Steps

1. **Test from multiple devices** - Phone, tablet, laptop
2. **Configure Chronicle mobile app** - Use your Tailscale hostname
3. **Set up OMI device** - Connect via Tailscale URL
4. **Explore Tailscale features** - SSH, exit nodes, etc.

---

## Getting Help

- **Tailscale Docs**: https://tailscale.com/kb/
- **Tailscale Forum**: https://forum.tailscale.com/
- **Chronicle Issues**: https://github.com/BasedHardware/Friend/issues

---

## Comparison: Local vs Tailscale Access

| Feature | Local Only | With Tailscale |
|---------|-----------|----------------|
| **Access from home WiFi** | ✅ | ✅ |
| **Access when away** | ❌ | ✅ |
| **Phone access (cellular)** | ❌ | ✅ |
| **HTTPS** | Manual setup | Automatic |
| **Port forwarding needed** | Yes (for remote) | No |
| **Firewall config** | Yes (for remote) | No |
| **Security** | Need to manage | Handled by Tailscale |
| **Setup complexity** | High (for remote) | Low |

**Verdict**: Tailscale is highly recommended for Chronicle! 🚀

Welcome to secure remote access! 🎉
