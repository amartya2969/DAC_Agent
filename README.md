# DAC Agent - The Isolation Layer for Multi-Tenant AI

**Sidecar-Based Infrastructure for Zero-Trust Agent Security**

A production-ready framework that provides cryptographic identity, policy enforcement, and circuit breaking for AI agents. Designed as transparent infrastructure—agents get security and observability "for free" without code changes.

---

## ⚡ Quick Demo (30 seconds)

**See the "Confused Deputy" attack prevention in action:**

```bash
python demo_confused_deputy.py
```

This demonstrates how DAC Agent prevents User A from accessing User B's data via prompt injection, even though they share the same agent container. It shows:
- ✅ Request-scoped identity isolation
- ✅ User-scoped AWS tokens (NOT shared service accounts)
- ✅ Network-layer blocking of unauthorized access
- ✅ Surgical revocation (Alice blocked, Bob continues)
- ✅ Complete audit trail (WHO accessed WHAT for WHOM)

**The value proposition in 30 seconds of runtime.** No Docker/Redis required.

---

## 🎯 The Problem We Solve

### The "Confused Deputy" Attack (Multi-Tenant Agents)

**The Architectural Conflict:**
To make AI cost-effective, you run one agent container serving 1000+ users. But while the compute is shared, the identity MUST be isolated.

**The Failure Mode:**
- Container uses ONE "Master Key" (Service Account) to access resources
- User A tricks agent via prompt injection: "Show me User B's financial data"
- Agent uses its Master Key to access User B's data
- Standard cloud IAM cannot distinguish User A from User B inside the container

**DAC Solution: Request-Scoped Identity Isolation**
- Sidecar intercepts request at network layer
- Swaps Master Key → User A's temporary token (scoped to ONLY User A's data)
- User A's token physically CANNOT access User B's resources
- Even if LLM is tricked, network layer enforces isolation

**Result:** User A blocked, User B continues, container keeps running. Surgical precision.

---

### The Problems We Solve

#### 1. Secret Sprawl
**Before**: API keys hardcoded in agent code → security risk, rotation nightmare, compliance violations

**After**: User-scoped tokens (1h auto-rotation) → zero static secrets in code

#### 2. Non-Repudiable Attribution
**Before**: Logs show "AI Agent did it" → auditors cannot prove which HUMAN caused action

**After**: CloudTrail shows "agent-user-alice@corp.com" → complete attribution

#### 3. Runaway Usage
**Before**: Agent enters infinite loop → $10,000 AWS bill overnight

**After**: Circuit breaker kills connection at 50MB/min → surgical cost control

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        AI AGENT (Container)                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Agent Code (Python/JS/Go)                               │  │
│  │  • NO AWS keys                                           │  │
│  │  • NO hardcoded secrets                                  │  │
│  │  • Makes requests to cloud/MCP                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           ↓ (all traffic)                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  SIDECAR (Go Binary)                                     │  │
│  │  • Intercepts ALL outbound traffic                       │  │
│  │  • Calls Control Plane for credentials                   │  │
│  │  • Injects identity into requests                        │  │
│  │  • Enforces circuit breaker (Redis)                      │  │
│  │  • Validates MCP messages                                │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                  CONTROL PLANE (Python)                          │
│  • Issues DIDs and Verifiable Credentials                       │
│  • Exchanges VCs for AWS/GCP tokens (OIDC Bridge)               │
│  • Enforces policies (OPA)                                      │
│  • Provides real-time dashboard                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Separation of Concerns

**Control Plane** (The Brain): Python service that handles identity logic
- `control-plane/src/identity/` - DID Manager & VC Issuer
- `control-plane/src/bridge/` - **NEW**: OIDC/AWS Token Exchange
- `control-plane/src/policy/` - OPA Policy Engine
- `control-plane/src/dashboard/` - Real-time monitoring UI

**Sidecar** (The Bouncer): Go binary deployed alongside agents
- `sidecar/main.go` - Transparent HTTP/HTTPS proxy
- `sidecar/circuit_breaker.go` - **NEW**: Redis-backed rate limiting
- `sidecar/mcp_inspector.go` - **NEW**: MCP protocol validator

