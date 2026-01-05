# System Architecture

## Overview

The OAuth 2.1 Agent Authentication Flow system consists of four primary components that work together to enable secure, delegated access for AI agents acting on behalf of users.

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          User (Resource Owner)                   │
│                   Authenticates & Grants Consent                 │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   │ 1. Authentication
                   │ 2. Authorization Grant
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Authorization Server                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Components:                                               │  │
│  │ • User Authentication Service                            │  │
│  │ • Agent Registration & Management                        │  │
│  │ • Authorization Endpoint                                 │  │
│  │ • Token Endpoint                                         │  │
│  │ • Token Revocation Endpoint                              │  │
│  │ • Consent Management                                     │  │
│  │ • Scope Validation                                       │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────┬───────────────────────────────────────────────┬────────┘
         │                                               │
         │ 3. Authorization Code                         │
         │                                               │
         ▼                                               │
┌─────────────────────────────────┐                     │
│       Agent Client (AI Agent)    │                     │
│  ┌───────────────────────────┐  │                     │
│  │ • Authorization Request   │  │                     │
│  │ • Token Management        │  │                     │
│  │ • Refresh Token Handler   │  │                     │
│  │ • API Request Handler     │  │                     │
│  └───────────────────────────┘  │                     │
└────────┬────────────────────────┘                     │
         │                                               │
         │ 4. Access Token Request                       │
         │ 5. Access Token + Refresh Token               │
         └───────────────────────────────────────────────┘
         │
         │ 6. API Request + Access Token
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Resource Server                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Components:                                               │  │
│  │ • Token Validation Middleware                            │  │
│  │ • Scope Verification                                     │  │
│  │ • Protected Resource Endpoints                           │  │
│  │ • Audit Logging                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │
         │ 7. Protected Resource Response
         ▼
┌─────────────────────────────────┐
│       Agent Client (AI Agent)    │
└─────────────────────────────────┘
```

## Component Details

### 1. Authorization Server

**Responsibility**: Central authority for authentication, authorization, and token management.

**Key Functions**:
- User authentication and session management
- Agent registration and credential management
- Authorization code generation and validation
- Access token and refresh token issuance
- Token revocation and invalidation
- Consent storage and retrieval
- Scope management and validation

**Technology Stack**:
- Flask web framework
- SQLite database
- JWT for token encoding
- cryptography library for secure operations

**Endpoints**:
- `POST /register/user` - User registration
- `POST /register/agent` - Agent registration
- `GET /authorize` - Authorization request (user consent)
- `POST /token` - Token issuance and refresh
- `POST /revoke` - Token revocation
- `GET /introspect` - Token introspection (optional)

### 2. Resource Server

**Responsibility**: Host protected resources and validate access tokens.

**Key Functions**:
- Access token validation
- Scope-based authorization
- Protected resource access control
- Audit logging of access attempts
- Rate limiting and abuse prevention

**Technology Stack**:
- Flask web framework
- JWT verification
- Shared secret or public key verification with auth server

**Endpoints**:
- `GET /api/user/profile` - User profile (requires `read:profile` scope)
- `GET /api/user/documents` - User documents (requires `read:documents` scope)
- `POST /api/user/documents` - Create document (requires `write:documents` scope)
- `DELETE /api/user/documents/:id` - Delete document (requires `delete:documents` scope)

### 3. Agent Client

**Responsibility**: AI agent that accesses resources on behalf of users.

**Key Functions**:
- Initiates authorization flow
- Manages authorization codes
- Requests and stores tokens
- Refreshes expired access tokens
- Makes authenticated API requests
- Handles token revocation

**Technology Stack**:
- Python client library
- Requests library for HTTP communication
- Secure token storage

**Example Agents**:
- Document processing agent
- Email management agent
- Calendar scheduling agent
- Data analysis agent

### 4. Database (SQLite)

**Responsibility**: Persistent storage for all system entities.

**Tables**:
- `users` - User accounts and credentials
- `agents` - Registered agent clients
- `authorization_codes` - Temporary authorization codes
- `access_tokens` - Issued access tokens
- `refresh_tokens` - Issued refresh tokens
- `consents` - User-granted permissions to agents
- `scopes` - Available permission scopes
- `audit_logs` - Access and security audit trail

## Security Architecture

### Authentication Layers

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: User Authentication (Authorization Server)         │
│ • Username/password                                         │
│ • Session management                                        │
│ • Multi-factor authentication (future)                      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Agent Authentication (Authorization Server)        │
│ • Client ID + Client Secret                                 │
│ • Certificate-based authentication (future)                 │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Token-based Authorization (Resource Server)        │
│ • JWT access token validation                               │
│ • Signature verification                                    │
│ • Expiration checking                                       │
│ • Scope validation                                          │
└─────────────────────────────────────────────────────────────┘
```

