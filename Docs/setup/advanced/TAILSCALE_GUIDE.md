# Tailscale Configuration Guide

## Understanding Tailscale Concepts

### Tailscale IP vs Hostname

When you run `tailscale status`, you'll see output like:

```
anubis    100.83.66.30   anubis.tail12345.ts.net   linux   -
kraken    100.84.22.15   kraken.tail12345.ts.net   linux   -
friend    100.85.10.42   friend.tail12345.ts.net   darwin  -
```

Each machine has:
1. **Machine Name** (left): Short name (e.g., `anubis`)
2. **IP Address** (middle): Tailscale IP (e.g., `100.83.66.30`)
3. **Hostname** (right): Full DNS name (e.g., `anubis.tail12345.ts.net`)

### Which One to Use?

**Use the HOSTNAME (ends in .ts.net)**, NOT the IP address.

**Why hostname instead of IP?**
- ✅ Permanent - doesn't change
- ✅ Works with SSL certificates
- ✅ Human-readable
- ✅ DNS resolution built-in
- ✅ Works across Tailscale networks

**IP addresses can change** when:
- You rejoin Tailscale
- Network configuration changes
- Tailscale updates

## Finding Your Tailscale Hostname

### Method 1: Using `tailscale status`

```bash
tailscale status
```

Output:
```
anubis    100.83.66.30   anubis.tail12345.ts.net   linux   -
                         ^^^^^^^^^^^^^^^^^^^^^^^^
                         This is your hostname!
```

**Your hostname is in the third column, ending in `.ts.net`**

### Method 2: Using `tailscale status --json`

```bash
tailscale status --json | grep DNSName
```

Output:
```json
"DNSName":"anubis.tail12345.ts.net."
```

Remove the trailing dot: `anubis.tail12345.ts.net`

### Method 3: Check Tailscale Admin Console

1. Visit https://login.tailscale.com/admin/machines
2. Find your machine in the list
3. The hostname is shown under "DNS name"

## When You're Asked for Tailscale Hostname

### During `make setup-tailscale`

**Question:** "Tailscale hostname [anubis.tail12345.ts.net]:"

