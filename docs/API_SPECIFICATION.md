# API Specification

## Overview

This document provides complete API specifications for the OAuth 2.1 Agent Authentication Flow system, including all endpoints for the Authorization Server and Resource Server.

## Base URLs

- **Authorization Server**: `http://localhost:5000` (development)
- **Resource Server**: `http://localhost:5001` (development)

## Common Headers

### Request Headers

```http
Content-Type: application/json
Accept: application/json
Authorization: Bearer {access_token}  # For protected endpoints
```

### Response Headers

```http
Content-Type: application/json
Cache-Control: no-store
Pragma: no-cache
```

## Error Response Format

All error responses follow this structure:

```json
{
  "error": "error_code",
  "error_description": "Human-readable description",
  "error_uri": "https://docs.example.com/errors/error_code"  // Optional
}
```

## Authorization Server API

### 1. User Registration

Register a new user account.

**Endpoint**: `POST /register/user`

**Request**:
```http
POST /register/user HTTP/1.1
Host: localhost:5000
Content-Type: application/json

{
  "username": "john.doe@example.com",
  "password": "SecurePassword123!",
  "email": "john.doe@example.com",
  "full_name": "John Doe"
}
```

**Request Parameters**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| username | string | Yes | Unique username (email format recommended) |
| password | string | Yes | Password (min 8 chars, must include uppercase, lowercase, number) |
| email | string | Yes | User's email address |
| full_name | string | Yes | User's full name |

**Success Response** (201 Created):
```json
{
  "user_id": "user_123",
  "username": "john.doe@example.com",
  "email": "john.doe@example.com",
  "full_name": "John Doe",
  "created_at": "2026-01-05T10:00:00Z"
}
```

**Error Responses**:

400 Bad Request:
```json
{
  "error": "invalid_request",
  "error_description": "Password must be at least 8 characters"
}
```

409 Conflict:
```json
{
  "error": "user_exists",
  "error_description": "Username already registered"
}
```

---

### 2. Agent Registration

Register a new agent client.

**Endpoint**: `POST /register/agent`

**Request**:
```http
POST /register/agent HTTP/1.1
Host: localhost:5000
Content-Type: application/json

{
  "agent_name": "Document Analyzer",
  "description": "AI agent for document analysis and summarization",
  "redirect_uris": [
    "https://agent.example.com/callback",
    "http://localhost:8080/callback"
  ],
  "homepage_url": "https://agent.example.com",
  "privacy_policy_url": "https://agent.example.com/privacy"
}
```

**Request Parameters**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| agent_name | string | Yes | Human-readable agent name |
| description | string | Yes | Description of agent's purpose |
| redirect_uris | array | Yes | List of valid redirect URIs |
| homepage_url | string | No | Agent's homepage |
| privacy_policy_url | string | No | Privacy policy URL |

**Success Response** (201 Created):
```json
{
  "client_id": "agent_abc123",
  "client_secret": "secret_xyz789_KEEP_THIS_SECURE",
  "agent_name": "Document Analyzer",
  "description": "AI agent for document analysis and summarization",
  "redirect_uris": [
    "https://agent.example.com/callback",
    "http://localhost:8080/callback"
  ],
  "created_at": "2026-01-05T10:00:00Z"
}
```

**Important**: The `client_secret` is only shown once. Store it securely.

**Error Responses**:

400 Bad Request:
```json
{
  "error": "invalid_request",
  "error_description": "redirect_uris must contain at least one URI"
}
```

---

### 3. User Login

Authenticate a user and create a session.

**Endpoint**: `POST /login`

**Request**:
```http
POST /login HTTP/1.1
Host: localhost:5000
Content-Type: application/json

{
  "username": "john.doe@example.com",
  "password": "SecurePassword123!"
}
```

**Request Parameters**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| username | string | Yes | User's username |
| password | string | Yes | User's password |

**Success Response** (200 OK):
```json
{
  "session_id": "session_abc123",
  "user_id": "user_123",
  "username": "john.doe@example.com",
  "expires_at": "2026-01-05T11:00:00Z"
}
```

**Set-Cookie Header**:
```http
Set-Cookie: session_id=session_abc123; HttpOnly; Secure; SameSite=Lax; Max-Age=3600
```

**Error Responses**:

401 Unauthorized:
```json
{
  "error": "invalid_credentials",
  "error_description": "Invalid username or password"
}
```

429 Too Many Requests:
```json
{
  "error": "rate_limit_exceeded",
  "error_description": "Too many login attempts. Please try again in 15 minutes."
}
```

