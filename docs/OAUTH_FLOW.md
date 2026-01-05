# OAuth 2.1 Agent Authentication Flow

## Overview

The OAuth 2.1 Agent Authentication Flow is a specialized authorization pattern designed for AI agents that need to access resources on behalf of users while maintaining distinct identities for both parties.

This flow is based on the OAuth 2.1 Authorization Code Flow with specific adaptations for agent-based scenarios.

## Key Principles

1. **Dual Identity**: Both user and agent have distinct, verifiable identities
2. **Explicit Consent**: Users must explicitly grant permissions to agents
3. **Granular Permissions**: Scope-based access control for fine-grained authorization
4. **Limited Token Lifetime**: Short-lived access tokens with refresh capability
5. **Revocable Access**: Users can revoke agent access at any time

## Flow Diagram

```
┌─────────┐                                                ┌─────────────┐
│         │                                                │             │
│  User   │                                                │    Agent    │
│         │                                                │   Client    │
└────┬────┘                                                └──────┬──────┘
     │                                                            │
     │ 1. User initiates agent task                             │
     │───────────────────────────────────────────────────────────►│
     │                                                            │
     │                                                            │ 2. Agent checks
     │                                                            │    for valid token
     │                                                            │
     │                  ┌─────────────────┐                      │
     │                  │ Authorization   │                      │
     │                  │     Server      │                      │
     │                  └────────┬────────┘                      │
     │                           │                               │
     │                           │ 3. Agent requests authorization
     │                           │◄──────────────────────────────│
     │                           │    GET /authorize?            │
     │                           │      response_type=code       │
     │                           │      client_id={agent_id}     │
     │                           │      redirect_uri={uri}       │
     │                           │      scope={scopes}           │
     │                           │      state={random_state}     │
     │                           │                               │
     │ 4. Redirect to login      │                               │
     │◄──────────────────────────│                               │
     │    (if not authenticated) │                               │
     │                           │                               │
     │ 5. User provides credentials                              │
     │───────────────────────────►│                               │
     │    POST /login            │                               │
     │      username={user}      │                               │
     │      password={pass}      │                               │
     │                           │                               │
     │ 6. Show consent screen    │                               │
     │◄──────────────────────────│                               │
     │    Agent "{name}" requests:                               │
     │    ☐ Read your profile    │                               │
     │    ☐ Access your documents│                               │
     │    [Allow] [Deny]         │                               │
     │                           │                               │
     │ 7. User grants consent    │                               │
     │───────────────────────────►│                               │
     │    POST /authorize/consent│                               │
     │      approved=true        │                               │
     │                           │                               │
     │                           │ 8. Generate auth code         │
     │                           │    and store consent          │
     │                           │                               │
     │ 9. Redirect to agent with auth code                       │
     │───────────────────────────────────────────────────────────►│
     │    {redirect_uri}?code={auth_code}&state={state}         │
     │                           │                               │
     │                           │ 10. Exchange code for tokens  │
     │                           │◄──────────────────────────────│
     │                           │     POST /token               │
     │                           │       grant_type=authorization_code
     │                           │       code={auth_code}        │
     │                           │       redirect_uri={uri}      │
     │                           │       client_id={agent_id}    │
     │                           │       client_secret={secret}  │
     │                           │                               │
     │                           │ 11. Validate code & client    │
     │                           │                               │
     │                           │ 12. Issue tokens              │
     │                           │──────────────────────────────►│
     │                           │     {                         │
     │                           │       access_token: "...",    │
     │                           │       token_type: "Bearer",   │
     │                           │       expires_in: 3600,       │
     │                           │       refresh_token: "...",   │
     │                           │       scope: "read:profile..."│
     │                           │     }                         │
     │                           │                               │
     │                ┌──────────────────┐                       │
     │                │  Resource Server │                       │
     │                └────────┬─────────┘                       │
     │                         │                                 │
     │                         │ 13. Access protected resource   │
     │                         │◄────────────────────────────────│
     │                         │     GET /api/user/profile       │
     │                         │     Authorization: Bearer {token}
     │                         │                                 │
     │                         │ 14. Validate token              │
     │                         │     (verify signature, expiry,  │
     │                         │      scopes)                    │
     │                         │                                 │
     │                         │ 15. Return protected resource   │
     │                         │─────────────────────────────────►│
     │                         │     {user profile data}         │
     │                         │                                 │
     │ 16. Agent processes resource and completes task           │
     │◄──────────────────────────────────────────────────────────│
     │                                                            │
```

## Detailed Flow Steps

### Step 1: User Initiates Agent Task

The user requests the agent to perform a task that requires access to protected resources.

**Example**:
```
User: "Agent, please summarize my recent documents"
```

### Step 2: Agent Checks for Valid Token

