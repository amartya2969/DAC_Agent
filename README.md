# Agentic AI Identity Management Framework

A Zero-Trust Identity and Access Management (IAM) framework for Multi-Agent Systems (MAS) that enables secure authentication, authorization, and lifecycle management of AI agents using decentralized identity primitives.

## Overview

This framework provides a complete identity and access control solution for AI agents, supporting:

- **Decentralized Identity (DIDs)**: Unique, verifiable identifiers for agents
- **Verifiable Credentials (VCs)**: Cryptographically-signed claims about agent capabilities
- **Agent Naming Service (ANS)**: DNS-like discovery for finding agents by capability
- **Dynamic Access Control**: Policy-based authorization with Open Policy Agent
- **Global Session Management**: Cross-protocol session control with instant revocation
- **Audit Trail**: Complete attribution of all agent actions

## Architecture - 4 Core Layers

### Layer 1: Identity & Credential Management
- **DID Manager**: Create, resolve, and manage Decentralized Identifiers
- **VC Issuer/Verifier**: Issue and verify Verifiable Credentials
- **Agent Wallet**: Secure storage for keys and credentials

### Layer 2: Agent Discovery & Trust (ANS)
- **ANS Registry**: Store and index agent registrations
- **ANS Resolver**: Query agents by capability, protocol, version
- **Trust Framework**: Maintain trusted credential issuers

### Layer 3: Dynamic Access Control
- **Policy Decision Point (PDP)**: Evaluate access using policies
- **Policy Information Point (PIP)**: Gather agent and resource attributes
- **JIT Credential Service**: Issue short-lived, scoped credentials

### Layer 4: Global Session Management
- **Session Authority (SA)**: Coordinate global session state
- **Session State Synchronizer (SSS)**: Distributed session registry
- **Adapter Enforcement Middleware (AEM)**: Protocol-specific enforcement

## Technology Stack

- **Language**: Python 3.11+
- **DID/VC**: Custom implementation for did:key method
- **Policy Engine**: Open Policy Agent (OPA) with Rego
- **Session Store**: Redis
- **Database**: SQLite/PostgreSQL for ANS registry
- **Crypto**: Ed25519 signatures
- **API**: Flask REST API

## Project Structure

```
DAC_Agent/
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DID_SPECIFICATION.md
│   ├── VC_SPECIFICATION.md
│   ├── ANS_SPECIFICATION.md
│   └── IMPLEMENTATION_PLAN.md
├── src/
│   ├── identity/
│   │   ├── did_manager.py
│   │   ├── vc_issuer.py
│   │   └── agent_wallet.py
│   ├── ans/
│   │   ├── registry.py
│   │   └── resolver.py
│   ├── policy/
│   │   ├── pdp.py
│   │   └── pip.py
│   ├── session/
│   │   ├── session_authority.py
│   │   └── session_store.py
│   ├── adapters/
│   │   └── http_aem.py
│   ├── services/
│   │   ├── did_service.py
│   │   ├── ans_service.py
│   │   └── session_service.py
│   ├── models/
│   └── cli/
├── scripts/
│   └── init_db.py
└── README.md
```

## Quick Start

### Prerequisites

- Python 3.11 or higher
- Redis server
- pip (Python package manager)

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

# Set up environment
cp .env.example .env

# Initialize database
python scripts/init_db.py

# Start Redis (in separate terminal)
redis-server

# Run the framework
python -m src.main
```

## Usage Example

```python
from src.identity.did_manager import DIDManager
from src.identity.vc_issuer import VCIssuer
from src.ans.registry import ANSRegistry

# Create agent identity
did_manager = DIDManager()
agent_did = did_manager.create_did("agent-alpha")

# Issue capability credential
vc_issuer = VCIssuer()
capability_vc = vc_issuer.issue_capability_vc(
    subject_did=agent_did,
    capability="FinancialAnalysis",
    issuer_did="did:key:z6Mk..."
)

# Register with ANS
ans = ANSRegistry()
ans.register(
    ans_name="financial://agent-alpha.analysis.acme.v1",
    agent_did=agent_did,
    capabilities=["FinancialAnalysis"],
    service_endpoint="https://api.example.com/agent"
)

# Discover agents by capability
agents = ans.resolve_by_capability("FinancialAnalysis")
```

## Core Workflows

### 1. Agent Registration
1. Generate DID and keypair
2. Create DID Document with metadata
3. Request capability VCs from issuers
4. Register with ANS
5. Store credentials in wallet

### 2. Agent Authorization
1. Agent presents DID + VCs to resource
2. PDP validates credentials and evaluates policy
3. Create global session if authorized
4. Grant access to resource

### 3. Global Revocation
1. Revocation triggered (compromise, violation)
2. Session Authority terminates all sessions
3. AEMs enforce termination across protocols
4. Update ANS and VC status lists

### 4. JIT Credential Delegation
1. Orchestrator queries ANS for suitable agent
2. Issues short-lived, scoped VC
3. Ephemeral agent presents VC for access
4. VC expires after use

## CLI Tool

```bash
# Register new agent
python -m src.cli agent register --name agent-alpha --model gpt-4

# Issue capability credential
python -m src.cli vc issue --subject did:key:z6Mk... --capability FinancialAnalysis

# Query ANS
python -m src.cli ans resolve --capability FinancialAnalysis

# Check session status
python -m src.cli session status --did did:key:z6Mk...

# Revoke agent access
python -m src.cli agent revoke --did did:key:z6Mk...
```

## Phase 1 MVP (Current)

✅ DID creation and resolution (did:key method)
✅ Basic VC issuance and verification
✅ ANS registry with capability search
✅ PDP with hardcoded policies
✅ Session management with Redis
✅ HTTP AEM adapter
✅ Demo CLI

## Security Considerations

- All keys use Ed25519 cryptography
- DIDs and VCs follow W3C standards
- Session state is distributed and fault-tolerant
- Comprehensive audit logging with DID attribution
- Rate limiting on all public endpoints
- Input validation and sanitization

## Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)
- [DID Specification](docs/DID_SPECIFICATION.md)
- [Verifiable Credentials](docs/VC_SPECIFICATION.md)
- [Agent Naming Service](docs/ANS_SPECIFICATION.md)
- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md)

## License

MIT License

## Contributing

Contributions welcome! This is a research prototype for exploring decentralized identity in multi-agent systems.

## References

- [W3C DID Core](https://www.w3.org/TR/did-core/)
- [W3C Verifiable Credentials](https://www.w3.org/TR/vc-data-model/)
- [DID Method Specifications](https://w3c.github.io/did-spec-registries/)
- [Open Policy Agent](https://www.openpolicyagent.org/)