---

### 4. Authorization Endpoint

Request user authorization for an agent.

**Endpoint**: `GET /authorize`

**Request**:
```http
GET /authorize?response_type=code
  &client_id=agent_abc123
  &redirect_uri=https://agent.example.com/callback
  &scope=read:profile read:documents
  &state=random_state_xyz
  &code_challenge=E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM
  &code_challenge_method=S256
HTTP/1.1
Host: localhost:5000
Cookie: session_id=session_abc123
```

**Query Parameters**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| response_type | string | Yes | Must be "code" |
| client_id | string | Yes | Registered agent client ID |
| redirect_uri | string | Yes | Must match registered redirect URI |
| scope | string | Yes | Space-separated list of scopes |
| state | string | Yes | Random string for CSRF protection |
| code_challenge | string | No | PKCE code challenge (recommended) |
| code_challenge_method | string | No | Must be "S256" if code_challenge provided |

**User Not Authenticated Response** (302 Redirect):
```http
HTTP/1.1 302 Found
Location: /login?redirect=/authorize?response_type=code&client_id=...
```

**User Authenticated - Show Consent Screen** (200 OK):
```html
<!DOCTYPE html>
<html>
<head><title>Authorization Request</title></head>
<body>
  <h1>Authorization Request</h1>
  <p><strong>Document Analyzer</strong> wants to:</p>
  <ul>
    <li>Read your profile information</li>
    <li>Access your documents</li>
  </ul>
  <form method="POST" action="/authorize/consent">
    <input type="hidden" name="client_id" value="agent_abc123">
    <input type="hidden" name="redirect_uri" value="https://agent.example.com/callback">
    <input type="hidden" name="scope" value="read:profile read:documents">
    <input type="hidden" name="state" value="random_state_xyz">
    <input type="hidden" name="code_challenge" value="...">
    <button type="submit" name="approved" value="true">Allow</button>
    <button type="submit" name="approved" value="false">Deny</button>
  </form>
</body>
</html>
```

**Error Responses**:

400 Bad Request (Redirect to redirect_uri):
```http
HTTP/1.1 302 Found
Location: https://agent.example.com/callback?error=invalid_request
  &error_description=Missing+required+parameter+scope
  &state=random_state_xyz
```

---

### 5. Authorization Consent

User approves or denies authorization request.

**Endpoint**: `POST /authorize/consent`

**Request**:
```http
POST /authorize/consent HTTP/1.1
Host: localhost:5000
Content-Type: application/x-www-form-urlencoded
Cookie: session_id=session_abc123

client_id=agent_abc123
&redirect_uri=https://agent.example.com/callback
&scope=read:profile read:documents
&state=random_state_xyz
&code_challenge=E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM
&approved=true
```

**Request Parameters**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| client_id | string | Yes | Agent client ID |
| redirect_uri | string | Yes | Redirect URI |
| scope | string | Yes | Requested scopes |
| state | string | Yes | CSRF token |
| code_challenge | string | No | PKCE challenge |
| approved | boolean | Yes | User's decision (true/false) |

**Success Response - Approved** (302 Redirect):
```http
HTTP/1.1 302 Found
Location: https://agent.example.com/callback?code=auth_code_123&state=random_state_xyz
```

**Success Response - Denied** (302 Redirect):
```http
HTTP/1.1 302 Found
Location: https://agent.example.com/callback?error=access_denied
  &error_description=User+denied+authorization
  &state=random_state_xyz
```

---

### 6. Token Endpoint

Exchange authorization code for tokens or refresh an access token.

**Endpoint**: `POST /token`

#### 6.1 Authorization Code Grant

**Request**:
```http
POST /token HTTP/1.1
Host: localhost:5000
Content-Type: application/x-www-form-urlencoded
Authorization: Basic YWdlbnRfYWJjMTIzOnNlY3JldF94eXo3ODk=

grant_type=authorization_code
&code=auth_code_123
&redirect_uri=https://agent.example.com/callback
&code_verifier=dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk
```

**Authorization Header**:
```
Basic base64(client_id:client_secret)
```

**Request Parameters**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| grant_type | string | Yes | Must be "authorization_code" |
| code | string | Yes | Authorization code from Step 5 |
| redirect_uri | string | Yes | Must match original request |
| code_verifier | string | No | PKCE verifier (required if PKCE used) |

