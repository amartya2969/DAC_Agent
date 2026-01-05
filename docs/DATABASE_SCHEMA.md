# Database Schema

## Overview

This document describes the complete database schema for the OAuth 2.1 Agent Authentication Flow system. The schema is designed for SQLite but can be easily adapted for PostgreSQL.

## Database Design Principles

- **Normalization**: Tables are normalized to 3NF to minimize redundancy
- **Referential Integrity**: Foreign key constraints ensure data consistency
- **Indexing**: Strategic indexes for performance optimization
- **Soft Deletes**: Critical records use soft deletes (revoked flags) instead of hard deletes
- **Audit Trail**: Timestamps on all tables for audit purposes
- **Security**: Passwords and secrets are hashed; tokens are stored securely

## Entity Relationship Diagram

```
┌─────────────┐
│    Users    │
└──────┬──────┘
       │
       │ 1:N
       │
       ▼
┌─────────────────┐         ┌──────────────┐
│    Consents     │◄───────►│    Agents    │
└────────┬────────┘   N:1   └──────┬───────┘
         │                         │
         │                         │
         │ 1:N                     │ 1:N
         │                         │
         ▼                         ▼
┌──────────────────────┐  ┌──────────────────────┐
│ Authorization Codes  │  │   Access Tokens      │
└──────────────────────┘  └──────────────────────┘
                                    │
                                    │ 1:1
                                    ▼
                          ┌──────────────────────┐
                          │   Refresh Tokens     │
                          └──────────────────────┘

┌─────────────┐
│   Scopes    │ (Reference table)
└─────────────┘

┌─────────────┐
│ Audit Logs  │ (Logging table)
└─────────────┘
```

## Tables

### 1. users

Stores user account information.

```sql
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,                    -- UUID or unique identifier
    username TEXT UNIQUE NOT NULL,               -- Unique username (email)
    email TEXT UNIQUE NOT NULL,                  -- Email address
    password_hash TEXT NOT NULL,                 -- Bcrypt/Argon2 hashed password
    full_name TEXT NOT NULL,                     -- User's full name
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,                        -- Last successful login
    account_status TEXT DEFAULT 'active',        -- active, suspended, deleted
    email_verified BOOLEAN DEFAULT FALSE,        -- Email verification status
    mfa_enabled BOOLEAN DEFAULT FALSE,           -- Multi-factor auth enabled
    mfa_secret TEXT                              -- TOTP secret (if MFA enabled)
);

-- Indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_account_status ON users(account_status);
```

**Sample Data**:
```sql
INSERT INTO users VALUES (
    'user_123e4567-e89b-12d3-a456-426614174000',
    'john.doe@example.com',
    'john.doe@example.com',
    '$2b$12$K7vVY5WZNj9VzQ8hXQ8rJOJYGr8x1Y9wZB7pZ8QZ8QZ8QZ8QZ8QZ8',
    'John Doe',
    '2026-01-01 00:00:00',
    '2026-01-05 10:00:00',
    '2026-01-05 09:30:00',
    'active',
    TRUE,
    FALSE,
    NULL
);
```

---

### 2. agents

Stores registered agent client applications.

```sql
CREATE TABLE agents (
    client_id TEXT PRIMARY KEY,                  -- Unique client identifier
    client_secret_hash TEXT NOT NULL,            -- Hashed client secret
    agent_name TEXT NOT NULL,                    -- Human-readable name
    description TEXT,                            -- Agent description
    homepage_url TEXT,                           -- Agent's homepage
    privacy_policy_url TEXT,                     -- Privacy policy URL
    logo_url TEXT,                               -- Logo/icon URL
    redirect_uris TEXT NOT NULL,                 -- JSON array of redirect URIs
    allowed_scopes TEXT NOT NULL,                -- JSON array of allowed scopes
    agent_type TEXT DEFAULT 'confidential',      -- confidential, public
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active',                -- active, suspended, revoked
    created_by TEXT,                             -- User who registered the agent
    FOREIGN KEY (created_by) REFERENCES users(user_id)
);

-- Indexes
CREATE INDEX idx_agents_status ON agents(status);
CREATE INDEX idx_agents_created_by ON agents(created_by);
```