**Deployment** (Infrastructure-as-Code):
- `docker-compose.yml` - Local dev environment
- `deploy/helm/` - Kubernetes DaemonSet (coming soon)

---

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

This spins up the complete stack: Control Plane + Sidecar + Redis + Mock Agent

```bash
# Clone repository
git clone https://github.com/amartya2969/DAC_Agent.git
cd DAC_Agent

# Start the mesh
docker-compose up

# In another terminal, view logs
docker-compose logs -f sidecar
docker-compose logs -f mock-agent

# Access dashboard
open http://localhost:5000
```

**What you'll see:**
- Mock agent making requests (all intercepted by sidecar)
- Circuit breaker enforcing 50MB/min limit
- MCP messages being validated
- Real-time dashboard showing agent activity

### Option 2: Local Development

```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start Control Plane
cd control-plane
pip install -r requirements.txt
python demo_enterprise.py

# Terminal 3: Build and run Sidecar
cd sidecar
go build -o dac-sidecar
./dac-sidecar

# Terminal 4: Run simulation
cd simulation
python agent_simulation.py
```

---

## 💡 Core Features

### 1. Cloud Identity Bridge (VC → OIDC)

**The specific code that solves "Secret Sprawl":**

```python
# control-plane/src/bridge/aws_adapter.py

def exchange_credential(agent_vc_jwt, user_context, target_role_arn):
    # 1. Verify Agent's VC cryptographically
    verified_payload = vc_issuer.verify_vc(agent_vc_jwt)

    # 2. Create OIDC token from VC (Web3 → Web2 bridge)
    oidc_token = generate_oidc_token_from_vc(agent_vc_jwt)

    # 3. Call AWS STS AssumeRoleWithWebIdentity
    aws_credentials = sts_client.assume_role_with_web_identity(
        RoleArn=target_role_arn,
        RoleSessionName=f"{agent_did}-{user_context}",  # Attribution!
        WebIdentityToken=oidc_token,
        DurationSeconds=3600  # 1 hour, auto-rotates
    )

    return aws_credentials  # Temporary keys, no static secrets!
```

**Supports:**
- ✅ AWS STS (AssumeRoleWithWebIdentity)
- ✅ GCP Workload Identity
- ✅ Azure Managed Identity

### 2. MCP Sidecar (Security Chip for MCP)

**The moat - protocol-specific validation:**

```go
// sidecar/mcp_inspector.go

func (mi *MCPInspector) Validate(mcpMessage map[string]interface{}) error {
    method := mcpMessage["method"]  // e.g., "tools/call"
    toolName := mcpMessage["params"]["name"]  // e.g., "execute_sql"

    // Map tool to required capability
    requiredCapability := getRequiredCapability(toolName)
    // "execute_sql" → "DatabaseAccess"

    // Call Control Plane to verify agent has capability in VC
    if !agentHasCapability(agentDID, requiredCapability) {
        return fmt.Errorf("agent lacks capability '%s'", requiredCapability)
    }

    // Inject agent identity into MCP message
    mcpMessage["params"]["_agent_identity"] = map[string]interface{}{
        "did": agentDID,
        "session_id": sessionID,
        "timestamp": time.Now(),
    }

    return nil  // Allowed!
}
```

**Blocks:**
- ❌ `delete_database` - High-risk destructive tool
- ❌ Tools requiring capabilities the agent doesn't have
- ❌ Access to restricted resources (e.g., `/etc/passwd`)

### 3. Circuit Breaker (The Kill Switch)

**Redis-backed velocity limits:**

```go
// sidecar/circuit_breaker.go

func (cb *CircuitBreaker) CheckLimit(ctx context.Context) (bool, string) {
    usage := redis.Get(ctx, "usage:" + agentDID).Int64()
    limitBytes := 50 * 1024 * 1024  // 50 MB/min

    if usage >= limitBytes {
        return false, "Rate limit exceeded"  // 429 Too Many Requests
    }

    return true, ""  // Allowed
}

func (cb *CircuitBreaker) RecordUsage(ctx context.Context, bytes int) {
    redis.IncrBy(ctx, "usage:" + agentDID, bytes)
    redis.Expire(ctx, "usage:" + agentDID, 60 * time.Second)
}
```