**Success Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "refresh_abc123xyz",
  "scope": "read:profile read:documents"
}
```

**Response Fields**:
| Field | Type | Description |
|-------|------|-------------|
| access_token | string | JWT access token |
| token_type | string | Always "Bearer" |
| expires_in | integer | Token lifetime in seconds |
| refresh_token | string | Refresh token for getting new access tokens |
| scope | string | Granted scopes (may differ from requested) |

**Error Responses**:

400 Bad Request:
```json
{
  "error": "invalid_request",
  "error_description": "Missing required parameter: code"
}
```

401 Unauthorized:
```json
{
  "error": "invalid_client",
  "error_description": "Client authentication failed"
}
```

400 Bad Request:
```json
{
  "error": "invalid_grant",
  "error_description": "Authorization code has expired or already been used"
}
```

#### 6.2 Refresh Token Grant

**Request**:
```http
POST /token HTTP/1.1
Host: localhost:5000
Content-Type: application/x-www-form-urlencoded
Authorization: Basic YWdlbnRfYWJjMTIzOnNlY3JldF94eXo3ODk=

grant_type=refresh_token
&refresh_token=refresh_abc123xyz
```

**Request Parameters**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| grant_type | string | Yes | Must be "refresh_token" |
| refresh_token | string | Yes | Refresh token from previous token response |

**Success Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "refresh_new_456def",
  "scope": "read:profile read:documents"
}
```

**Note**: The old refresh token is invalidated and a new one is issued (token rotation).

**Error Responses**:

400 Bad Request:
```json
{
  "error": "invalid_grant",
  "error_description": "Refresh token has expired or been revoked"
}
```

---

### 7. Token Revocation

Revoke an access token or refresh token.

**Endpoint**: `POST /revoke`

**Request**:
```http
POST /revoke HTTP/1.1
Host: localhost:5000
Content-Type: application/x-www-form-urlencoded
Authorization: Basic YWdlbnRfYWJjMTIzOnNlY3JldF94eXo3ODk=

token=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
&token_type_hint=access_token
```

**Request Parameters**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| token | string | Yes | Token to revoke |
| token_type_hint | string | No | "access_token" or "refresh_token" (helps server optimize) |

**Success Response** (200 OK):
```json
{
  "revoked": true
}
```

**Note**: Response is always 200 OK, even if token doesn't exist (per OAuth spec).

---

### 8. Token Introspection (Optional)

Check if a token is active and retrieve metadata.

**Endpoint**: `POST /introspect`

**Request**:
```http
POST /introspect HTTP/1.1
Host: localhost:5000
Content-Type: application/x-www-form-urlencoded
Authorization: Basic cmVzb3VyY2Vfc2VydmVyOnJlc291cmNlX3NlY3JldA==

token=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
&token_type_hint=access_token
```

**Request Parameters**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| token | string | Yes | Token to introspect |
| token_type_hint | string | No | "access_token" or "refresh_token" |

**Success Response - Active Token** (200 OK):
```json
{
  "active": true,
  "scope": "read:profile read:documents",
  "client_id": "agent_abc123",
  "username": "john.doe@example.com",
  "token_type": "Bearer",
  "exp": 1704452400,
  "iat": 1704448800,
  "sub": "user_123",
  "aud": "https://api.example.com"
}
```

**Success Response - Inactive Token** (200 OK):
```json
{
  "active": false
}
```

---

### 9. List User Consents

List all active consent grants for a user.

**Endpoint**: `GET /user/consents`

**Authentication**: Required (user session)

**Request**:
```http
GET /user/consents HTTP/1.1
Host: localhost:5000
Cookie: session_id=session_abc123
```

**Success Response** (200 OK):
```json
{
  "consents": [
    {
      "consent_id": "consent_123",
      "agent_id": "agent_abc123",
      "agent_name": "Document Analyzer",
      "scopes": ["read:profile", "read:documents"],
      "granted_at": "2026-01-05T10:00:00Z",
      "last_used": "2026-01-05T12:30:00Z"
    },
    {
      "consent_id": "consent_456",
      "agent_id": "agent_def456",
      "agent_name": "Email Assistant",
      "scopes": ["read:email", "send:email"],
      "granted_at": "2026-01-04T08:00:00Z",
      "last_used": "2026-01-05T09:15:00Z"
    }
  ]
}
```

---

### 10. Revoke Consent

Revoke all access for an agent.

**Endpoint**: `POST /user/consents/{consent_id}/revoke`

**Authentication**: Required (user session)

**Request**:
```http
POST /user/consents/consent_123/revoke HTTP/1.1
Host: localhost:5000
Cookie: session_id=session_abc123
```

