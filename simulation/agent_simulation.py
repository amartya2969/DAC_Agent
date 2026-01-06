"""Mock Agent Simulation - Testing the Sidecar

This script simulates an AI agent trying to:
1. Make HTTP requests (will be intercepted by sidecar)
2. Call MCP tools (will be validated by MCP inspector)
3. Access cloud resources (will get credentials from control plane)

All traffic goes through the sidecar proxy via http_proxy environment variable.
"""
import os
import time
import requests
import json

AGENT_DID = os.getenv('AGENT_DID', 'did:key:zMockAgentForTesting')
CONTROL_PLANE_URL = os.getenv('CONTROL_PLANE_URL', 'http://control-plane:5000')

def print_section(title):
    """Print a formatted section header."""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")

def test_http_request():
    """Test 1: Make a regular HTTP request through sidecar."""
    print_section("TEST 1: HTTP Request via Sidecar")

    print("Attempting to access example.com...")
    print("(This will be intercepted by the sidecar)")

    try:
        # This request will go through the sidecar proxy
        response = requests.get(
            "http://example.com",
            timeout=10,
            proxies={
                'http': os.getenv('http_proxy'),
                'https': os.getenv('https_proxy')
            }
        )

        print(f"✓ Request succeeded!")
        print(f"  Status Code: {response.status_code}")
        print(f"  Content Length: {len(response.content)} bytes")
        print(f"  Headers: {dict(response.headers)}")

    except requests.exceptions.ProxyError as e:
        print(f"⚠️  Proxy error (expected in demo): {e}")
    except Exception as e:
        print(f"❌ Request failed: {e}")

def test_mcp_tool_call():
    """Test 2: Make an MCP tool call (will be inspected by sidecar)."""
    print_section("TEST 2: MCP Tool Call via Sidecar")

    # Simulate an MCP JSON-RPC request
    mcp_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "execute_sql",
            "arguments": {
                "query": "SELECT * FROM users WHERE id = 1"
            }
        },
        "id": 1
    }

    print(f"Calling MCP tool: execute_sql")
    print(f"Request: {json.dumps(mcp_request, indent=2)}")

    try:
        # This would normally go to an MCP server, but will be intercepted
        response = requests.post(
            "http://mcp-server:3000/mcp",
            json=mcp_request,
            headers={"Content-Type": "application/json"},
            timeout=10,
            proxies={
                'http': os.getenv('http_proxy'),
                'https': os.getenv('https_proxy')
            }
        )

        print(f"✓ MCP request processed!")
        print(f"  Response: {response.text}")

    except requests.exceptions.ProxyError as e:
        print(f"⚠️  Proxy error (expected in demo): {e}")
    except Exception as e:
        print(f"❌ MCP request failed: {e}")

def test_circuit_breaker():
    """Test 3: Trigger circuit breaker by exceeding rate limit."""
    print_section("TEST 3: Circuit Breaker Test")

    print("Sending multiple requests to trigger rate limit...")

    for i in range(5):
        try:
            print(f"\nRequest {i+1}/5:")

            # Generate large request to consume bandwidth
            response = requests.get(
                "http://example.com/large-file",
                timeout=5,
                proxies={
                    'http': os.getenv('http_proxy'),
                    'https': os.getenv('https_proxy')
                }
            )

            print(f"  Status: {response.status_code}")

            if response.status_code == 429:
                print(f"  🚫 Circuit Breaker triggered!")
                print(f"     Rate limit exceeded - this is the 'Kill Switch' in action")
                break

        except requests.exceptions.ProxyError:
            print(f"  ⚠️  Proxy error (expected)")
        except Exception as e:
            print(f"  ❌ Error: {e}")

        time.sleep(1)