The agent checks if it has a valid access token for this user with the required scopes.

**Decision Points**:
- ✅ Valid token exists → Use it (skip to Step 13)
- ❌ No token or expired → Initiate authorization flow (Step 3)
- ❌ Token lacks required scopes → Request new authorization with additional scopes

### Step 3: Authorization Request

The agent redirects the user to the authorization server's authorization endpoint.

**Request**:
```http
GET /authorize?response_type=code
    &client_id=agent_123
    &redirect_uri=https://agent.example.com/callback
    &scope=read:profile read:documents
    &state=xyz123
    &code_challenge=E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM
    &code_challenge_method=S256
```

**Parameters**:
- `response_type`: Must be `code` (authorization code grant)
- `client_id`: The registered agent identifier
- `redirect_uri`: Where to send the authorization code (must match registered URI)
- `scope`: Space-separated list of requested permissions
- `state`: Random string to prevent CSRF attacks
- `code_challenge`: PKCE code challenge (optional but recommended)
- `code_challenge_method`: PKCE challenge method (S256 recommended)

### Step 4-5: User Authentication

If the user is not already authenticated, the authorization server presents a login page.

**Request**:
```http
POST /login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=secure_password
```

**Response**:
- Success: Creates session, redirects to consent screen
- Failure: Shows error message, allows retry

**Security Considerations**:
- Passwords must be hashed using bcrypt or Argon2
- Implement rate limiting to prevent brute force attacks
- Support MFA (future enhancement)

### Step 6-7: User Consent

The authorization server displays a consent screen showing:
- Agent identity (name, description, icon)
- Requested scopes with human-readable descriptions
- Option to allow or deny

**Consent Screen Example**:
```
┌─────────────────────────────────────────────┐
│  Authorization Request                      │
├─────────────────────────────────────────────┤
│                                             │
│  Agent "Document Analyzer" wants to:        │
│                                             │
│  ✓ Read your profile information            │
│  ✓ Access your documents                    │
│                                             │
│  This will allow the agent to:              │
│  • View your name and email                 │
│  • Read and analyze your documents          │
│                                             │
│  You can revoke this access at any time     │
│  in your account settings.                  │
│                                             │
│  [ Deny ]              [ Allow ]            │
└─────────────────────────────────────────────┘
```

**Request**:
```http
POST /authorize/consent
Content-Type: application/x-www-form-urlencoded

approved=true&consent_id=consent_789
```

### Step 8: Authorization Code Generation

Upon user consent, the authorization server:

1. **Generates Authorization Code**:
   - Cryptographically random string (32+ bytes)
   - Short expiration (5 minutes)
   - Single-use only

2. **Stores Authorization Record**:
   ```json
   {
     "code": "auth_abc123...",
     "client_id": "agent_123",
     "user_id": "user_456",
     "redirect_uri": "https://agent.example.com/callback",
     "scope": "read:profile read:documents",
     "expires_at": "2026-01-05T10:15:00Z",
     "code_challenge": "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
     "used": false
   }
   ```

3. **Records Consent**:
   ```json
   {
     "user_id": "user_456",
     "agent_id": "agent_123",
     "scopes": ["read:profile", "read:documents"],
     "granted_at": "2026-01-05T10:10:00Z",
     "revoked": false
   }
   ```

### Step 9: Authorization Code Delivery

The authorization server redirects the user back to the agent's redirect URI.

**Response**:
```http
HTTP/1.1 302 Found
Location: https://agent.example.com/callback?code=auth_abc123&state=xyz123
```

**Agent Validation**:
- ✅ Verify `state` matches original request (CSRF protection)
- ✅ Extract authorization code
- ❌ If error parameter present, handle authorization denial

### Step 10: Token Request

The agent exchanges the authorization code for tokens by making a server-to-server request.

**Request**:
```http
POST /token
Content-Type: application/x-www-form-urlencoded
Authorization: Basic base64(client_id:client_secret)

grant_type=authorization_code
&code=auth_abc123
&redirect_uri=https://agent.example.com/callback
&code_verifier=dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk
```

**Parameters**:
- `grant_type`: Must be `authorization_code`
- `code`: The authorization code received in Step 9
- `redirect_uri`: Must match the original request
- `code_verifier`: PKCE code verifier (if PKCE used)

**Authentication**:
- Client credentials in Basic Auth header, OR
- `client_id` and `client_secret` in request body

### Step 11: Authorization Code Validation

The authorization server validates the request:

```python
def validate_token_request(request):
    # 1. Verify client authentication
    if not authenticate_client(request.client_id, request.client_secret):
        return error("invalid_client")

    # 2. Verify authorization code exists and is valid
    auth_code = get_authorization_code(request.code)
    if not auth_code or auth_code.used or auth_code.expired:
        return error("invalid_grant")

    # 3. Verify code belongs to this client
    if auth_code.client_id != request.client_id:
        return error("invalid_grant")

    # 4. Verify redirect URI matches
    if auth_code.redirect_uri != request.redirect_uri:
        return error("invalid_grant")

    # 5. Verify PKCE (if used)
    if auth_code.code_challenge:
        if not verify_pkce(request.code_verifier, auth_code.code_challenge):
            return error("invalid_grant")

    # 6. Mark code as used (prevent replay)
    mark_code_as_used(auth_code)

    return auth_code
```

### Step 12: Token Issuance

Upon successful validation, the authorization server issues tokens.

**Access Token (JWT)**:
```json
{
  "header": {
    "alg": "RS256",
    "typ": "JWT",
    "kid": "key_001"
  },
  "payload": {
    "iss": "https://auth.example.com",
    "sub": "user_456",
    "aud": "https://api.example.com",
    "exp": 1704452400,
    "iat": 1704448800,
    "client_id": "agent_123",
    "scope": "read:profile read:documents",
    "jti": "token_unique_id"
  },
  "signature": "..."
}
```

**Refresh Token (Opaque)**:
- Cryptographically random string (32+ bytes)
- Stored in database with metadata
- Longer expiration (30 days)
- Can be revoked

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "refresh_xyz789...",
  "scope": "read:profile read:documents"
}
```

**Token Storage**:
```json
{
  "access_token": {
    "jti": "token_unique_id",
    "user_id": "user_456",
    "client_id": "agent_123",
    "scopes": ["read:profile", "read:documents"],
    "expires_at": "2026-01-05T11:10:00Z",
    "revoked": false
  },
  "refresh_token": {
    "token": "refresh_xyz789...",
    "user_id": "user_456",
    "client_id": "agent_123",
    "access_token_jti": "token_unique_id",
    "expires_at": "2026-02-04T10:10:00Z",
    "revoked": false
  }
}
```

### Step 13: Resource Access

The agent uses the access token to request protected resources.

**Request**:
```http
GET /api/user/profile
Host: api.example.com
Authorization: Bearer eyJhbGciOiJSUzI1NiIs...
```

### Step 14: Token Validation

The resource server validates the access token:

```python
def validate_access_token(token):
    # 1. Decode JWT
    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience="https://api.example.com"
        )
    except jwt.InvalidTokenError:
        return error("invalid_token")

    # 2. Check expiration
    if payload["exp"] < current_timestamp():
        return error("token_expired")

    # 3. Check if revoked (optional - check database or cache)
    if is_token_revoked(payload["jti"]):
        return error("token_revoked")

    # 4. Extract claims
    return {
        "user_id": payload["sub"],
        "client_id": payload["client_id"],
        "scopes": payload["scope"].split()
    }
```

**Scope Validation**:
```python
def check_scope(required_scope, token_scopes):
    if required_scope not in token_scopes:
        return error("insufficient_scope")
    return True
```

### Step 15: Resource Response

If validation succeeds and scopes are sufficient, the resource server returns the protected resource.

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "user_456",
  "name": "John Doe",
  "email": "john@example.com",
  "created_at": "2025-01-01T00:00:00Z"
}
```

### Step 16: Task Completion

The agent processes the resource and completes the user's requested task.

## Token Refresh Flow

When the access token expires, the agent uses the refresh token to obtain a new access token.

```
Agent                Authorization Server
  │                         │
  │ POST /token             │
  │─────────────────────────►│
  │ grant_type=refresh_token│
  │ refresh_token={token}   │
  │ client_id={id}          │
  │ client_secret={secret}  │
  │                         │
  │                         │ 1. Validate refresh token
  │                         │ 2. Verify client credentials
  │                         │ 3. Check if revoked
  │                         │ 4. Generate new access token
  │                         │ 5. Rotate refresh token
  │                         │
  │ New Tokens              │
  │◄─────────────────────────│
  │ {                       │
  │   access_token: "...",  │
  │   refresh_token: "...", │
  │   expires_in: 3600      │
  │ }                       │
```

**Request**:
```http
POST /token
Content-Type: application/x-www-form-urlencoded
Authorization: Basic base64(client_id:client_secret)

grant_type=refresh_token
&refresh_token=refresh_xyz789
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "refresh_new_abc456",
  "scope": "read:profile read:documents"
}
```

**Refresh Token Rotation**:
- Old refresh token is invalidated
- New refresh token is issued
- Prevents token theft/replay attacks
- Maintains long-lived access without storing long-lived tokens

## Token Revocation Flow

Users or agents can revoke tokens to immediately terminate access.