**Success Response** (200 OK):
```json
{
  "revoked": true,
  "consent_id": "consent_123",
  "tokens_revoked": 2
}
```

**Error Responses**:

404 Not Found:
```json
{
  "error": "consent_not_found",
  "error_description": "No consent found with this ID"
}
```

---

## Resource Server API

### 1. Get User Profile

Retrieve authenticated user's profile information.

**Endpoint**: `GET /api/user/profile`

**Required Scope**: `read:profile`

**Request**:
```http
GET /api/user/profile HTTP/1.1
Host: localhost:5001
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Success Response** (200 OK):
```json
{
  "user_id": "user_123",
  "username": "john.doe@example.com",
  "email": "john.doe@example.com",
  "full_name": "John Doe",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2026-01-05T10:00:00Z"
}
```

**Error Responses**:

401 Unauthorized:
```http
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer error="invalid_token"

{
  "error": "invalid_token",
  "error_description": "Token has expired"
}
```

403 Forbidden:
```http
HTTP/1.1 403 Forbidden
WWW-Authenticate: Bearer error="insufficient_scope", scope="read:profile"

{
  "error": "insufficient_scope",
  "error_description": "Token lacks required scope: read:profile"
}
```

---

### 2. Update User Profile

Update authenticated user's profile information.

**Endpoint**: `PATCH /api/user/profile`

**Required Scope**: `write:profile`

**Request**:
```http
PATCH /api/user/profile HTTP/1.1
Host: localhost:5001
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "full_name": "Jonathan Doe",
  "email": "jonathan.doe@example.com"
}
```

**Success Response** (200 OK):
```json
{
  "user_id": "user_123",
  "username": "john.doe@example.com",
  "email": "jonathan.doe@example.com",
  "full_name": "Jonathan Doe",
  "updated_at": "2026-01-05T13:00:00Z"
}
```

---

### 3. List Documents

List user's documents.

**Endpoint**: `GET /api/user/documents`

**Required Scope**: `read:documents`

**Request**:
```http
GET /api/user/documents?limit=10&offset=0 HTTP/1.1
Host: localhost:5001
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Query Parameters**:
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| limit | integer | No | 20 | Number of results (max 100) |
| offset | integer | No | 0 | Pagination offset |

**Success Response** (200 OK):
```json
{
  "documents": [
    {
      "document_id": "doc_123",
      "title": "Project Proposal",
      "content": "Lorem ipsum...",
      "created_at": "2026-01-03T10:00:00Z",
      "updated_at": "2026-01-04T15:30:00Z"
    },
    {
      "document_id": "doc_456",
      "title": "Meeting Notes",
      "content": "Discussion points...",
      "created_at": "2026-01-02T14:00:00Z",
      "updated_at": "2026-01-02T14:00:00Z"
    }
  ],
  "total": 25,
  "limit": 10,
  "offset": 0
}
```

---

### 4. Get Single Document

Retrieve a specific document.

**Endpoint**: `GET /api/user/documents/{document_id}`

**Required Scope**: `read:documents`

**Request**:
```http
GET /api/user/documents/doc_123 HTTP/1.1
Host: localhost:5001
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Success Response** (200 OK):
```json
{
  "document_id": "doc_123",
  "title": "Project Proposal",
  "content": "Lorem ipsum dolor sit amet...",
  "created_at": "2026-01-03T10:00:00Z",
  "updated_at": "2026-01-04T15:30:00Z",
  "tags": ["project", "proposal", "2026"]
}
```

**Error Responses**:

404 Not Found:
```json
{
  "error": "document_not_found",
  "error_description": "Document does not exist or you don't have access"
}
```

---

### 5. Create Document

Create a new document.

**Endpoint**: `POST /api/user/documents`

**Required Scope**: `write:documents`

**Request**:
```http
POST /api/user/documents HTTP/1.1
Host: localhost:5001
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "title": "New Document",
  "content": "Document content here...",
  "tags": ["draft", "2026"]
}
```

**Success Response** (201 Created):
```json
{
  "document_id": "doc_789",
  "title": "New Document",
  "content": "Document content here...",
  "created_at": "2026-01-05T13:00:00Z",
  "updated_at": "2026-01-05T13:00:00Z",
  "tags": ["draft", "2026"]
}
```

---

### 6. Update Document

Update an existing document.

**Endpoint**: `PATCH /api/user/documents/{document_id}`

**Required Scope**: `write:documents`

**Request**:
```http
PATCH /api/user/documents/doc_123 HTTP/1.1
Host: localhost:5001
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "title": "Updated Title",
  "content": "Updated content..."
}
```

**Success Response** (200 OK):
```json
{
  "document_id": "doc_123",
  "title": "Updated Title",
  "content": "Updated content...",
  "created_at": "2026-01-03T10:00:00Z",
  "updated_at": "2026-01-05T13:30:00Z",
  "tags": ["project", "proposal", "2026"]
}
```

---

### 7. Delete Document

Delete a document.

**Endpoint**: `DELETE /api/user/documents/{document_id}`

**Required Scope**: `delete:documents`

**Request**:
```http
DELETE /api/user/documents/doc_123 HTTP/1.1
Host: localhost:5001
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Success Response** (204 No Content):
```http
HTTP/1.1 204 No Content
```

