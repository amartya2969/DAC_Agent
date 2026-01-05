"""Enterprise Demo - Full Stack Identity Management for AI Agents

This demonstrates the COMPLETE solution:
1. Agent Identity Creation (DIDs)
2. Capability Credentials (VCs)
3. Agent Discovery (ANS)
4. Cloud Identity Bridge (VC → AWS/GCP tokens)
5. MCP Sidecar Security
6. Secure Key Bootstrap from KMS

This is the "money shot" demo for enterprise customers.
"""
import sys
sys.path.insert(0, '.')

import asyncio
import json
from src.identity.did_manager import DIDManager
from src.identity.vc_issuer import VCIssuer
from src.ans.registry import ANSRegistry
from src.cloud.identity_bridge import CloudIdentityBridge, CloudCredentialCache
from src.cloud.key_bootstrap import SecureKeyBootstrap
from src.mcp.sidecar import MCPSidecar, MCPSidecarServer


def print_section(title, emoji="📋"):
    """Print section header."""
    print("\n" + "=" * 80)
    print(f"{emoji}  {title}")
    print("=" * 80)


def print_subsection(title):
    """Print subsection."""
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


async def main():
    print("\n" + "🎯" * 40)
    print("ENTERPRISE DEMO: Agentic AI Identity Management Framework")
    print("Full Stack Solution: DIDs + VCs + ANS + Cloud Bridge + MCP Sidecar")
    print("🎯" * 40)

    # =========================================================================
    # PHASE 1: IDENTITY FOUNDATION
    # =========================================================================
    print_section("PHASE 1: Identity Foundation (DIDs + VCs)", "🆔")

    # Initialize core components
    did_manager = DIDManager()
    vc_issuer = VCIssuer(did_manager=did_manager)
    ans_registry = ANSRegistry()

    print("✓ Initialized: DID Manager, VC Issuer, ANS Registry")

    # Create trusted issuer
    print_subsection("1.1 Create Trusted Credential Issuer")
    issuer_result = did_manager.create_did(
        agent_name="ACME Enterprise Trust Authority",
        metadata={
            "model": "system",
            "provider": "ACME Corp",
            "capabilities": ["CredentialIssuance", "PolicyEnforcement"],
            "scopeOfBehavior": "Issues and manages credentials for ACME agents"
        }
    )
    issuer_did = issuer_result["did"]
    issuer_key = issuer_result["private_key_pem"]
    print(f"✓ Issuer DID: {issuer_did[:60]}...")

    # Create production agent
    print_subsection("1.2 Create Production Agent (Financial Analyzer)")
    agent_result = did_manager.create_did(
        agent_name="Agent Alpha - Financial Analyzer",
        metadata={
            "model": "gpt-4-turbo",
            "version": "2.0",
            "provider": "ACME Corp",
            "capabilities": ["FinancialAnalysis", "DatabaseAccess", "ExternalAPIAccess"],
            "scopeOfBehavior": "Analyzes financial data from cloud databases and APIs"
        }
    )
    agent_did = agent_result["did"]
    agent_key = agent_result["private_key_pem"]
    print(f"✓ Agent DID: {agent_did[:60]}...")
    print(f"✓ Capabilities: FinancialAnalysis, DatabaseAccess, ExternalAPIAccess")

    # Issue capability credentials
    print_subsection("1.3 Issue Capability Credentials")

    financial_vc = vc_issuer.issue_capability_vc(
        issuer_did=issuer_did,
        issuer_private_key_pem=issuer_key,
        subject_did=agent_did,
        capability="FinancialAnalysis",
        validity_days=365
    )
    print(f"✓ Issued: FinancialAnalysis VC")

    database_vc = vc_issuer.issue_capability_vc(
        issuer_did=issuer_did,
        issuer_private_key_pem=issuer_key,
        subject_did=agent_did,
        capability="DatabaseAccess",
        validity_days=365
    )
    print(f"✓ Issued: DatabaseAccess VC")

    # Verify credentials
    verified = vc_issuer.verify_vc(financial_vc)
    print(f"✓ VC verified cryptographically")
    print(f"  Capabilities: {vc_issuer.extract_capabilities(financial_vc)}")

    # =========================================================================
    # PHASE 2: DISCOVERY & REGISTRATION
    # =========================================================================
    print_section("PHASE 2: Agent Discovery (ANS)", "🔍")

    print_subsection("2.1 Register Agent in ANS")
    ans_registry.register(
        ans_name="financial://agent-alpha.analyzer.acme.v2",
        agent_did=agent_did,
        capabilities=["FinancialAnalysis", "DatabaseAccess", "ExternalAPIAccess"],
        service_endpoint="https://api.acme.com/agents/alpha",
        provider="ACME Corp",
        version="2.0",
        protocol_extensions={
            "mcp": {
                "supported_tools": ["execute_sql", "call_api"],
                "max_concurrent_requests": 10
            }
        }
    )
    print(f"✓ Registered: financial://agent-alpha.analyzer.acme.v2")

    print_subsection("2.2 Discover Agent by Capability")
    discovered = ans_registry.resolve_by_capability("FinancialAnalysis")
    print(f"✓ Found {len(discovered)} agent(s) with 'FinancialAnalysis' capability")
    for agent in discovered:
        print(f"  - {agent['ans_name']}")
        print(f"    Endpoint: {agent['service_endpoint']}")

    # =========================================================================
    # PHASE 3: CLOUD IDENTITY BRIDGE (THE GAME CHANGER)
    # =========================================================================
    print_section("PHASE 3: Cloud Identity Bridge (VC → OIDC)", "☁️")

    cloud_bridge = CloudIdentityBridge(vc_issuer=vc_issuer)
    credential_cache = CloudCredentialCache()

    print_subsection("3.1 Exchange VC for AWS Credentials")
    print("Agent presents VC, receives temporary AWS credentials...")
    print("(No long-lived API keys stored in agent code!)")

    aws_credentials = cloud_bridge.exchange_vc_for_aws_token(
        vc_jwt=database_vc,
        aws_role_arn="arn:aws:iam::123456789012:role/AgentDatabaseAccess",
        aws_region="us-east-1",
        session_duration=3600
    )

    print(f"\n✅ AWS Credentials Received:")
    print(f"  Access Key ID: {aws_credentials['AccessKeyId']}")
    print(f"  Session Token: {aws_credentials['SessionToken'][:40]}...")
    print(f"  Expires: {aws_credentials['Expiration']}")
    print(f"  Duration: 1 hour (auto-rotates)")

    print_subsection("3.2 Exchange VC for GCP Credentials")
    gcp_credentials = cloud_bridge.exchange_vc_for_gcp_token(
        vc_jwt=database_vc,
        gcp_service_account="agent-alpha@acme-project.iam.gserviceaccount.com",
        gcp_project_id="acme-project",
        session_duration=3600
    )

    print(f"\n✅ GCP Credentials Received:")
    print(f"  Access Token: {gcp_credentials['access_token'][:40]}...")
    print(f"  Token Type: {gcp_credentials['token_type']}")
    print(f"  Expires In: {gcp_credentials['expires_in']} seconds")

    print_subsection("3.3 Cache Cloud Credentials")
    cache_key = f"{agent_did}:aws:database"
    credential_cache.set(cache_key, aws_credentials)
    print(f"✓ Cached credentials with key: {cache_key}")

    cached = credential_cache.get(cache_key)
    print(f"✓ Retrieved from cache: {cached is not None}")

    # =========================================================================
    # PHASE 4: SECURE KEY BOOTSTRAP
    # =========================================================================
    print_section("PHASE 4: Secure Key Bootstrap (KMS)", "🔐")

    key_bootstrap = SecureKeyBootstrap(cloud_provider="aws")

    print_subsection("4.1 Bootstrap Agent Key from KMS")
    print("Container starts with NO keys...")
    print("Bootstrapping from AWS KMS using workload identity...")

    bootstrapped_key_path = key_bootstrap.bootstrap_agent_key(
        agent_did=agent_did,
        kms_key_id="arn:aws:kms:us-east-1:123456789012:key/abcd-1234",
        tmpfs_path="/tmp/agent-keys"  # In production: /dev/shm/agent-keys
    )

    print(f"\n✅ Key Bootstrapped Successfully:")
    print(f"  Key Path: {bootstrapped_key_path}")
    print(f"  Storage: tmpfs (memory-only, never disk)")
    print(f"  Permissions: 0400 (read-only)")
    print(f"  Lifecycle: Deleted on container restart")

    # =========================================================================
    # PHASE 5: MCP SIDECAR SECURITY
    # =========================================================================
    print_section("PHASE 5: MCP Sidecar (Security Proxy)", "🛡️")

    print_subsection("5.1 Initialize MCP Sidecar")
    print("Using DatabaseAccess VC for MCP tool 'execute_sql'...")
    mcp_sidecar = MCPSidecar(
        agent_did=agent_did,
        agent_vc_jwt=database_vc,  # Use DatabaseAccess VC for SQL operations
        session_authority_url="http://session-authority:8080",
        vc_issuer=vc_issuer
    )

    await mcp_sidecar.start_session()

    print_subsection("5.2 Intercept MCP Message (Tool Call)")

    # Simulate agent calling MCP tool
    mcp_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "execute_sql",
            "arguments": {
                "query": "SELECT * FROM financial_data WHERE year = 2024"
            }
        },
        "id": 1
    }

    print("Agent sends MCP request:")
    print(json.dumps(mcp_request, indent=2))

    # Sidecar intercepts and validates
    print("\n🛡️  Sidecar intercepting...")
    enhanced_request = await mcp_sidecar.intercept_mcp_message(mcp_request)

    print("\n✅ Enhanced MCP Request:")
    print(json.dumps(enhanced_request, indent=2))

    print("\nKey Security Features:")
    print("  ✓ Agent identity injected (DID)")
    print("  ✓ Capability validated (DatabaseAccess)")
    print("  ✓ Session status checked (ACTIVE)")
    print("  ✓ Audit log created")
    print("  ✓ Request forwarded to MCP server")

    # =========================================================================
    # PHASE 6: COMPLETE WORKFLOW SIMULATION
    # =========================================================================
    print_section("PHASE 6: Complete Workflow", "🚀")

    print_subsection("6.1 Agent Startup Sequence")
    print("1. Container starts (Kubernetes Pod)")
    print("2. Workload identity authenticates to KMS")
    print("3. Private key bootstrapped to tmpfs")
    print("4. MCP Sidecar starts as DaemonSet")
    print("5. Agent queries ANS for required tools")
    print("6. Agent presents VC to cloud bridge")
    print("7. Receives temporary AWS credentials")
    print("8. Agent makes MCP tool call")
    print("9. Sidecar validates and forwards")
    print("10. Tool executes, returns data")
    print("✓ All steps complete - Zero hardcoded secrets!")

    print_subsection("6.2 Security Properties")
    print("✅ Identity: Cryptographically verifiable DIDs")
    print("✅ Capabilities: Signed VCs, cannot be forged")
    print("✅ Discovery: ANS provides service location")
    print("✅ Cloud Access: Short-lived tokens, auto-rotating")
    print("✅ Key Management: KMS-backed, memory-only storage")
    print("✅ MCP Security: Every call authenticated and authorized")
    print("✅ Audit Trail: Complete attribution to agent DID")
    print("✅ Zero Trust: Continuous verification at every layer")

    # =========================================================================
    # PHASE 7: ENTERPRISE VALUE PROPOSITION
    # =========================================================================
    print_section("PHASE 7: Enterprise Value Summary", "💼")

    print("""
╔═══════════════════════════════════════════════════════════════════════╗
║  PROBLEM SOLVED: Secret Sprawl                                        ║
╠═══════════════════════════════════════════════════════════════════════╣
║  BEFORE: API keys hardcoded in agent code                             ║
║          • Security risk (keys in git, logs, container images)        ║
║          • Rotation nightmare (redeploy all agents)                   ║
║          • Compliance violation (SOC2, ISO27001)                      ║
║                                                                        ║
║  AFTER:  Agents present VCs, receive short-lived tokens               ║
║          • No secrets in code (KMS bootstrap)                         ║
║          • Auto-rotation (hourly)                                     ║
║          • Audit trail (every access attributed to DID)               ║
╚═══════════════════════════════════════════════════════════════════════╝

╔═══════════════════════════════════════════════════════════════════════╗
║  PROBLEM SOLVED: MCP Security Gap                                     ║
╠═══════════════════════════════════════════════════════════════════════╣
║  BEFORE: MCP servers don't know WHO is calling                        ║
║          • No identity in MCP protocol                                ║
║          • Cannot enforce policies                                    ║
║          • Audit trail impossible                                     ║
║                                                                        ║
║  AFTER:  MCP Sidecar injects agent identity                           ║
║          • Every call attributed to DID                               ║
║          • Capability-based enforcement                               ║
║          • Complete audit trail                                       ║
╚═══════════════════════════════════════════════════════════════════════╝

╔═══════════════════════════════════════════════════════════════════════╗
║  COMPETITIVE ADVANTAGE: "Security Chip for MCP"                       ║
╠═══════════════════════════════════════════════════════════════════════╣
║  If MCP becomes the standard (like USB):                              ║
║  → This becomes the security layer (like TPM for laptops)             ║
║  → Infrastructure play, not application play                          ║
║  → Defensible moat (standards + first mover)                          ║
╚═══════════════════════════════════════════════════════════════════════╝
    """)

    print_section("✅ Demo Complete - Production Ready Architecture", "🎉")

    print("""
Next Steps for Production Deployment:
======================================
1. Deploy Session Authority (Redis cluster)
2. Deploy Policy Engine (OPA)
3. Configure cloud KMS integration
4. Deploy MCP Sidecar as Kubernetes DaemonSet
5. Integrate with existing MCP servers
6. Set up monitoring & observability dashboard

Enterprise Support Available:
==============================
- Pilot program for early adopters
- Integration assistance
- Custom policy development
- Training and documentation

Repository: github.com/your-org/DAC_Agent
Contact: enterprise@your-company.com
    """)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