**What to enter:** The hostname for **THIS machine** (where you're running the wizard)

**Why:** This is used to:
1. Generate SSL certificates for this machine
2. Configure CORS to allow connections from this hostname
3. Set up URLs for accessing this machine's services

**Example:**
```bash
# You're on machine "anubis"
tailscale status shows:
  anubis    100.83.66.30   anubis.tail12345.ts.net   linux   -

Enter: anubis.tail12345.ts.net
```

### During `make setup-environment`

**Question:** "Tailscale hostname (or press Enter to skip):"

**What to enter:** Same hostname as before (usually auto-filled if you ran `make setup-tailscale`)

**Why asked again:** In case you:
- Skipped Tailscale setup earlier
- Want to create an environment for a different machine
- Ran `make setup-environment` standalone

**Difference from first question:**
- First question (setup-tailscale): Configures SSL certificates and validates Tailscale
- Second question (setup-environment): Just saves hostname to environment config
- **They should usually be the same!**

## Common Scenarios

### Scenario 1: Single Machine Setup

You have one machine running Friend-Lite:

```bash
# Run wizard on your machine
make wizard

# Tailscale setup:
Tailscale hostname: friend-lite.tail12345.ts.net  ← Your machine's hostname

# Environment setup:
Tailscale hostname: friend-lite.tail12345.ts.net  ← Same hostname
```

### Scenario 2: Distributed Setup (Backend + Speaker Service)

You have two machines:
- Machine 1 (anubis): Backend
- Machine 2 (kraken): Speaker Recognition

**On Machine 1 (Backend):**
```bash
make wizard
# Tailscale hostname: anubis.tail12345.ts.net  ← THIS machine's hostname

# Then configure speaker service URL in config-docker.env:
SPEAKER_SERVICE_URL=https://kraken.tail12345.ts.net:8085  ← OTHER machine
```

**On Machine 2 (Speaker Service):**
```bash
make wizard
# Tailscale hostname: kraken.tail12345.ts.net  ← THIS machine's hostname

# Then configure backend URL in config-docker.env:
BACKEND_URL=https://anubis.tail12345.ts.net:8000  ← OTHER machine
```

### Scenario 3: Multiple Environments on Same Machine

You want dev, staging, and prod on the same machine:

```bash
# Run wizard once
make wizard
# Tailscale hostname: friend-lite.tail12345.ts.net

# All environments use the same hostname
./start-env.sh dev      # Uses friend-lite.tail12345.ts.net:8000
./start-env.sh staging  # Uses friend-lite.tail12345.ts.net:8100
./start-env.sh prod     # Uses friend-lite.tail12345.ts.net:8200
```

## Troubleshooting

### Issue: "No hostname detected"

**Cause:** Tailscale not running or `tailscale status --json` not available

**Solution:**
```bash
# Check Tailscale status
tailscale status

# If not running:
sudo tailscale up

# Manually find hostname from status output
tailscale status
# Look at third column, copy the hostname ending in .ts.net
```

### Issue: "Should I use the IP or hostname?"

**Answer:** Always use the **hostname** (ends in .ts.net)

**Why:**
- IPs can change
- SSL certificates need hostnames
- DNS is more reliable
- Better for documentation

### Issue: "I entered the IP address by mistake"

**Solution:** Edit the environment file:
```bash
# Edit your environment file
nano environments/dev.env

# Change:
TAILSCALE_HOSTNAME=100.83.66.30  # Wrong! IP address

# To:
TAILSCALE_HOSTNAME=anubis.tail12345.ts.net  # Correct! Hostname
```

### Issue: "Wizard shows different hostname than I expect"

**Cause:** Auto-detection might pick the wrong machine

**Solution:** Just enter the correct hostname manually:
```bash
# When prompted:
Tailscale hostname [wrong-hostname.ts.net]:
# Type: correct-hostname.ts.net
```

### Issue: "I'm not sure which machine I'm on"

**Solution:**
```bash
# Check your machine name
hostname

# Check Tailscale status
tailscale status
# The first line (with asterisk *) is THIS machine

# Example output:
anubis*   100.83.66.30   anubis.tail12345.ts.net   linux   -
          ^
          This asterisk means THIS is your current machine
```

## Quick Reference

| Command | Purpose |
|---------|---------|
| `tailscale status` | Show all machines and their hostnames |
| `tailscale status --json` | JSON output for parsing |
| `hostname` | Show local machine name |
| `tailscale ip` | Show your Tailscale IP (don't use for wizard!) |

| Concept | Example | Use in Wizard |
|---------|---------|---------------|
| Machine Name | `anubis` | No - too short |
| IP Address | `100.83.66.30` | No - can change |
| **Hostname** | `anubis.tail12345.ts.net` | **Yes - use this!** |

## SSL Certificate Names

When you generate SSL certificates, they'll include:
- `localhost`
- `127.0.0.1`
- Your Tailscale hostname (e.g., `anubis.tail12345.ts.net`)

This means you can access services via:
- `https://localhost:8000` (on the machine itself)
- `https://anubis.tail12345.ts.net:8000` (from any Tailscale device)

## Summary

**Key Points:**
1. ✅ Use **hostname** (ends in `.ts.net`), NOT IP address
2. ✅ Find it with: `tailscale status` (third column)
3. ✅ Use the hostname for **THIS machine** (where you're running the wizard)
4. ✅ If wizard asks twice, enter the **same hostname** both times
5. ✅ For distributed setup, each machine uses its **own hostname**

**Quick Check:**
```bash
# Am I using the right thing?
✅ anubis.tail12345.ts.net     # Correct - hostname
❌ 100.83.66.30                # Wrong - IP address
❌ anubis                      # Wrong - short name
❌ tail12345.ts.net            # Wrong - missing machine name
```

Still confused? Just run `tailscale status` and copy the **third column** for your machine! 🎯