### Token Lifecycle

```
┌──────────────┐
│ Authorization│
│     Code     │
│  (Short-lived│
│   5 minutes) │
└──────┬───────┘
       │ Exchange
       ▼
┌──────────────────────────────────────┐
│         Access Token                 │
│      (Short-lived: 1 hour)           │
│  • JWT with user & agent identity    │
│  • Scopes embedded                   │
│  • Signature for verification        │
└──────┬───────────────────────────────┘
       │
       │ Expires
       ▼
┌──────────────────────────────────────┐
│        Refresh Token                 │
│     (Long-lived: 30 days)            │
│  • Opaque token                      │
│  • Stored in database                │
│  • Can be revoked                    │
│  • One-time use with rotation        │
└──────┬───────────────────────────────┘
       │ Use to get new access token
       ▼
┌──────────────────────────────────────┐
│      New Access Token                │
│   + New Refresh Token (rotation)     │
└──────────────────────────────────────┘
```

## Data Flow

### Complete Authorization Flow

```
User          Agent Client    Auth Server    Resource Server
  │                │               │                │
  │                │               │                │
  │◄───Request────►│               │                │
  │  Authorization │               │                │
  │                │               │                │
  │                │──Register────►│                │
  │                │  Agent Info   │                │
  │                │◄──Client ID───│                │
  │                │   + Secret    │                │
  │                │               │                │
  │                │──Auth Req────►│                │
  │                │  redirect_uri │                │
  │                │  scopes       │                │
  │                │               │                │
  │◄───Redirect────────────────────│                │
  │   Login Page                   │                │
  │                                │                │
  │──Login Creds──────────────────►│                │
  │  username/password             │                │
  │                                │                │
  │◄───Consent Page────────────────│                │
  │  Agent requests:               │                │
  │  • read:profile                │                │
  │  • write:documents             │                │
  │                                │                │
  │──Grant Consent─────────────────►│                │
  │                                │                │
  │                │◄──Auth Code───│                │
  │                │   via redirect│                │
  │                │               │                │
  │                │──Token Req───►│                │
  │                │  auth code    │                │
  │                │  client creds │                │
  │                │               │                │
  │                │◄──Tokens──────│                │
  │                │  access_token │                │
  │                │  refresh_token│                │
  │                │  expires_in   │                │
  │                │               │                │
  │                │───API Request────────────────►│
  │                │   + access_token              │
  │                │                               │
  │                │               │◄──Validate────│
  │                │               │   Token       │
  │                │               │               │
  │                │               │──Token Info──►│
  │                │               │  user_id      │
  │                │               │  scopes       │
  │                │               │               │
  │                │◄──Protected Resource──────────│
  │                │   (if authorized)             │
  │                │                               │
```

## Scope Management

### Scope Hierarchy

```
Root Scopes:
├── user
│   ├── read:profile        (Read user profile information)
│   ├── write:profile       (Update user profile)
│   └── delete:account      (Delete user account)
│
├── documents
│   ├── read:documents      (View documents)
│   ├── write:documents     (Create/update documents)
│   ├── delete:documents    (Delete documents)
│   └── share:documents     (Share documents with others)
│
├── calendar
│   ├── read:calendar       (View calendar events)
│   ├── write:calendar      (Create/update events)
│   └── delete:calendar     (Delete events)
│
└── email
    ├── read:email          (Read emails)
    ├── send:email          (Send emails)
    └── delete:email        (Delete emails)
```

### Scope Validation Rules

1. **Granular Permissions**: Each scope represents a specific permission
2. **No Wildcards**: Explicit scope grant required (no `*` or broad access)
3. **User Consent Required**: User must explicitly grant each scope
4. **Revocable**: Users can revoke scopes at any time
5. **Token-Scoped**: Access tokens only contain granted scopes

## Deployment Architecture

### Development Environment

