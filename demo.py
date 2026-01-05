"""Demo script for Agentic AI Identity Management Framework.

This demonstrates:
1. Creating agent identities (DIDs)
2. Issuing verifiable credentials
3. Registering agents in ANS
4. Discovering agents by capability
5. Verifying credentials
"""
import sys
sys.path.insert(0, '.')

from src.identity.did_manager import DIDManager
from src.identity.vc_issuer import VCIssuer
from src.ans.registry import ANSRegistry, ANSResolver


def print_section(title):
    """Print section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def main():
    print("\n🚀 Agentic AI Identity Management Framework - Demo\n")

    # Initialize components
    print_section("1. Initialize Framework Components")
    did_manager = DIDManager()
    vc_issuer = VCIssuer(did_manager=did_manager)
    ans_registry = ANSRegistry()
    ans_resolver = ANSResolver(ans_registry)
    print("✓ DID Manager initialized")
    print("✓ VC Issuer initialized")
    print("✓ ANS Registry initialized")

    # Create trusted issuer identity
    print_section("2. Create Trusted Issuer Identity")
    issuer_result = did_manager.create_did(
        agent_name="ACME Trust Authority",
        metadata={
            "model": "system",
            "provider": "ACME Corp",
            "capabilities": ["CredentialIssuance"],
            "scopeOfBehavior": "Issues capability and compliance credentials for ACME agents"
        }
    )
    issuer_did = issuer_result["did"]
    issuer_key = issuer_result["private_key_pem"]
    print(f"✓ Issuer DID: {issuer_did[:50]}...")

    # Create Agent 1: Financial Analyzer
    print_section("3. Create Agent: Financial Analyzer")
    agent1_result = did_manager.create_did(
        agent_name="Agent Alpha - Financial Analyzer",
        metadata={
            "model": "gpt-4-turbo",
            "version": "1.0",
            "provider": "ACME Corp",
            "capabilities": ["FinancialAnalysis", "RiskAssessment"],
            "scopeOfBehavior": "Analyzes financial data and assesses investment risks"
        }
    )
    agent1_did = agent1_result["did"]
    agent1_key = agent1_result["private_key_pem"]
    print(f"✓ Agent DID: {agent1_did[:50]}...")
    print(f"✓ Capabilities: FinancialAnalysis, RiskAssessment")

    # Create Agent 2: Data Processor
    print_section("4. Create Agent: Data Processor")
    agent2_result = did_manager.create_did(
        agent_name="Agent Beta - Data Processor",
        metadata={
            "model": "claude-3-opus",
            "version": "1.0",
            "provider": "ACME Corp",
            "capabilities": ["DataProcessing", "DataTransformation"],
            "scopeOfBehavior": "Processes and transforms large datasets"
        }
    )
    agent2_did = agent2_result["did"]
    print(f"✓ Agent DID: {agent2_did[:50]}...")
    print(f"✓ Capabilities: DataProcessing, DataTransformation")

    # Issue capability credentials
    print_section("5. Issue Verifiable Credentials")

    # Issue FinancialAnalysis capability to Agent 1
    vc1 = vc_issuer.issue_capability_vc(
        issuer_did=issuer_did,
        issuer_private_key_pem=issuer_key,
        subject_did=agent1_did,
        capability="FinancialAnalysis",
        validity_days=365
    )
    print(f"✓ Issued 'FinancialAnalysis' VC to Agent Alpha")
    print(f"  VC (first 80 chars): {vc1[:80]}...")

    # Issue DataProcessing capability to Agent 2
    vc2 = vc_issuer.issue_capability_vc(
        issuer_did=issuer_did,
        issuer_private_key_pem=issuer_key,
        subject_did=agent2_did,
        capability="DataProcessing",
        validity_days=365
    )
    print(f"✓ Issued 'DataProcessing' VC to Agent Beta")

    # Verify credentials
    print_section("6. Verify Credentials")
    verified1 = vc_issuer.verify_vc(vc1, expected_issuer_did=issuer_did)
    print(f"✓ VC1 verified successfully")
    print(f"  Subject: {verified1['sub'][:50]}...")
    print(f"  Capabilities: {vc_issuer.extract_capabilities(vc1)}")

    verified2 = vc_issuer.verify_vc(vc2, expected_issuer_did=issuer_did)
    print(f"✓ VC2 verified successfully")
    print(f"  Capabilities: {vc_issuer.extract_capabilities(vc2)}")

    # Register agents in ANS
    print_section("7. Register Agents in ANS (Agent Naming Service)")

    ans_registry.register(
        ans_name="financial://agent-alpha.analysis.acme.v1",
        agent_did=agent1_did,
        capabilities=["FinancialAnalysis", "RiskAssessment"],
        service_endpoint="https://api.acme.com/agents/alpha",
        provider="ACME Corp",
        version="1.0"
    )
    print("✓ Registered: financial://agent-alpha.analysis.acme.v1")

    ans_registry.register(
        ans_name="data://agent-beta.processor.acme.v1",
        agent_did=agent2_did,
        capabilities=["DataProcessing", "DataTransformation"],
        service_endpoint="https://api.acme.com/agents/beta",
        provider="ACME Corp",
        version="1.0"
    )
    print("✓ Registered: data://agent-beta.processor.acme.v1")

    # Discover agents by capability
    print_section("8. Discover Agents by Capability")

    financial_agents = ans_registry.resolve_by_capability("FinancialAnalysis")
    print(f"✓ Found {len(financial_agents)} agent(s) with 'FinancialAnalysis' capability:")
    for agent in financial_agents:
        print(f"  - {agent['ans_name']}")
        print(f"    DID: {agent['agent_did'][:50]}...")
        print(f"    Endpoint: {agent['service_endpoint']}")

    data_agents = ans_registry.resolve_by_capability("DataProcessing")
    print(f"\n✓ Found {len(data_agents)} agent(s) with 'DataProcessing' capability:")
    for agent in data_agents:
        print(f"  - {agent['ans_name']}")

    # Resolve specific ANS name
    print_section("9. Resolve Specific ANS Name")
    agent_details = ans_registry.resolve("financial://agent-alpha.analysis.acme.v1")
    if agent_details:
        print("✓ Resolved: financial://agent-alpha.analysis.acme.v1")
        print(f"  DID: {agent_details['agent_did'][:50]}...")
        print(f"  Capabilities: {', '.join(agent_details['capabilities'])}")
        print(f"  Provider: {agent_details['provider']}")
        print(f"  Version: {agent_details['version']}")

    # Demonstrate JIT credential
    print_section("10. Issue Just-In-Time (Ephemeral) Credential")

    # Create ephemeral agent
    ephemeral_result = did_manager.create_did(
        agent_name="Ephemeral Task Agent",
        metadata={
            "model": "gpt-3.5-turbo",
            "provider": "ACME Corp",
            "capabilities": []  # No permanent capabilities
        }
    )
    ephemeral_did = ephemeral_result["did"]
    print(f"✓ Created ephemeral agent: {ephemeral_did[:50]}...")

    # Agent Alpha issues JIT credential to ephemeral agent
    jit_vc = vc_issuer.issue_jit_vc(
        issuer_did=agent1_did,  # Agent Alpha delegates
        issuer_private_key_pem=agent1_key,
        subject_did=ephemeral_did,
        scopes=["read:data", "process:batch"],
        validity_minutes=15,
        max_usage_count=1,
        allowed_resources=["/api/financial-data/batch-123"]
    )
    print(f"✓ Issued JIT credential (valid for 15 minutes, single-use)")
    print(f"  Scopes: read:data, process:batch")
    print(f"  Max usage: 1 time")

    # Verify JIT credential
    verified_jit = vc_issuer.verify_vc(jit_vc)
    jit_capabilities = vc_issuer.extract_capabilities(jit_vc)
    print(f"✓ JIT VC verified")
    print(f"  Granted scopes: {jit_capabilities}")

    # Summary
    print_section("✅ Demo Complete - Summary")
    print(f"""
    Created Components:
    • 1 Trusted Issuer: {issuer_did[:40]}...
    • 2 Permanent Agents: Alpha (Financial), Beta (Data)
    • 1 Ephemeral Agent: For temporary task

    Issued Credentials:
    • 2 Capability VCs (FinancialAnalysis, DataProcessing)
    • 1 JIT VC (ephemeral, 15-minute validity)

    ANS Registrations:
    • financial://agent-alpha.analysis.acme.v1
    • data://agent-beta.processor.acme.v1

    Key Features Demonstrated:
    ✓ Decentralized Identity (did:key method)
    ✓ Verifiable Credentials (JWT with Ed25519)
    ✓ Agent Naming Service (DNS-like discovery)
    ✓ Capability-based discovery
    ✓ Just-In-Time credentials for delegation
    """)

    print("\n" + "=" * 70)
    print("  Framework is ready for integration with:")
    print("  • Session Management (Redis)")
    print("  • Policy Decision Point (OPA)")
    print("  • HTTP AEM Adapter")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