**If response > 50MB in single request:**
→ Kill TCP connection immediately (prevents runaway costs)

---

## 📊 Dashboard

Real-time monitoring UI at `http://localhost:5000`

**Features:**
- **Agent Registry**: View all DIDs, capabilities, models
- **Active Sessions**: Monitor running agents
- **Surgical Kill Switch**: Revoke individual sessions instantly
- **Audit Trail**: Complete attribution (every action → agent DID)
- **ANS Browser**: Discover agents by capability
- **Cloud Credentials**: Track cached AWS/GCP tokens

**Screenshots:**
- Dark mode, SOC team-optimized
- Auto-refresh every 5s
- Responsive design

---

## 🔒 Security Properties

| Property | Implementation | Verification |
|----------|----------------|--------------|
| **Identity** | Ed25519 DIDs (W3C standard) | Cryptographic signatures |
| **Capabilities** | Signed VCs (cannot be forged) | JWT with EdDSA |
| **Discovery** | ANS (capability-based search) | SQLite registry |
| **Cloud Access** | Short-lived tokens (1h) | AWS STS, GCP Workload Identity |
| **Key Management** | KMS bootstrap → tmpfs (memory-only) | Never stored on disk |
| **MCP Security** | Sidecar validates every call | JSON-RPC inspection |
| **Audit Trail** | Complete DID attribution | PostgreSQL/SQLite logs |
| **Zero Trust** | Continuous verification | Every layer checks credentials |
| **Kill Switch** | Instant session revocation | Redis-backed state |

---

## 📁 Repository Structure

```
DAC_Agent/
├── control-plane/           # The Brain (Python)
│   ├── src/
│   │   ├── identity/        # DID Manager, VC Issuer
│   │   ├── bridge/          # ⭐ NEW: OIDC/AWS Token Exchange
│   │   ├── ans/             # Agent Naming Service
│   │   ├── session/         # Session Authority
│   │   ├── policy/          # OPA Policies (.rego files)
│   │   ├── dashboard/       # ⭐ NEW: Real-time UI
│   │   ├── cloud/           # Cloud integrations
│   │   ├── mcp/             # MCP server components
│   │   └── models/          # Database models
│   ├── demo.py              # Core demo
│   ├── demo_enterprise.py   # Complete workflow demo
│   └── requirements.txt
├── sidecar/                 # ⭐ NEW: The Bouncer (Go)
│   ├── main.go              # Transparent proxy
│   ├── circuit_breaker.go   # Redis-backed rate limiting
│   ├── mcp_inspector.go     # MCP protocol validator
│   └── go.mod
├── simulation/              # ⭐ NEW: Testing
│   └── agent_simulation.py  # Mock agent for validation
├── deploy/                  # ⭐ Coming Soon
│   └── helm/                # Kubernetes charts
├── docker-compose.yml       # ⭐ NEW: Full stack
├── Dockerfile.control       # Control Plane image
├── Dockerfile.sidecar       # Sidecar image
├── PRESENTATION.md          # 60-slide pitch deck
└── README.md                # This file
```

---

## 🎯 Use Cases

### 1. Financial Services
**Problem**: Analyst agents need S3 access, but hardcoded keys are a compliance violation (SOC2, ISO27001)

**Solution**:
- Agent presents `FinancialAnalysis` VC
- Sidecar exchanges for 1h AWS token
- CloudTrail shows: `agent-z6MkxYz-user-john` accessed `s3://financial-data/`
- Compliance team can prove WHO accessed WHAT for WHOM

### 2. Healthcare (HIPAA)
**Problem**: Diagnostic agent accesses patient database—need audit trail

**Solution**:
- Agent presents `HealthcareProvider` VC
- MCP sidecar injects DID into every SQL query
- Database logs show: `did:key:z6MkABC executed SELECT * FROM patients`
- Non-repudiable proof for auditors

