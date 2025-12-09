# Mycelia Auto-Login and OAuth Access

Friend-Lite supports **two methods** for accessing Mycelia, giving you flexibility for different use cases.

## Method 1: Auto-Login (Web Frontend) ✅ RECOMMENDED

**Use Case**: Seamless access when using both Friend-Lite and Mycelia web frontends in the same browser.

**How it works**:
1. User logs into Friend-Lite web dashboard (`/login`)
2. Friend-Lite stores JWT in `localStorage['mycelia_jwt_token']`
3. User opens Mycelia frontend (same browser)
4. Mycelia automatically detects the JWT and logs in
5. **No manual configuration needed!**

**Implementation**:
- Friend-Lite: `webui/src/contexts/AuthContext.tsx` - Stores JWT on login
- Mycelia: `extras/mycelia/frontend/src/lib/auth.ts:40-44` - Reads JWT from localStorage

**User Experience**:
```
User Login Flow:
1. Visit http://localhost:5173 (Friend-Lite)
2. Login with email/password
3. Visit http://localhost:3002 (Mycelia)
4. Already logged in! ✨
```

## Method 2: OAuth Client Credentials (API Access)

**Use Case**:
- Direct API access to Mycelia
- CLI tools and scripts
- Standalone Mycelia usage (without Friend-Lite frontend)
- Third-party integrations

**How it works**:
1. On startup, Friend-Lite creates OAuth credentials for admin user (if `MEMORY_PROVIDER=mycelia`)
2. Credentials are logged to console and stored in Friend-Lite database
3. Use Client ID + Client Secret to authenticate with Mycelia API

**Implementation**:
- `services/mycelia_sync.py` - Sync service that creates OAuth credentials
- `app_factory.py:76-82` - Calls sync on startup
- Mycelia: `extras/mycelia/backend/app/lib/auth/tokens.ts` - Verifies OAuth credentials

**Startup Logs**:
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

**API Usage Example**:
```bash
# Exchange credentials for access token
curl -X POST http://localhost:5100/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET"

# Use access token for API calls
curl -X POST http://localhost:5100/api/resource/tech.mycelia.objects \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action": "list", "filters": {}, "options": {"limit": 10}}'
```

**Manual Frontend Configuration**:
1. Visit http://localhost:3002/settings
2. Enter the Client ID and Client Secret from startup logs
3. Save settings
4. Mycelia will use OAuth instead of auto-login

## Authentication Priority

Mycelia frontend checks authentication in this order:

1. **localStorage JWT** (`mycelia_jwt_token`) - Auto-login from Friend-Lite
2. **OAuth credentials** (from Settings page) - Manual configuration
3. **No authentication** - Shows login/settings UI

## User Isolation and Object Ownership

Both authentication methods use the **same user ID** as the principal:

- **Friend-Lite JWT**: `principal = payload.sub` (Friend-Lite user ID)
- **OAuth Token**: `principal = api_key.owner` (Friend-Lite user ID)

This ensures:
✅ Objects created via Friend-Lite are accessible via Mycelia
✅ Objects created via Mycelia are accessible via Friend-Lite
✅ All objects have `userId = friend_lite_user_id`
✅ Data isolation works correctly across both systems

## Configuration

### Environment Variables

```bash
# Friend-Lite
AUTH_SECRET_KEY=your-super-secret-jwt-key-here
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=your-secure-password

# Mycelia (must match Friend-Lite)
JWT_SECRET=your-super-secret-jwt-key-here  # Same as AUTH_SECRET_KEY!

# Memory Provider (enables OAuth sync)
MEMORY_PROVIDER=mycelia  # OAuth credentials created on startup
```

### MongoDB Collections

**Friend-Lite Database** (`friend-lite`):
- `users` collection:
  ```json
  {
    "_id": ObjectId("692c7727c7b16bdf58d23cd1"),
    "email": "admin@example.com",
    "mycelia_oauth": {
      "client_id": "67a4f2e1b3c9d8e5f6a7b8c9",
      "created_at": "2025-12-01T10:30:00Z",
      "synced": true
    }
  }
  ```

**Mycelia Database** (`mycelia` or `mycelia_test`):
- `api_keys` collection:
  ```json
  {
    "_id": ObjectId("67a4f2e1b3c9d8e5f6a7b8c9"),
    "owner": "692c7727c7b16bdf58d23cd1",  // Friend-Lite user ID
    "hashedKey": "...",
    "salt": "...",
    "name": "Friend-Lite Auto (admin@example.com)",
    "policies": [{"resource": "**", "action": "*", "effect": "allow"}],
    "isActive": true
  }
  ```

## Debugging

### Check Auto-Login Status

Open browser console on Mycelia frontend:
```javascript
// Check if Friend-Lite JWT exists
localStorage.getItem('mycelia_jwt_token')

// Check OAuth settings
JSON.parse(localStorage.getItem('mycelia-settings'))
```

### Verify OAuth Credentials

```bash
# Check Friend-Lite database
mongosh mongodb://localhost:27017/friend-lite
db.users.findOne({email: "admin@example.com"}, {mycelia_oauth: 1})

# Check Mycelia database
mongosh mongodb://localhost:27017/mycelia
db.api_keys.find({owner: "692c7727c7b16bdf58d23cd1"})
```

### Common Issues

**Issue**: "Can't see objects in Mycelia"
- **Check**: JWT principal matches object userId
- **Solution**: Use auto-login (localStorage) for seamless experience

**Issue**: "OAuth token invalid"
- **Check**: JWT_SECRET in Mycelia matches AUTH_SECRET_KEY in Friend-Lite
- **Solution**: Ensure environment variables are identical

**Issue**: "No OAuth credentials in logs"
- **Check**: `MEMORY_PROVIDER=mycelia` is set
- **Check**: Admin user exists in Friend-Lite database
- **Solution**: Check startup logs for errors

## Summary

| Feature | Auto-Login | OAuth |
|---------|-----------|-------|
| **Use Case** | Web frontend | API/CLI access |
| **Setup** | Automatic | Manual or auto-sync |
| **User Experience** | Seamless | Requires credentials |
| **Principal** | `sub` from JWT | `owner` from API key |
| **Best For** | End users | Developers/integrations |

**Recommendation**: Use auto-login for normal web usage, OAuth for API access and integrations.