def test_mcp_high_risk_tool():
    """Test 4: Try to call a high-risk MCP tool (should be blocked)."""
    print_section("TEST 4: High-Risk Tool Blocking")

    # Try to call a destructive tool
    dangerous_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "delete_database",
            "arguments": {
                "database": "production"
            }
        },
        "id": 2
    }

    print(f"⚠️  Attempting to call DANGEROUS tool: delete_database")
    print(f"Request: {json.dumps(dangerous_request, indent=2)}")

    try:
        response = requests.post(
            "http://mcp-server:3000/mcp",
            json=dangerous_request,
            headers={"Content-Type": "application/json"},
            timeout=10,
            proxies={
                'http': os.getenv('http_proxy'),
                'https': os.getenv('https_proxy')
            }
        )

        print(f"Response Status: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code == 403:
            print(f"\n✓ CORRECTLY BLOCKED by sidecar MCP inspector!")
        else:
            print(f"\n❌ Tool was allowed (should have been blocked)")

    except requests.exceptions.ProxyError as e:
        print(f"⚠️  Proxy error (expected in demo): {e}")
    except Exception as e:
        print(f"Error: {e}")

def test_identity_injection():
    """Test 5: Verify agent identity is injected into requests."""
    print_section("TEST 5: Identity Injection")

    print(f"Agent DID: {AGENT_DID}")
    print(f"Making request to see if identity is injected...")

    mcp_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "read_file",
            "arguments": {
                "path": "/tmp/test.txt"
            }
        },
        "id": 3
    }

    try:
        response = requests.post(
            "http://mcp-server:3000/mcp",
            json=mcp_request,
            headers={"Content-Type": "application/json"},
            timeout=10,
            proxies={
                'http': os.getenv('http_proxy'),
                'https': os.getenv('https_proxy')
            }
        )

        print(f"✓ Request sent through sidecar")
        print(f"  The sidecar should have injected X-Agent-DID header")
        print(f"  The MCP server will see WHO is making this request")

    except requests.exceptions.ProxyError as e:
        print(f"⚠️  Proxy error (expected in demo): {e}")
    except Exception as e:
        print(f"Error: {e}")

def main():
    """Run all simulation tests."""
    print("\n")
    print("╔═══════════════════════════════════════════════════════════════════════╗")
    print("║                 DAC AGENT SIMULATION                                  ║")
    print("║                                                                        ║")
    print("║  This mock agent demonstrates the sidecar architecture:               ║")
    print("║  1. All traffic is intercepted by the sidecar                         ║")
    print("║  2. MCP messages are inspected and validated                          ║")
    print("║  3. Circuit breaker enforces rate limits                              ║")
    print("║  4. Agent identity is injected into every request                     ║")
    print("╚═══════════════════════════════════════════════════════════════════════╝")

    print(f"\nAgent Configuration:")
    print(f"  DID: {AGENT_DID}")
    print(f"  Control Plane: {CONTROL_PLANE_URL}")
    print(f"  HTTP Proxy: {os.getenv('http_proxy', 'Not set')}")
    print(f"  HTTPS Proxy: {os.getenv('https_proxy', 'Not set')}")

    # Wait for services to be ready
    print("\nWaiting for services to be ready...")
    time.sleep(5)

    # Run tests
    test_http_request()
    time.sleep(2)

    test_mcp_tool_call()
    time.sleep(2)

    test_circuit_breaker()
    time.sleep(2)

    test_mcp_high_risk_tool()
    time.sleep(2)

    test_identity_injection()

    print("\n")
    print("╔═══════════════════════════════════════════════════════════════════════╗")
    print("║                 SIMULATION COMPLETE                                   ║")
    print("║                                                                        ║")
    print("║  Key Takeaways:                                                       ║")
    print("║  ✓ All agent traffic flows through the sidecar (enforced)            ║")
    print("║  ✓ MCP protocol is inspected and validated                           ║")
    print("║  ✓ Circuit breaker prevents runaway usage                            ║")
    print("║  ✓ Agent identity is attributed to every action                      ║")
    print("║  ✓ Zero hardcoded secrets in agent code                              ║")
    print("╚═══════════════════════════════════════════════════════════════════════╝")
    print("\n")

    # Keep container running for inspection
    print("Simulation complete. Container will stay alive for 1 hour for inspection.")
    print("Press Ctrl+C to exit early.\n")

    try:
        time.sleep(3600)  # 1 hour
    except KeyboardInterrupt:
        print("\nSimulation interrupted by user.")

if __name__ == "__main__":
    main()