**Sample Data**:
```sql
INSERT INTO agents VALUES (
    'agent_abc123xyz',
    '$2b$12$hashed_client_secret',
    'Document Analyzer',
    'AI agent for document analysis and summarization',
    'https://agent.example.com',
    'https://agent.example.com/privacy',
    'https://agent.example.com/logo.png',
    '["https://agent.example.com/callback", "http://localhost:8080/callback"]',
    '["read:profile", "read:documents", "write:documents"]',
    'confidential',
    '2026-01-03 10:00:00',
    '2026-01-03 10:00:00',
    'active',
    'user_123e4567-e89b-12d3-a456-426614174000'
);
```

---

### 3. consents

Stores user consent grants to agents.

```sql
CREATE TABLE consents (
    consent_id TEXT PRIMARY KEY,                 -- Unique consent identifier
    user_id TEXT NOT NULL,                       -- User granting consent
    client_id TEXT NOT NULL,                     -- Agent receiving consent
    scopes TEXT NOT NULL,                        -- JSON array of granted scopes
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP,                         -- Last time agent used this consent
    expires_at TIMESTAMP,                        -- Optional expiration
    revoked BOOLEAN DEFAULT FALSE,               -- Revocation status
    revoked_at TIMESTAMP,                        -- When revoked
    revocation_reason TEXT,                      -- Why revoked (user, system, security)
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (client_id) REFERENCES agents(client_id) ON DELETE CASCADE,
    UNIQUE(user_id, client_id)                   -- One consent per user-agent pair
);

-- Indexes
CREATE INDEX idx_consents_user_id ON consents(user_id);
CREATE INDEX idx_consents_client_id ON consents(client_id);
CREATE INDEX idx_consents_revoked ON consents(revoked);
CREATE INDEX idx_consents_user_client ON consents(user_id, client_id);
```

**Sample Data**:
```sql
INSERT INTO consents VALUES (
    'consent_789def456',
    'user_123e4567-e89b-12d3-a456-426614174000',
    'agent_abc123xyz',
    '["read:profile", "read:documents"]',
    '2026-01-05 10:10:00',
    '2026-01-05 10:10:00',
    '2026-01-05 12:30:00',
    NULL,
    FALSE,
    NULL,
    NULL
);
```

---

### 4. authorization_codes

Stores temporary authorization codes.

```sql
CREATE TABLE authorization_codes (
    code TEXT PRIMARY KEY,                       -- Authorization code (unique, random)
    client_id TEXT NOT NULL,                     -- Agent client ID
    user_id TEXT NOT NULL,                       -- User granting authorization
    redirect_uri TEXT NOT NULL,                  -- Redirect URI for this request
    scopes TEXT NOT NULL,                        -- JSON array of requested scopes
    code_challenge TEXT,                         -- PKCE code challenge
    code_challenge_method TEXT,                  -- PKCE method (S256)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,               -- Short expiration (5 minutes)
    used BOOLEAN DEFAULT FALSE,                  -- Has been exchanged for token
    used_at TIMESTAMP,                           -- When it was used
    FOREIGN KEY (client_id) REFERENCES agents(client_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_auth_codes_client_id ON authorization_codes(client_id);
CREATE INDEX idx_auth_codes_user_id ON authorization_codes(user_id);
CREATE INDEX idx_auth_codes_expires_at ON authorization_codes(expires_at);
CREATE INDEX idx_auth_codes_used ON authorization_codes(used);
```