---

## Rate Limiting

All endpoints are subject to rate limiting to prevent abuse.

**Rate Limit Headers**:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1704452400
```

**Rate Limit Exceeded** (429 Too Many Requests):
```json
{
  "error": "rate_limit_exceeded",
  "error_description": "API rate limit exceeded. Try again in 60 seconds.",
  "retry_after": 60
}
```

**Default Rate Limits**:
- Authentication endpoints: 10 requests/minute per IP
- Authorization endpoints: 20 requests/minute per user
- Token endpoints: 30 requests/minute per client
- Resource endpoints: 100 requests/minute per token

---

## Webhook Events (Future)

Notify agents of important events.

**Event Types**:
- `consent.granted` - User grants new consent
- `consent.revoked` - User revokes consent
- `token.revoked` - Token is revoked
- `scope.changed` - Consent scopes are modified

**Webhook Payload**:
```json
{
  "event_id": "evt_123",
  "event_type": "consent.revoked",
  "timestamp": "2026-01-05T13:00:00Z",
  "data": {
    "user_id": "user_123",
    "client_id": "agent_abc123",
    "consent_id": "consent_123"
  }
}
```

---

## Appendix: Scope Definitions

| Scope | Description | Resource Endpoints |
|-------|-------------|-------------------|
| `read:profile` | Read user profile information | `GET /api/user/profile` |
| `write:profile` | Update user profile | `PATCH /api/user/profile` |
| `delete:account` | Delete user account | `DELETE /api/user/account` |
| `read:documents` | View user documents | `GET /api/user/documents`, `GET /api/user/documents/{id}` |
| `write:documents` | Create/update documents | `POST /api/user/documents`, `PATCH /api/user/documents/{id}` |
| `delete:documents` | Delete documents | `DELETE /api/user/documents/{id}` |
| `read:email` | Read emails | `GET /api/user/emails` |
| `send:email` | Send emails | `POST /api/user/emails` |
| `read:calendar` | View calendar events | `GET /api/user/calendar` |
| `write:calendar` | Create/update events | `POST /api/user/calendar` |

---

## Testing with cURL

### Complete Flow Example

**1. Register User**:
```bash
curl -X POST http://localhost:5000/register/user \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test@example.com",
    "password": "SecurePass123!",
    "email": "test@example.com",
    "full_name": "Test User"
  }'
```

**2. Register Agent**:
```bash
curl -X POST http://localhost:5000/register/agent \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "Test Agent",
    "description": "Testing agent",
    "redirect_uris": ["http://localhost:8080/callback"]
  }'
```

**3. Get Authorization URL** (manual - visit in browser):
```
http://localhost:5000/authorize?response_type=code&client_id={CLIENT_ID}&redirect_uri=http://localhost:8080/callback&scope=read:profile&state=test123
```

**4. Exchange Code for Token**:
```bash
curl -X POST http://localhost:5000/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -u "CLIENT_ID:CLIENT_SECRET" \
  -d "grant_type=authorization_code&code={AUTH_CODE}&redirect_uri=http://localhost:8080/callback"
```

**5. Access Resource**:
```bash
curl http://localhost:5001/api/user/profile \
  -H "Authorization: Bearer {ACCESS_TOKEN}"
```

**6. Refresh Token**:
```bash
curl -X POST http://localhost:5000/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -u "CLIENT_ID:CLIENT_SECRET" \
  -d "grant_type=refresh_token&refresh_token={REFRESH_TOKEN}"
```

**7. Revoke Token**:
```bash
curl -X POST http://localhost:5000/revoke \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -u "CLIENT_ID:CLIENT_SECRET" \
  -d "token={ACCESS_TOKEN}&token_type_hint=access_token"
```
