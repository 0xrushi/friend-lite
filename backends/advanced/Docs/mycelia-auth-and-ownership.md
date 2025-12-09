# Mycelia Authentication & Object Ownership

## How Mycelia Determines the Logged-In User

### 1. Token Extraction
```typescript
// From extras/mycelia/backend/app/lib/auth/core.server.ts:82-133

async authenticate(req: Request): Promise<Auth | null> {
  // Extract token from:
  // 1. Authorization header: "Bearer <token>"
  // 2. Query parameter: ?token=<token>
  // 3. URL search params

  // Try Friend-Lite JWT first
  let auth = await verifyFriendLiteToken(token);

  if (!auth) {
    // Fall back to Mycelia native token
    auth = await verifyToken(token);
  }

  return auth;
}
```

### 2. JWT Verification & Auth Object Creation

#### Friend-Lite JWT
```typescript
// extras/mycelia/backend/app/lib/auth/friend-lite-jwt.ts:36-86

export const verifyFriendLiteToken = async (token: string): Promise<Auth | null> => {
  const { payload } = await jwtVerify(token, secret);

  // Extract principal from JWT (sub for Friend-Lite, owner/principal for OAuth)
  const principal = payload.sub || payload.principal || payload.owner;

  // Create Auth object
  const auth = new Auth({
    principal,  // THIS is the user ID used for everything!
    policies: [{ resource: "**", action: "*", effect: "allow" }],
  });

  return auth;
}
```

#### OAuth Token (Client Credentials)
```typescript
// extras/mycelia/backend/app/lib/auth/tokens.ts:138-154

async decodeAccessToken(apiKey: string): Promise<string | null> {
  const keyDoc = await verifyApiKey(apiKey);

  return signJWT(
    keyDoc.owner,           // owner field (Friend-Lite user ID)
    keyDoc._id!.toString(), // principal field (API key ID) ⚠️
    keyDoc.policies,
    duration,
  );
}

// The resulting JWT has:
// {
//   "owner": "692c7727c7b16bdf58d23cd1",     // Friend-Lite user
//   "principal": "692d76235ef8d25e060ad9f6", // API key ID
//   "policies": [...]
// }
```

### 3. Auth Object Structure

```typescript
class Auth {
  principal: string;  // THIS is what everything is scoped by!
  policies: Policy[];

  constructor(options: { policies?: Policy[]; principal: string }) {
    this.policies = options.policies || [];
    this.principal = options.principal;  // ⭐ KEY FIELD
  }
}
```

## How Object Ownership Works

### 1. Object Creation (Auto-inject userId)
```typescript
// extras/mycelia/backend/app/lib/objects/resource.server.ts:261-286

case "create": {
  const doc = {
    ...input.object,
    userId: auth.principal,  // ⭐ Auto-inject from JWT principal
    version: 1,
    createdAt: new Date(),
    updatedAt: new Date(),
  };

  await mongo({ action: "insertOne", collection: "objects", doc });
}
```

### 2. Object Retrieval (Auto-scope by userId)
```typescript
// extras/mycelia/backend/app/lib/objects/resource.server.ts:289-303

case "get": {
  const object = await mongo({
    action: "findOne",
    collection: "objects",
    query: {
      _id: objectId,
      userId: auth.principal  // ⭐ Auto-scope by user
    },
  });
  if (!object) throw new Error("Object not found");
  return object;
}
```

### 3. Object Listing (Auto-scope by userId)
```typescript
// extras/mycelia/backend/app/lib/objects/resource.server.ts:412-441

case "list": {
  let query = input.filters || {};

  // Auto-scope all queries by user
  query = {
    ...query,
    userId: auth.principal,  // ⭐ ALWAYS filtered by principal
  };

  const results = await mongo({
    action: "find",
    collection: "objects",
    query,
    options: { limit, skip, sort }
  });
  return results;
}
```

### 4. Object Updates & Deletes (Auto-scope by userId)
```typescript
case "update":
case "delete": {
  // First, find the object - ensures it belongs to this user
  const current = await mongo({
    action: "findOne",
    collection: "objects",
    query: { _id: objectId, userId: auth.principal },  // ⭐ Verify ownership
  });
  if (!current) throw new Error("Object not found");

  // Then perform the update/delete
  await mongo({ ... });
}
```

## The Authentication Flow Summary

```
┌─────────────────────────────────────────────────────────────┐
│ 1. HTTP Request with JWT Token                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Mycelia `authenticate()` function                        │
│    • Extracts token from Authorization header              │
│    • Tries Friend-Lite JWT verification first              │
│    • Falls back to Mycelia native JWT                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. JWT Verification                                         │
│    Friend-Lite JWT:                                         │
│      → principal = payload.sub (user ID)                    │
│    OAuth Token:                                             │
│      → principal = keyDoc._id.toString() (API key ID)       │
│                                                             │
│    Creates: Auth { principal, policies }                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Object Operations                                        │
│    CREATE:  doc.userId = auth.principal                     │
│    GET:     query { _id, userId: auth.principal }          │
│    LIST:    query { ..., userId: auth.principal }          │
│    UPDATE:  query { _id, userId: auth.principal }          │
│    DELETE:  query { _id, userId: auth.principal }          │
└─────────────────────────────────────────────────────────────┘
```

## The Problem: OAuth Token Principal Mismatch

### Friend-Lite Memory Creation (via JWT)
```python
# Friend-Lite generates JWT with actual user ID
jwt_token = generate_jwt_for_user(user_id, user_email)
# JWT payload: { "sub": "692c7727c7b16bdf58d23cd1", "email": "..." }

# Mycelia extracts principal from sub field
# principal = "692c7727c7b16bdf58d23cd1"

# Object created with:
# { "userId": "692c7727c7b16bdf58d23cd1", ... }
```

### Mycelia OAuth Token Access
```javascript
// OAuth client credentials exchange
// API key has: { owner: "692c7727c7b16bdf58d23cd1", _id: "692d76235ef8d25e060ad9f6" }

// Mycelia generates JWT with API key ID as principal
// JWT payload: { "principal": "692d76235ef8d25e060ad9f6", ... }

// Object queries filtered by:
// { "userId": "692d76235ef8d25e060ad9f6" }

// ❌ Mismatch! Objects have userId="692c7727..." but query expects "692d7623..."
```

## The Answer

**Q: If I create a new object via Friend-Lite, will I be able to access it via Mycelia OAuth?**

**A: No**, because:

1. Friend-Lite creates objects with `userId = "692c7727c7b16bdf58d23cd1"` (actual user ID)
2. Mycelia OAuth token has `principal = "692d76235ef8d25e060ad9f6"` (API key ID)
3. All Mycelia queries filter by `userId == principal`
4. **Mismatch** → Objects not visible via OAuth!

## Solutions

### Option 1: Use Friend-Lite Auto-Login (Recommended ✅)
Access Mycelia through Friend-Lite at **http://localhost:5173/memories**
- Uses Friend-Lite JWT directly
- Principal matches object userId
- All objects accessible!

### Option 2: Fix Mycelia's OAuth Implementation (Requires Code Change)
Modify `extras/mycelia/backend/app/lib/auth/tokens.ts`:
```typescript
export async function decodeAccessToken(...) {
  const keyDoc = await verifyApiKey(apiKey);

  return signJWT(
    keyDoc.owner,
    keyDoc.owner,  // ⬅️ Use owner as principal, not _id!
    keyDoc.policies,
    duration,
  );
}
```

This would make OAuth tokens use the actual user ID as principal, matching object ownership.
