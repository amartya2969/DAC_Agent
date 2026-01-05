# OAuth 2.1 Agent Authentication Flow - Dynamic Access Control

A proof-of-concept implementation demonstrating how AI agents authenticate and access resources on behalf of users, with distinct identities for both the user and the agent.

## Overview

This project implements the OAuth 2.1 Agent Authentication Flow, a specialized authorization pattern designed for AI agents that need to act on behalf of users while maintaining separate identities. This enables:

- **Distinct Identity Management**: Separate authentication and authorization for users and agents
- **Dynamic Access Control**: Fine-grained permission management based on user consent and agent capabilities
- **Secure Token Management**: Support for access tokens, refresh tokens, and token revocation
- **Scope-based Permissions**: Granular control over what resources agents can access

## Key Features

- ✅ OAuth 2.1 compliant authorization server
- ✅ Agent authentication and authorization flow
- ✅ User consent management
- ✅ Refresh token support with rotation
- ✅ Token revocation (access and refresh tokens)
- ✅ Scope-based access control
- ✅ Resource server with protected endpoints
- ✅ SQLite database (easily upgradeable to PostgreSQL)

## Architecture Components

1. **Authorization Server**: Handles user authentication, agent registration, and token issuance
2. **Resource Server**: Hosts protected resources accessible by authorized agents
3. **Agent Client**: Example AI agent that requests access on behalf of users
4. **Database**: SQLite database storing users, agents, tokens, and consent records

## Technology Stack

- **Language**: Python 3.9+
- **Web Framework**: Flask
- **Database**: SQLite (production-ready for PostgreSQL migration)
- **Authentication**: JWT (JSON Web Tokens)
- **Security**: cryptography, secrets, hashlib

## Project Structure

```
DAC_Agent/
├── docs/
│   ├── ARCHITECTURE.md          # System architecture and design
│   ├── OAUTH_FLOW.md           # OAuth 2.1 Agent Authentication Flow details
│   ├── API_SPECIFICATION.md    # Complete API documentation
│   ├── DATABASE_SCHEMA.md      # Database schema and design
│   └── IMPLEMENTATION_PLAN.md  # Step-by-step implementation guide
├── src/
│   ├── auth_server/            # Authorization server implementation
│   ├── resource_server/        # Resource server implementation
│   ├── agent_client/           # Example agent client
│   ├── models/                 # Database models
│   └── utils/                  # Shared utilities
├── tests/                      # Test suite
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## Quick Start

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- Virtual environment (recommended)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd DAC_Agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python scripts/init_db.py

# Run the authorization server
python -m src.auth_server.app

# In another terminal, run the resource server
python -m src.resource_server.app

# In another terminal, run the example agent
python -m src.agent_client.example_agent
```

## Usage Example

```python
from src.agent_client import AgentClient

# Initialize agent
agent = AgentClient(
    agent_id="my-ai-agent",
    client_secret="agent-secret"
)

# Request user authorization
auth_url = agent.get_authorization_url(
    user_id="user@example.com",
    scopes=["read:profile", "write:documents"]
)

# User visits auth_url and grants consent

# Exchange authorization code for tokens
tokens = agent.exchange_code(authorization_code)

# Access protected resources
response = agent.access_resource(
    url="https://api.example.com/user/profile",
    access_token=tokens["access_token"]
)

# Refresh tokens when needed
new_tokens = agent.refresh_access_token(tokens["refresh_token"])

# Revoke tokens when done
agent.revoke_token(tokens["access_token"])
```

## Security Considerations

This is a **proof-of-concept** implementation for demonstration and learning purposes. For production use, consider:

- Using HTTPS/TLS for all communications
- Implementing rate limiting and brute force protection
- Adding comprehensive logging and monitoring
- Using a production-grade database (PostgreSQL)
- Implementing proper secret management (environment variables, secret managers)
- Adding CSRF protection
- Implementing PKCE (Proof Key for Code Exchange)
- Regular security audits

## Documentation

- [Architecture Overview](docs/ARCHITECTURE.md) - System design and component interactions
- [OAuth 2.1 Agent Flow](docs/OAUTH_FLOW.md) - Detailed flow diagrams and specifications
- [API Specification](docs/API_SPECIFICATION.md) - Complete API reference
- [Database Schema](docs/DATABASE_SCHEMA.md) - Database design and relationships
- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md) - Development roadmap

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please read CONTRIBUTING.md for guidelines.

## References

- [OAuth 2.1 Draft Specification](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-07)
- [RFC 6749 - OAuth 2.0 Framework](https://datatracker.ietf.org/doc/html/rfc6749)
- [RFC 7009 - Token Revocation](https://datatracker.ietf.org/doc/html/rfc7009)
- [RFC 7662 - Token Introspection](https://datatracker.ietf.org/doc/html/rfc7662)