**Sample Data**:
```sql
INSERT INTO authorization_codes VALUES (
    'auth_code_abc123xyz789',
    'agent_abc123xyz',
    'user_123e4567-e89b-12d3-a456-426614174000',
    'https://agent.example.com/callback',
    '["read:profile", "read:documents"]',
    'E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM',
    'S256',
    '2026-01-05 10:10:00',
    '2026-01-05 10:15:00',  -- 5 minutes expiration
    FALSE,
    NULL
);
```

---

### 5. access_tokens

Stores issued access tokens (for tracking and revocation).

```sql
CREATE TABLE access_tokens (
    jti TEXT PRIMARY KEY,                        -- JWT ID (unique token identifier)
    user_id TEXT NOT NULL,                       -- User the token represents
    client_id TEXT NOT NULL,                     -- Agent that owns the token
    scopes TEXT NOT NULL,                        -- JSON array of scopes
    token_hash TEXT NOT NULL,                    -- Hash of the token (for revocation check)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,               -- Token expiration (1 hour typical)
    revoked BOOLEAN DEFAULT FALSE,               -- Revocation status
    revoked_at TIMESTAMP,                        -- When revoked
    revocation_reason TEXT,                      -- Why revoked
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (client_id) REFERENCES agents(client_id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_access_tokens_user_id ON access_tokens(user_id);
CREATE INDEX idx_access_tokens_client_id ON access_tokens(client_id);
CREATE INDEX idx_access_tokens_expires_at ON access_tokens(expires_at);
CREATE INDEX idx_access_tokens_revoked ON access_tokens(revoked);
CREATE INDEX idx_access_tokens_jti_revoked ON access_tokens(jti, revoked);
```

**Sample Data**:
```sql
INSERT INTO access_tokens VALUES (
    'jti_token123',
    'user_123e4567-e89b-12d3-a456-426614174000',
    'agent_abc123xyz',
    '["read:profile", "read:documents"]',
    'sha256_hash_of_token',
    '2026-01-05 10:10:30',
    '2026-01-05 11:10:30',  -- 1 hour expiration
    FALSE,
    NULL,
    NULL
);
```

---

### 6. refresh_tokens

Stores refresh tokens.

```sql
CREATE TABLE refresh_tokens (
    token_id TEXT PRIMARY KEY,                   -- Unique refresh token ID
    token_hash TEXT UNIQUE NOT NULL,             -- Hash of the refresh token
    user_id TEXT NOT NULL,                       -- User the token represents
    client_id TEXT NOT NULL,                     -- Agent that owns the token
    access_token_jti TEXT,                       -- Associated access token
    scopes TEXT NOT NULL,                        -- JSON array of scopes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,               -- Long expiration (30 days typical)
    revoked BOOLEAN DEFAULT FALSE,               -- Revocation status
    revoked_at TIMESTAMP,                        -- When revoked
    revocation_reason TEXT,                      -- Why revoked
    replaced_by TEXT,                            -- ID of replacement token (rotation)
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (client_id) REFERENCES agents(client_id) ON DELETE CASCADE,
    FOREIGN KEY (access_token_jti) REFERENCES access_tokens(jti) ON DELETE SET NULL,
    FOREIGN KEY (replaced_by) REFERENCES refresh_tokens(token_id) ON DELETE SET NULL
);

-- Indexes
CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_client_id ON refresh_tokens(client_id);
CREATE INDEX idx_refresh_tokens_token_hash ON refresh_tokens(token_hash);
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);
CREATE INDEX idx_refresh_tokens_revoked ON refresh_tokens(revoked);
```

**Sample Data**:
```sql
INSERT INTO refresh_tokens VALUES (
    'refresh_id_abc123',
    'sha256_hash_of_refresh_token',
    'user_123e4567-e89b-12d3-a456-426614174000',
    'agent_abc123xyz',
    'jti_token123',
    '["read:profile", "read:documents"]',
    '2026-01-05 10:10:30',
    '2026-02-04 10:10:30',  -- 30 days expiration
    FALSE,
    NULL,
    NULL,
    NULL
);
```

---

### 7. scopes

Reference table for available scopes.

