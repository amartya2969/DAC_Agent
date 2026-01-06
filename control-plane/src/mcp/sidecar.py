"""MCP Sidecar - Security Layer for Model Context Protocol.

The "Security Chip" for MCP:
- Intercepts all MCP JSON-RPC messages
- Injects agent identity (DID) into context
- Validates agent capabilities before forwarding
- Logs all MCP interactions for audit
- Enforces session revocation

This runs as a transparent proxy between MCP client and MCP server.

Architecture:
```
MCP Client (Agent)
    ↓
MCP Sidecar (This Code)
    ↓ Validates identity + capabilities
    ↓ Injects DID context
    ↓ Checks session status
MCP Server (Tool)
```
"""
import json
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime


class MCPSidecar:
    """MCP Sidecar - Transparent security proxy for Model Context Protocol.

    Implements the "Sidecar" pattern:
    - Runs alongside the agent container (DaemonSet in K8s)
    - Intercepts MCP traffic without code changes in agent
    - Adds identity and policy enforcement

    This is the DIFFERENTIATOR vs generic HTTP proxies.
    """

    def __init__(
        self,
        agent_did: str,
        agent_vc_jwt: str,
        session_authority_url: str,
        vc_issuer
    ):
        """Initialize MCP Sidecar.

        Args:
            agent_did: Agent's DID
            agent_vc_jwt: Agent's Verifiable Credential (JWT)
            session_authority_url: Session Authority endpoint
            vc_issuer: VC Issuer for verification
        """
        self.agent_did = agent_did
        self.agent_vc = agent_vc_jwt
        self.session_authority_url = session_authority_url
        self.vc_issuer = vc_issuer

        # Extract capabilities from VC
        self.capabilities = vc_issuer.extract_capabilities(agent_vc_jwt)

        # Session state
        self.session_active = True
        self.session_id = None

        print(f"🛡️  MCP Sidecar initialized for agent: {agent_did[:50]}...")
        print(f"   Capabilities: {self.capabilities}")

    async def intercept_mcp_message(self, mcp_message: Dict[str, Any]) -> Dict[str, Any]:
        """Intercept and process MCP JSON-RPC message.

        This is the CORE LOGIC that makes MCP secure.

        Args:
            mcp_message: MCP JSON-RPC message
                {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "execute_sql",
                        "arguments": {...}
                    },
                    "id": 1
                }

        Returns:
            Modified MCP message with identity context injected

        Raises:
            PermissionError: If agent lacks capability or session revoked
        """
        # Step 1: Check session status
        if not await self._check_session_active():
            raise PermissionError(
                f"Session revoked for agent {self.agent_did}. "
                "All MCP access terminated."
            )

        # Step 2: Validate capability for requested tool
        tool_name = mcp_message.get("params", {}).get("name")
        required_capability = self._get_required_capability_for_tool(tool_name)

        if required_capability and required_capability not in self.capabilities:
            raise PermissionError(
                f"Agent lacks capability '{required_capability}' "
                f"required for tool '{tool_name}'"
            )

        # Step 3: Inject identity context into MCP message
        enhanced_message = self._inject_identity_context(mcp_message)

        # Step 4: Log for audit trail
        await self._log_mcp_interaction(enhanced_message)

        print(f"✓ MCP message validated and enhanced")
        print(f"  Tool: {tool_name}")
        print(f"  Capability check: PASSED")

        return enhanced_message

    def _inject_identity_context(self, mcp_message: Dict) -> Dict:
        """Inject agent identity into MCP message.

        This allows MCP servers to:
        - Know which agent is calling
        - Enforce fine-grained policies
        - Attribute actions in logs

        Args:
            mcp_message: Original MCP message

        Returns:
            Enhanced message with identity context
        """
        # Add identity context to params
        if "params" not in mcp_message:
            mcp_message["params"] = {}

        # Inject agent identity metadata (without breaking MCP spec)
        mcp_message["params"]["_agent_identity"] = {
            "did": self.agent_did,
            "capabilities": self.capabilities,
            "session_id": self.session_id,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        return mcp_message

    def _get_required_capability_for_tool(self, tool_name: str) -> Optional[str]:
        """Map MCP tool to required capability.

        This is the policy enforcement layer.

        Args:
            tool_name: MCP tool name (e.g., "execute_sql")

        Returns:
            Required capability or None if no restriction
        """
        # Example policy: Map tools to capabilities
        tool_capability_map = {
            "execute_sql": "DatabaseAccess",
            "read_file": "FileSystemRead",
            "write_file": "FileSystemWrite",
            "call_api": "ExternalAPIAccess",
            "execute_code": "CodeExecution"
        }

        return tool_capability_map.get(tool_name)

    async def _check_session_active(self) -> bool:
        """Check if agent's session is still active.

        In production, this queries the Session Authority (Redis).

        Returns:
            True if session active, False if revoked
        """
        # PRODUCTION: Query Session Authority via HTTP/gRPC
        # response = await http_client.get(
        #     f"{self.session_authority_url}/sessions/{self.agent_did}"
        # )
        # return response["status"] == "ACTIVE"

        # POC: Simulate session check
        return self.session_active

    async def _log_mcp_interaction(self, mcp_message: Dict):
        """Log MCP interaction for audit trail.

        Args:
            mcp_message: MCP message to log
        """
        # In production, send to audit log service
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "agent_did": self.agent_did,
            "tool": mcp_message.get("params", {}).get("name"),
            "method": mcp_message.get("method"),
            "session_id": self.session_id
        }

        # POC: Print to console
        print(f"📝 Audit: {json.dumps(audit_entry, indent=2)}")

    async def start_session(self):
        """Start a session with Session Authority.

        This registers the agent's MCP activity.
        """
        # In production, call Session Authority API
        self.session_id = f"mcp_session_{int(datetime.utcnow().timestamp())}"
        self.session_active = True

        print(f"✓ Session started: {self.session_id}")

    async def terminate_session(self):
        """Terminate session (called on revocation)."""
        self.session_active = False
        print(f"⚠️  Session terminated for {self.agent_did}")