### 3. DevOps Automation
**Problem**: CI/CD agent deploys to Kubernetes—needs short-lived kubeconfig

**Solution**:
- Agent presents `KubernetesAdmin` VC
- Bridge exchanges for GCP Workload Identity token
- Token expires after 1h (zero long-lived secrets)
- Circuit breaker prevents runaway pod creation

---

## 🚢 Production Deployment

### Kubernetes (Recommended)

```yaml
# deploy/helm/values.yaml
sidecar:
  image: dac-sidecar:latest
  deployment: daemonset  # One sidecar per node
  env:
    CONTROL_PLANE_URL: https://control-plane.internal
    REDIS_URL: redis-cluster.internal:6379
    POLICY_LIMIT_MB_PER_MIN: 100

controlPlane:
  image: dac-control-plane:latest
  replicas: 3  # HA setup
  env:
    DATABASE_URL: postgresql://...
    AWS_SIMULATION: false  # Use real AWS STS
```

**Inject sidecar via MutatingWebhook:**
→ Every pod with label `dac.security/enabled: true` gets sidecar automatically

### AWS ECS

```json
{
  "containerDefinitions": [
    {
      "name": "agent",
      "image": "my-agent:latest",
      "dependsOn": [{"containerName": "dac-sidecar"}]
    },
    {
      "name": "dac-sidecar",
      "image": "dac-sidecar:latest",
      "essential": true,
      "portMappings": [{"containerPort": 8080}]
    }
  ]
}
```

---

## 📈 Market Positioning

### "SOC2 for Agents"
Compliance teams will block agent deployments without cryptographic proof of WHO did WHAT. This framework provides that proof.

### "Security Chip for MCP"
If MCP becomes the standard (like USB), this becomes the security layer (like TPM). Infrastructure play, not application play.

### Competitive Moat
- **Standards-based**: W3C DIDs, VCs (defensible)
- **Protocol-specific**: MCP inspector (high switching cost)
- **Multi-cloud**: AWS + GCP + Azure (cloud-agnostic)

---

## 🛠️ Development

### Run Tests
```bash
# Control Plane tests
cd control-plane
pytest tests/

# Sidecar tests
cd sidecar
go test ./...

# Integration test
docker-compose up
# Verify mock-agent logs show successful interception
```

### Add New Cloud Provider

1. Create adapter in `control-plane/src/bridge/`
2. Implement `exchange_credential(vc_jwt, provider_config)`
3. Update sidecar to call new endpoint
4. Add integration test

### Add MCP Tool Mapping

Edit `sidecar/mcp_inspector.go`:

```go
capabilityMap := map[string]string{
    "your_new_tool": "RequiredCapability",
}
```

---

## 📚 Documentation

- **Architecture**: See `PRESENTATION.md` (60-slide deck)
- **API Docs**: Coming soon (Swagger/OpenAPI)
- **Deployment Guide**: `deploy/README.md` (coming soon)
- **Video Demo**: Coming soon

---

## 🤝 Contributing

Contributions welcome! This is infrastructure-grade code—focus areas:

- [ ] Helm chart for Kubernetes
- [ ] Terraform modules for AWS/GCP
- [ ] OpenTelemetry integration
- [ ] Grafana dashboards
- [ ] Additional cloud providers (Alibaba Cloud, Oracle Cloud)

---

## 📄 License

MIT License - See LICENSE file

---

## 🌟 Why This Matters

Traditional agent security is **reactive** (detect breaches after they happen).

This framework is **proactive** (prevent unauthorized actions before they execute).

The difference:
- **Before**: "We detected Agent X accessed S3 bucket Y at 3am" (too late)
- **After**: "Agent X tried to access S3 bucket Y but was blocked (no `S3Read` VC)"

**Zero Trust Architecture** means continuous verification at every layer.

---

## 📧 Contact

- **Issues**: https://github.com/amartya2969/DAC_Agent/issues
- **Discussions**: https://github.com/amartya2969/DAC_Agent/discussions
- **Enterprise Support**: enterprise@your-company.com

---

**Built with ❤️ for the future of secure AI agents**