```sql
CREATE TABLE scopes (
    scope_id TEXT PRIMARY KEY,                   -- Unique scope identifier
    scope_name TEXT UNIQUE NOT NULL,             -- Scope string (e.g., "read:profile")
    display_name TEXT NOT NULL,                  -- Human-readable name
    description TEXT NOT NULL,                   -- User-friendly description
    category TEXT NOT NULL,                      -- Grouping (profile, documents, etc.)
    sensitive BOOLEAN DEFAULT FALSE,             -- Requires extra user confirmation
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_scopes_scope_name ON scopes(scope_name);
CREATE INDEX idx_scopes_category ON scopes(category);
```

**Sample Data**:
```sql
INSERT INTO scopes VALUES
    ('scope_001', 'read:profile', 'Read Profile', 'View your profile information', 'profile', FALSE, '2026-01-01 00:00:00'),
    ('scope_002', 'write:profile', 'Update Profile', 'Update your profile information', 'profile', FALSE, '2026-01-01 00:00:00'),
    ('scope_003', 'delete:account', 'Delete Account', 'Delete your account', 'profile', TRUE, '2026-01-01 00:00:00'),
    ('scope_004', 'read:documents', 'Read Documents', 'View your documents', 'documents', FALSE, '2026-01-01 00:00:00'),
    ('scope_005', 'write:documents', 'Manage Documents', 'Create and update your documents', 'documents', FALSE, '2026-01-01 00:00:00'),
    ('scope_006', 'delete:documents', 'Delete Documents', 'Delete your documents', 'documents', TRUE, '2026-01-01 00:00:00'),
    ('scope_007', 'read:email', 'Read Emails', 'Read your emails', 'email', FALSE, '2026-01-01 00:00:00'),
    ('scope_008', 'send:email', 'Send Emails', 'Send emails on your behalf', 'email', TRUE, '2026-01-01 00:00:00'),
    ('scope_009', 'read:calendar', 'Read Calendar', 'View your calendar events', 'calendar', FALSE, '2026-01-01 00:00:00'),
    ('scope_010', 'write:calendar', 'Manage Calendar', 'Create and update calendar events', 'calendar', FALSE, '2026-01-01 00:00:00');
```

---

### 8. sessions

Stores user sessions for the authorization server.

```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,                 -- Unique session identifier
    user_id TEXT NOT NULL,                       -- User this session belongs to
    session_data TEXT,                           -- JSON session data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,               -- Session expiration
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address TEXT,                             -- User's IP address
    user_agent TEXT,                             -- User's browser/client
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);
```

**Sample Data**:
```sql
INSERT INTO sessions VALUES (
    'session_abc123xyz',
    'user_123e4567-e89b-12d3-a456-426614174000',
    '{"csrf_token": "xyz123", "login_time": "2026-01-05T09:30:00Z"}',
    '2026-01-05 09:30:00',
    '2026-01-05 10:30:00',  -- 1 hour session
    '2026-01-05 09:35:00',
    '192.168.1.100',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64)...'
);
```

---

### 9. audit_logs

Audit trail for security-relevant events.

```sql
CREATE TABLE audit_logs (
    log_id TEXT PRIMARY KEY,                     -- Unique log identifier
    event_type TEXT NOT NULL,                    -- Event type (login, consent, token_issued, etc.)
    user_id TEXT,                                -- User involved (if applicable)
    client_id TEXT,                              -- Agent involved (if applicable)
    resource TEXT,                               -- Resource accessed (if applicable)
    action TEXT NOT NULL,                        -- Action performed
    result TEXT NOT NULL,                        -- success, failure, error
    ip_address TEXT,                             -- Client IP address
    user_agent TEXT,                             -- Client user agent
    metadata TEXT,                               -- JSON additional metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL,
    FOREIGN KEY (client_id) REFERENCES agents(client_id) ON DELETE SET NULL
);

-- Indexes
CREATE INDEX idx_audit_logs_event_type ON audit_logs(event_type);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_client_id ON audit_logs(client_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX idx_audit_logs_result ON audit_logs(result);
```