```
┌────────────────────────────────────────┐
│         Single Machine (localhost)      │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │ Auth Server     (port 5000)      │ │
│  └──────────────────────────────────┘ │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │ Resource Server (port 5001)      │ │
│  └──────────────────────────────────┘ │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │ SQLite Database (file-based)     │ │
│  └──────────────────────────────────┘ │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │ Agent Client    (CLI/Script)     │ │
│  └──────────────────────────────────┘ │
└────────────────────────────────────────┘
```

### Production-Ready Architecture (Future)

```
┌─────────────────────────────────────────────────────────┐
│                      Load Balancer                       │
└──────────────┬─────────────────────┬────────────────────┘
               │                     │
               ▼                     ▼
┌──────────────────────┐  ┌──────────────────────┐
│  Auth Server (x2)    │  │ Resource Server (x2) │
│  (Containerized)     │  │  (Containerized)     │
└──────────┬───────────┘  └──────────┬───────────┘
           │                         │
           └────────┬────────────────┘
                    ▼
           ┌─────────────────┐
           │   PostgreSQL    │
           │   (Clustered)   │
           └─────────────────┘
```

## Performance Considerations

### Token Validation Strategy

**Stateless JWT Validation** (Recommended for PoC):
- No database lookup required for each request
- Fast validation using cryptographic signatures
- Tradeoff: Cannot instantly revoke without blacklist

**Stateful Token Validation** (Optional):
- Database lookup for each request
- Instant revocation capability
- Tradeoff: Higher latency, database load

### Caching Strategy

```
┌─────────────────────────────────────────┐
│         Resource Server                 │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │  Token Cache (In-Memory)          │ │
│  │  • Cache validated tokens (1 min) │ │
│  │  • Reduce auth server calls       │ │
│  └───────────────────────────────────┘ │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │  Scope Cache                      │ │
│  │  • Cache scope definitions        │ │
│  │  • Refresh periodically           │ │
│  └───────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

## Scalability Considerations

### Horizontal Scaling

- **Stateless Design**: Authorization and resource servers are stateless
- **Session Storage**: Use Redis for distributed session management (future)
- **Database Connection Pooling**: Efficient database connection management
- **Load Balancing**: Round-robin or least-connections strategy

### Database Scaling

- **Read Replicas**: Separate read and write operations
- **Connection Pooling**: Limit concurrent database connections
- **Indexing**: Proper indexes on frequently queried columns
- **Partitioning**: Partition large tables (tokens, audit logs) by date

## Monitoring and Observability

### Key Metrics

1. **Authorization Server**:
   - Token issuance rate
   - Token refresh rate
   - Failed authentication attempts
   - Average response time

2. **Resource Server**:
   - Request rate per endpoint
   - Unauthorized access attempts
   - Average response time
   - Error rate

3. **Database**:
   - Query performance
   - Connection pool utilization
   - Storage usage

### Audit Logging

All security-relevant events are logged:
- User authentication (success/failure)
- Agent registration
- Authorization grants (consent)
- Token issuance/refresh/revocation
- Resource access attempts
- Scope violations

## Security Hardening

### PoC Security Features

✅ Implemented:
- Password hashing (bcrypt/argon2)
- Secure token generation (secrets module)
- JWT signature verification
- HTTPS redirect (for production)
- SQL injection prevention (parameterized queries)

### Production Security Requirements

🔲 Additional Requirements:
- HTTPS/TLS enforcement
- CSRF protection
- Rate limiting (per IP, per user, per agent)
- Brute force protection
- DDoS mitigation
- Input validation and sanitization
- Security headers (HSTS, CSP, etc.)
- Regular security audits
- Dependency vulnerability scanning

## Future Enhancements

### Phase 2 Features

- **PKCE Support**: Proof Key for Code Exchange for public clients
- **Multi-factor Authentication**: TOTP, SMS, or hardware keys
- **OpenID Connect**: Add identity layer on top of OAuth
- **Dynamic Client Registration**: Automated agent registration
- **Token Introspection**: RFC 7662 compliant endpoint
- **JWT Key Rotation**: Automatic signing key rotation

### Phase 3 Features

- **Federated Identity**: Support for external identity providers
- **Fine-grained Authorization**: Attribute-based access control (ABAC)
- **Webhook Support**: Real-time notifications for events
- **Analytics Dashboard**: Usage statistics and insights
- **Mobile SDK**: Native iOS and Android support
