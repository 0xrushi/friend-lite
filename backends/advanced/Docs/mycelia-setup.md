# Mycelia Setup Guide

Mycelia is an advanced memory management interface that provides a rich, interactive way to explore and manage your Friend-Lite memories. This guide explains how to set up and access Mycelia with Friend-Lite.

## What is Mycelia?

Mycelia is a separate frontend application that connects to Friend-Lite's memory system. It provides:
- Advanced memory visualization and exploration
- Graph-based memory relationships
- Rich query and filtering capabilities
- API access for programmatic memory management

## Prerequisites

Before setting up Mycelia, ensure Friend-Lite is installed and running:

```bash
cd backends/advanced
docker compose up --build -d
```

Verify Friend-Lite is accessible at http://localhost:5173

## Setup Methods

There are **two ways** to access Mycelia, depending on your use case:

### Method 1: Auto-Login (Recommended for Web UI)

**Best for**: Regular users accessing Mycelia through the web interface

**How it works**: When you log into Friend-Lite, it automatically stores your authentication token. When you open Mycelia in the same browser, it detects this token and logs you in automatically.

**Setup Steps**:

1. **Enable Mycelia in Friend-Lite**

   Edit your `.env` file:
   ```bash
   MEMORY_PROVIDER=mycelia  # Enable Mycelia integration
   ```

2. **Start Mycelia services**

   ```bash
   docker compose --profile mycelia up --build -d
   ```

3. **Login to Friend-Lite**

   - Visit http://localhost:5173
   - Login with your credentials (e.g., admin@example.com)

4. **Open Mycelia**

   - Visit http://localhost:3002
   - **You're automatically logged in!** ✨

**No manual configuration needed** - the authentication happens automatically via browser localStorage.

---

### Method 2: OAuth Client Credentials (For API Access)

**Best for**:
- API/CLI access to Mycelia
- Programmatic memory management
- Third-party integrations
- Standalone Mycelia usage

**How it works**: Friend-Lite generates OAuth credentials (Client ID and Client Secret) that can be used to authenticate with Mycelia's API.

**Setup Steps**:

1. **Enable Mycelia and start services**

   Edit your `.env` file:
   ```bash
   MEMORY_PROVIDER=mycelia
   ```

   Start services:
   ```bash
   docker compose --profile mycelia up --build -d
   ```

2. **Find your OAuth credentials**

   When Friend-Lite starts with `MEMORY_PROVIDER=mycelia`, it automatically creates OAuth credentials. Check the startup logs:

   ```bash
   docker compose logs friend-backend | grep -A 10 "MYCELIA OAUTH"
   ```

   You'll see output like:
   ```
   🔑 MYCELIA OAUTH CREDENTIALS (Save these!)
   ======================================================================
   User:          admin@example.com
   Client ID:     67a4f2e1b3c9d8e5f6a7b8c9
   Client Secret: mycelia_aBcDeFgHiJkLmNoPqRsTuVwXyZ123456
   ======================================================================
   Configure Mycelia frontend at http://localhost:3002/settings
   ======================================================================
   ```

   **⚠️ IMPORTANT: Save these credentials securely!** They provide full API access to your memories.

3. **Configure Mycelia Frontend (Optional)**

   If you want to use OAuth instead of auto-login in the web UI:

   - Visit http://localhost:3002/settings
   - Enter your **Client ID** and **Client Secret**
   - Click Save

   Mycelia will now use OAuth authentication instead of auto-login.

4. **Use OAuth for API Access**

   **Get an access token**:
   ```bash
   curl -X POST http://localhost:5100/oauth/token \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "grant_type=client_credentials" \
     -d "client_id=YOUR_CLIENT_ID" \
     -d "client_secret=YOUR_CLIENT_SECRET"
   ```

   Response:
   ```json
   {
     "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
     "token_type": "Bearer"
   }
   ```

   **Use the token to access Mycelia API**:
   ```bash
   curl -X POST http://localhost:5100/api/resource/tech.mycelia.objects \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "action": "list",
       "filters": {},
       "options": {"limit": 10}
     }'
   ```

## Service URLs

When running with Mycelia enabled:

| Service | URL | Description |
|---------|-----|-------------|
| Friend-Lite Web UI | http://localhost:5173 | Main Friend-Lite dashboard |
| Friend-Lite API | http://localhost:8000 | Backend API |
| Mycelia Frontend | http://localhost:3002 | Mycelia memory interface |
| Mycelia API | http://localhost:5100 | Mycelia backend API |

## Configuration

### Required Environment Variables

```bash
# Friend-Lite Authentication (Required)
AUTH_SECRET_KEY=your-super-secret-jwt-key-here
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=your-secure-admin-password

# Memory Provider (Required for Mycelia)
MEMORY_PROVIDER=mycelia

# LLM Configuration (Required for memory extraction)
LLM_PROVIDER=openai
OPENAI_API_KEY=your-openai-key-here
OPENAI_MODEL=gpt-4o-mini

# Database (Shared between Friend-Lite and Mycelia)
MONGODB_URI=mongodb://mongo:27017
```

### Mycelia-Specific Configuration

The following variables are automatically set by docker-compose when using the mycelia profile:

```bash
# Mycelia Backend
MYCELIA_PORT=5100
MYCELIA_DB=mycelia  # Separate database for Mycelia objects

# JWT Secret (Must match Friend-Lite!)
JWT_SECRET=your-super-secret-jwt-key-here  # Same as AUTH_SECRET_KEY
```

## Verification

### Check Auto-Login

Open browser console on http://localhost:3002:

```javascript
// Check if Friend-Lite JWT exists
localStorage.getItem('mycelia_jwt_token')
// Should show: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Check OAuth Credentials in Database

```bash
# Connect to MongoDB
docker compose exec mongo mongosh

# Check Friend-Lite user
use friend-lite
db.users.findOne({email: "admin@example.com"}, {mycelia_oauth: 1})

# Check Mycelia API key
use mycelia
db.api_keys.find({name: {$regex: "Friend-Lite Auto"}})
```

### Test Memory Sync

1. Create a memory in Friend-Lite (upload audio or use chat)
2. Open Mycelia at http://localhost:3002
3. Your memories should appear automatically

## Troubleshooting

### Issue: Can't see Mycelia OAuth credentials

**Cause**: `MEMORY_PROVIDER` not set to `mycelia`

**Solution**:
```bash
# Check current setting
docker compose exec friend-backend env | grep MEMORY_PROVIDER

# If not set, edit .env and restart
echo "MEMORY_PROVIDER=mycelia" >> .env
docker compose restart friend-backend
docker compose logs friend-backend | grep -A 10 "MYCELIA OAUTH"
```

### Issue: Auto-login doesn't work

**Cause**: JWT not stored in localStorage

**Solution**:
1. Ensure you logged into Friend-Lite first at http://localhost:5173
2. Check browser console on http://localhost:3002:
   ```javascript
   localStorage.getItem('mycelia_jwt_token')
   ```
3. If null, re-login to Friend-Lite

### Issue: Can't see objects in Mycelia

**Cause**: JWT principal doesn't match object userId

**Solution**:
- Use auto-login (recommended) - ensures principal matches
- Verify JWT secret matches in both services:
  ```bash
  docker compose exec friend-backend env | grep AUTH_SECRET_KEY
  docker compose exec mycelia-backend env | grep JWT_SECRET
  ```

### Issue: OAuth token exchange fails

**Cause**: Wrong credentials or JWT secret mismatch

**Solution**:
1. Verify credentials from logs:
   ```bash
   docker compose logs friend-backend | grep -A 10 "MYCELIA OAUTH"
   ```
2. Check JWT secrets match (see above)
3. Verify API key in database:
   ```bash
   docker compose exec mongo mongosh
   use mycelia
   db.api_keys.find().pretty()
   ```

### Issue: "Connection refused" to Mycelia

**Cause**: Mycelia services not running

**Solution**:
```bash
# Start with Mycelia profile
docker compose --profile mycelia up --build -d

# Verify services are running
docker compose ps | grep mycelia
```

## Security Considerations

### JWT Secret

**CRITICAL**: `AUTH_SECRET_KEY` (Friend-Lite) and `JWT_SECRET` (Mycelia) **MUST match**!

If they don't match:
- Auto-login won't work (JWT verification fails)
- Data isolation will be broken (wrong user IDs)

### OAuth Credentials

- **Client Secret** provides full API access - treat it like a password
- Never commit credentials to version control
- Rotate credentials if compromised (delete API key from Mycelia database)
- Use separate credentials for different applications/users

### Network Security

For production deployments:
- Use HTTPS for all services
- Restrict Mycelia API access (port 5100) to authorized networks
- Consider using API gateway or reverse proxy
- Implement rate limiting on OAuth endpoints

## Advanced: Multiple Users

Each Friend-Lite user automatically gets their own OAuth credentials:

1. Users created via Friend-Lite get auto-synced to Mycelia
2. Each user has isolated memory access
3. OAuth credentials are per-user
4. Data isolation is enforced at database level

To get credentials for a different user:
```bash
# Login as that user in Friend-Lite
# Check logs for their credentials
docker compose logs friend-backend | grep "User:.*$EMAIL" -A 5
```

## Additional Resources

- **[Mycelia Auth Details](mycelia-auth-and-ownership.md)** - Deep dive into authentication flow
- **[Mycelia Auto-Login](mycelia-auto-login.md)** - Auto-login implementation details
- **[Test Environment](mycelia-test-environment.md)** - Running Mycelia in test mode
- **[Memory Providers Guide](memory-configuration-guide.md)** - Compare Friend-Lite vs Mycelia memory systems

## Summary

### For Web UI Users (Recommended)
1. Set `MEMORY_PROVIDER=mycelia` in `.env`
2. Run `docker compose --profile mycelia up --build -d`
3. Login to Friend-Lite at http://localhost:5173
4. Visit Mycelia at http://localhost:3002 (auto-login!)

### For API Users
1. Set `MEMORY_PROVIDER=mycelia` in `.env`
2. Run `docker compose --profile mycelia up --build -d`
3. Get credentials from logs: `docker compose logs friend-backend | grep -A 10 "MYCELIA OAUTH"`
4. Exchange credentials for access token via OAuth
5. Use access token for API calls

Both methods provide the same memory access - choose based on your use case!