**Sample Data**:
```sql
INSERT INTO audit_logs VALUES
    ('log_001', 'user.login', 'user_123e4567-e89b-12d3-a456-426614174000', NULL, NULL, 'login', 'success', '192.168.1.100', 'Mozilla/5.0...', '{"method": "password"}', '2026-01-05 09:30:00'),
    ('log_002', 'consent.granted', 'user_123e4567-e89b-12d3-a456-426614174000', 'agent_abc123xyz', NULL, 'grant_consent', 'success', '192.168.1.100', 'Mozilla/5.0...', '{"scopes": ["read:profile", "read:documents"]}', '2026-01-05 10:10:00'),
    ('log_003', 'token.issued', 'user_123e4567-e89b-12d3-a456-426614174000', 'agent_abc123xyz', NULL, 'issue_token', 'success', '192.168.1.101', 'Agent/1.0', '{"grant_type": "authorization_code", "scopes": ["read:profile", "read:documents"]}', '2026-01-05 10:10:30'),
    ('log_004', 'resource.access', 'user_123e4567-e89b-12d3-a456-426614174000', 'agent_abc123xyz', '/api/user/profile', 'read', 'success', '192.168.1.101', 'Agent/1.0', '{"scope": "read:profile"}', '2026-01-05 10:11:00');
```

---

### 10. documents (Sample Resource)

Example resource table for the resource server.

```sql
CREATE TABLE documents (
    document_id TEXT PRIMARY KEY,                -- Unique document identifier
    user_id TEXT NOT NULL,                       -- Owner of the document
    title TEXT NOT NULL,                         -- Document title
    content TEXT,                                -- Document content
    tags TEXT,                                   -- JSON array of tags
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,                        -- Soft delete
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_documents_user_id ON documents(user_id);
CREATE INDEX idx_documents_created_at ON documents(created_at);
CREATE INDEX idx_documents_deleted_at ON documents(deleted_at);
```

**Sample Data**:
```sql
INSERT INTO documents VALUES
    ('doc_001', 'user_123e4567-e89b-12d3-a456-426614174000', 'Project Proposal', 'Lorem ipsum dolor sit amet...', '["project", "proposal", "2026"]', '2026-01-03 10:00:00', '2026-01-04 15:30:00', NULL),
    ('doc_002', 'user_123e4567-e89b-12d3-a456-426614174000', 'Meeting Notes', 'Discussion points from the meeting...', '["meeting", "notes"]', '2026-01-02 14:00:00', '2026-01-02 14:00:00', NULL);
```

---

## Database Initialization Script

```sql
-- Enable foreign key constraints (SQLite)
PRAGMA foreign_keys = ON;

-- Create all tables in order
-- (Copy CREATE TABLE statements from above)

-- Insert default scopes
-- (Copy scope INSERT statements from above)

-- Create cleanup trigger for expired codes
CREATE TRIGGER cleanup_expired_auth_codes
AFTER INSERT ON authorization_codes
BEGIN
    DELETE FROM authorization_codes
    WHERE expires_at < datetime('now')
    AND used = TRUE;
END;

-- Create cleanup trigger for expired sessions
CREATE TRIGGER cleanup_expired_sessions
AFTER INSERT ON sessions
BEGIN
    DELETE FROM sessions
    WHERE expires_at < datetime('now');
END;
```

---

## Data Retention Policies

### Automatic Cleanup

**Authorization Codes**:
- Delete after use AND expiration (5 minutes)
- Keep used codes for 24 hours for audit purposes

**Sessions**:
- Delete after expiration (1 hour typical)
- Keep for audit purposes: 30 days

**Access Tokens**:
- Keep revoked tokens for 90 days
- Delete expired tokens after 7 days
- Archive for compliance: 1 year