```
Agent/User            Authorization Server
  │                         │
  │ POST /revoke            │
  │─────────────────────────►│
  │ token={token}           │
  │ token_type_hint=access_token
  │ client_id={id}          │
  │ client_secret={secret}  │
  │                         │
  │                         │ 1. Validate client
  │                         │ 2. Identify token
  │                         │ 3. Mark as revoked
  │                         │ 4. Invalidate related tokens
  │                         │
  │ 200 OK                  │
  │◄─────────────────────────│
```

**Request**:
```http
POST /revoke
Content-Type: application/x-www-form-urlencoded
Authorization: Basic base64(client_id:client_secret)

token=eyJhbGciOiJSUzI1NiIs...
&token_type_hint=access_token
```

**Revocation Effects**:
- **Access Token Revocation**: Immediate effect (if resource server checks revocation)
- **Refresh Token Revocation**: Prevents new access tokens from being issued
- **Cascade Revocation**: Revoking refresh token also revokes associated access tokens

## Error Handling

### Authorization Errors

**Invalid Request**:
```http
HTTP/1.1 302 Found
Location: https://agent.example.com/callback?error=invalid_request
  &error_description=Missing+required+parameter+scope
  &state=xyz123
```

**Access Denied**:
```http
HTTP/1.1 302 Found
Location: https://agent.example.com/callback?error=access_denied
  &error_description=User+denied+authorization
  &state=xyz123
```

### Token Errors

**Invalid Grant**:
```json
{
  "error": "invalid_grant",
  "error_description": "Authorization code has expired or already been used"
}
```

**Invalid Client**:
```json
{
  "error": "invalid_client",
  "error_description": "Client authentication failed"
}
```

### Resource Access Errors

**Invalid Token**:
```http
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer error="invalid_token",
  error_description="Token signature verification failed"
```

**Insufficient Scope**:
```http
HTTP/1.1 403 Forbidden
WWW-Authenticate: Bearer error="insufficient_scope",
  error_description="Token lacks required scope: write:documents",
  scope="write:documents"
```

## Security Considerations

### PKCE (Proof Key for Code Exchange)

PKCE prevents authorization code interception attacks.

**Flow**:
1. Agent generates random `code_verifier` (43-128 characters)
2. Agent calculates `code_challenge = BASE64URL(SHA256(code_verifier))`
3. Agent sends `code_challenge` in authorization request
4. Agent sends `code_verifier` in token request
5. Server verifies `SHA256(code_verifier) == code_challenge`

### State Parameter

Prevents CSRF attacks by ensuring the callback is from a legitimate authorization request.

**Best Practices**:
- Generate cryptographically random state (16+ bytes)
- Store state in session before redirect
- Validate state matches upon callback
- Single-use state values

### Token Security

**Access Token**:
- Short lifetime (1 hour recommended)
- Transmitted only over HTTPS
- Never logged or exposed in URLs
- JWT signature prevents tampering

**Refresh Token**:
- Longer lifetime (30 days recommended)
- Stored securely (encrypted at rest)
- Rotation on each use
- Bound to specific client

### Scope Security

- **Principle of Least Privilege**: Request only necessary scopes
- **Granular Scopes**: Avoid broad permissions
- **User Education**: Clear descriptions of scope implications
- **Revocation UI**: Easy way for users to revoke access

## Compliance and Standards

This implementation follows:

- **OAuth 2.1** (Draft): Incorporates best practices and security enhancements
- **RFC 6749**: OAuth 2.0 Authorization Framework
- **RFC 7009**: Token Revocation
- **RFC 7636**: PKCE
- **RFC 8252**: OAuth for Native Apps (principles applied)

## Common Scenarios

### Scenario 1: First-Time Authorization

User has never authorized this agent before.

1. User requests agent action
2. Agent has no token → Initiates full flow
3. User logs in and grants consent
4. Agent receives tokens
5. Agent completes action

### Scenario 2: Returning User

User has previously authorized this agent.

1. User requests agent action
2. Agent has valid token → Uses it directly (skip auth flow)
3. Agent completes action

### Scenario 3: Expired Access Token

Access token has expired, but refresh token is valid.

1. User requests agent action
2. Agent has expired access token
3. Agent uses refresh token to get new access token
4. Agent uses new access token
5. Agent completes action

### Scenario 4: User Revokes Access

User revokes agent access mid-session.

1. Agent attempts to access resource
2. Resource server validates token → Finds it revoked
3. Resource server returns 401 Unauthorized
4. Agent detects revocation
5. Agent notifies user that re-authorization is needed

### Scenario 5: Scope Escalation

Agent needs additional permissions for new feature.

1. User requests new agent action requiring new scope
2. Agent checks current scopes → Insufficient
3. Agent initiates new authorization request with additional scopes
4. User sees existing scopes + new scope request
5. User grants additional permission
6. Agent receives token with expanded scopes
7. Agent completes action