class MCPSidecarServer:
    """MCP Sidecar Server - Runs as standalone process.

    This is the binary that runs in the sidecar container.

    Usage:
    ```bash
    # Start sidecar (runs alongside agent container)
    mcp-sidecar \
        --agent-did did:key:z6Mk... \
        --agent-vc /secrets/agent.vc.jwt \
        --upstream-mcp-server http://mcp-server:8080 \
        --listen-port 9090
    ```

    Agent code remains unchanged:
    ```python
    # Agent connects to localhost:9090 (sidecar)
    # Sidecar forwards to actual MCP server after validation
    mcp_client = MCPClient("http://localhost:9090")
    ```
    """

    def __init__(
        self,
        sidecar: MCPSidecar,
        upstream_mcp_url: str,
        listen_port: int = 9090
    ):
        """Initialize sidecar server.

        Args:
            sidecar: MCPSidecar instance
            upstream_mcp_url: Real MCP server URL
            listen_port: Port to listen on
        """
        self.sidecar = sidecar
        self.upstream_mcp_url = upstream_mcp_url
        self.listen_port = listen_port

    async def handle_client_request(self, mcp_request: Dict) -> Dict:
        """Handle MCP request from agent (client).

        Flow:
        1. Agent sends MCP request to sidecar
        2. Sidecar validates + enhances request
        3. Sidecar forwards to real MCP server
        4. Sidecar returns response to agent

        Args:
            mcp_request: MCP JSON-RPC request from agent

        Returns:
            MCP response from upstream server
        """
        try:
            # Validate and enhance request
            enhanced_request = await self.sidecar.intercept_mcp_message(mcp_request)

            # Forward to upstream MCP server
            response = await self._forward_to_upstream(enhanced_request)

            return response

        except PermissionError as e:
            # Return MCP error response
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32000,  # MCP error code
                    "message": str(e)
                },
                "id": mcp_request.get("id")
            }

    async def _forward_to_upstream(self, mcp_request: Dict) -> Dict:
        """Forward validated request to upstream MCP server.

        Args:
            mcp_request: Enhanced MCP request

        Returns:
            Response from upstream server
        """
        # In production, use aiohttp to forward HTTP request
        # async with aiohttp.ClientSession() as session:
        #     async with session.post(
        #         self.upstream_mcp_url,
        #         json=mcp_request
        #     ) as resp:
        #         return await resp.json()

        # POC: Simulate upstream response
        print(f"📡 Forwarding to upstream MCP server: {self.upstream_mcp_url}")

        return {
            "jsonrpc": "2.0",
            "result": {
                "content": "Simulated MCP tool response",
                "_forwarded_by_sidecar": True
            },
            "id": mcp_request.get("id")
        }

    async def run(self):
        """Start sidecar server (blocking).

        This would be the main() function in production.
        """
        print(f"🚀 MCP Sidecar Server starting on port {self.listen_port}")
        print(f"   Upstream MCP: {self.upstream_mcp_url}")
        print(f"   Agent DID: {self.sidecar.agent_did[:50]}...")

        # In production, start HTTP/WebSocket server
        # await start_http_server(port=self.listen_port)

        print(f"✓ Sidecar ready to intercept MCP traffic")


# Example Kubernetes DaemonSet manifest (YAML)
SIDECAR_DAEMONSET_MANIFEST = """
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: mcp-sidecar
spec:
  selector:
    matchLabels:
      app: mcp-sidecar
  template:
    metadata:
      labels:
        app: mcp-sidecar
    spec:
      containers:
      - name: mcp-sidecar
        image: acme/mcp-sidecar:v1
        ports:
        - containerPort: 9090
        env:
        - name: AGENT_DID
          valueFrom:
            secretKeyRef:
              name: agent-identity
              key: did
        - name: AGENT_VC_JWT
          valueFrom:
            secretKeyRef:
              name: agent-identity
              key: vc
        - name: UPSTREAM_MCP_URL
          value: "http://mcp-server.default.svc.cluster.local:8080"
        - name: SESSION_AUTHORITY_URL
          value: "http://session-authority.default.svc.cluster.local"
        volumeMounts:
        - name: agent-identity
          mountPath: /secrets
          readOnly: true
      volumes:
      - name: agent-identity
        secret:
          secretName: agent-identity
"""