**Refresh Tokens**:
- Keep revoked tokens for 90 days
- Delete expired tokens after 30 days
- Keep token rotation chain for audit

**Audit Logs**:
- Retain for 1 year minimum
- Archive older logs to cold storage
- Never delete security incidents

### Cleanup Queries

```sql
-- Clean up expired authorization codes (used)
DELETE FROM authorization_codes
WHERE expires_at < datetime('now', '-1 day')
AND used = TRUE;

-- Clean up expired sessions
DELETE FROM sessions
WHERE expires_at < datetime('now');

-- Clean up expired access tokens (non-revoked)
DELETE FROM access_tokens
WHERE expires_at < datetime('now', '-7 days')
AND revoked = FALSE;

-- Archive old revoked tokens
DELETE FROM access_tokens
WHERE revoked = TRUE
AND revoked_at < datetime('now', '-90 days');

-- Archive old audit logs
DELETE FROM audit_logs
WHERE created_at < datetime('now', '-1 year');
```

---

## Migration from SQLite to PostgreSQL

When migrating from SQLite to PostgreSQL, make these changes:

### Data Type Changes

```sql
-- SQLite -> PostgreSQL
TEXT -> VARCHAR or TEXT
TIMESTAMP -> TIMESTAMP WITH TIME ZONE
BOOLEAN -> BOOLEAN (same)
```

### UUID Support

```sql
-- Add UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Use UUID type
user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4()
```

### JSON Support

```sql
-- Use JSONB for better performance
scopes JSONB NOT NULL
redirect_uris JSONB NOT NULL
```

### Index Optimization

```sql
-- Add partial indexes
CREATE INDEX idx_access_tokens_active
ON access_tokens(jti)
WHERE revoked = FALSE AND expires_at > NOW();

-- Add GIN indexes for JSON
CREATE INDEX idx_consents_scopes ON consents USING GIN(scopes);
```

---

## Performance Optimization

### Recommended Indexes

```sql
-- Composite indexes for common queries
CREATE INDEX idx_access_tokens_user_client_valid
ON access_tokens(user_id, client_id, expires_at)
WHERE revoked = FALSE;

CREATE INDEX idx_consents_user_client_active
ON consents(user_id, client_id)
WHERE revoked = FALSE;

-- Full-text search on documents (PostgreSQL)
CREATE INDEX idx_documents_content_fts
ON documents USING GIN(to_tsvector('english', content));
```

### Query Optimization Tips

1. **Token Validation**: Cache valid tokens for 1 minute to reduce DB hits
2. **Scope Lookup**: Cache scope definitions in memory
3. **User Sessions**: Use Redis for session storage in production
4. **Audit Logs**: Use asynchronous writes to avoid blocking requests

---

## Security Considerations

### Password Storage

```python
import bcrypt

# Hash password
password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))

# Verify password
if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
    # Password correct
```

### Token Hashing

```python
import hashlib

# Hash token for storage
token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()

# Verify token
if hashlib.sha256(provided_token.encode('utf-8')).hexdigest() == stored_hash:
    # Token matches
```

### SQL Injection Prevention

```python
# ALWAYS use parameterized queries
cursor.execute(
    "SELECT * FROM users WHERE username = ?",
    (username,)
)

# NEVER concatenate user input
# BAD: cursor.execute(f"SELECT * FROM users WHERE username = '{username}'")
```

---

## Backup Strategy

### SQLite Backup

```bash
# Backup database file
sqlite3 database.db ".backup database_backup.db"

# Export to SQL
sqlite3 database.db .dump > database_backup.sql
```

### PostgreSQL Backup

```bash
# Dump database
pg_dump oauth_db > backup.sql

# Restore database
psql oauth_db < backup.sql
```

### Recommended Schedule

- **Hourly**: Incremental backups (WAL archiving for PostgreSQL)
- **Daily**: Full database backup
- **Weekly**: Off-site backup
- **Monthly**: Long-term archive
