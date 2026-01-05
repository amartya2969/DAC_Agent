"""Cloud Identity Bridge - Exchange VCs for Cloud Provider OIDC Tokens.

This is the CRITICAL enterprise feature that bridges Web3 identity (DIDs/VCs)
to Web2 cloud infrastructure (AWS, GCP, Azure).

The "Magic":
1. Agent presents Verifiable Credential
2. We validate it cryptographically
3. We exchange it for a short-lived cloud token (OIDC/STS)
4. Agent uses cloud token to access cloud resources
5. No long-lived API keys stored in agent code!

This solves the "Secret Sprawl" problem.
"""
import json
import jwt
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional
from src.identity.vc_issuer import VCIssuer


class CloudIdentityBridge:
    """Bridge between Verifiable Credentials and Cloud Provider Identity."""

    def __init__(self, vc_issuer: VCIssuer):
        """Initialize Cloud Identity Bridge.

        Args:
            vc_issuer: VC Issuer for credential verification
        """
        self.vc_issuer = vc_issuer

    def exchange_vc_for_aws_token(
        self,
        vc_jwt: str,
        aws_role_arn: str,
        aws_region: str = "us-east-1",
        session_duration: int = 3600
    ) -> Dict:
        """Exchange Verifiable Credential for AWS STS token.

        This implements the "VC → AWS OIDC" bridge that allows agents
        to access AWS resources without storing long-lived credentials.

        Flow:
        1. Verify VC cryptographically
        2. Extract agent DID and capabilities
        3. Generate JWT with claims AWS expects
        4. Call AWS STS AssumeRoleWithWebIdentity
        5. Return temporary AWS credentials

        Args:
            vc_jwt: Verifiable Credential (JWT format)
            aws_role_arn: AWS IAM Role ARN to assume
            aws_region: AWS region
            session_duration: Token validity in seconds (default 1 hour)

        Returns:
            Dict with AWS temporary credentials:
            {
                "AccessKeyId": "...",
                "SecretAccessKey": "...",
                "SessionToken": "...",
                "Expiration": "2026-01-05T12:00:00Z"
            }

        Raises:
            ValueError: If VC verification fails
        """
        # Step 1: Verify the Verifiable Credential
        verified_payload = self.vc_issuer.verify_vc(vc_jwt)

        agent_did = verified_payload.get("sub")
        vc_data = verified_payload.get("vc", {})
        capabilities = self.vc_issuer.extract_capabilities(vc_jwt)

        print(f"✓ VC verified for agent: {agent_did[:50]}...")
        print(f"  Capabilities: {capabilities}")

        # Step 2: Create OIDC-compatible JWT for AWS
        # AWS expects a JWT with specific claims for AssumeRoleWithWebIdentity
        oidc_token = self._create_oidc_token_for_aws(
            agent_did=agent_did,
            capabilities=capabilities,
            duration=session_duration
        )

        # Step 3: Exchange OIDC token for AWS STS credentials
        # In production, this would call AWS STS AssumeRoleWithWebIdentity
        # For POC, we simulate the response
        aws_credentials = self._call_aws_sts(
            oidc_token=oidc_token,
            role_arn=aws_role_arn,
            region=aws_region,
            duration=session_duration
        )

        return aws_credentials

    def exchange_vc_for_gcp_token(
        self,
        vc_jwt: str,
        gcp_service_account: str,
        gcp_project_id: str,
        session_duration: int = 3600
    ) -> Dict:
        """Exchange Verifiable Credential for GCP Workload Identity token.

        This implements the "VC → GCP OIDC" bridge for Google Cloud.

        Args:
            vc_jwt: Verifiable Credential (JWT format)
            gcp_service_account: GCP service account email
            gcp_project_id: GCP project ID
            session_duration: Token validity in seconds

        Returns:
            Dict with GCP access token:
            {
                "access_token": "...",
                "token_type": "Bearer",
                "expires_in": 3600
            }
        """
        # Verify VC
        verified_payload = self.vc_issuer.verify_vc(vc_jwt)
        agent_did = verified_payload.get("sub")
        capabilities = self.vc_issuer.extract_capabilities(vc_jwt)

        print(f"✓ VC verified for agent: {agent_did[:50]}...")
        print(f"  Capabilities: {capabilities}")

        # Create OIDC token for GCP
        oidc_token = self._create_oidc_token_for_gcp(
            agent_did=agent_did,
            capabilities=capabilities,
            service_account=gcp_service_account,
            duration=session_duration
        )

        # Exchange for GCP token
        gcp_credentials = self._call_gcp_sts(
            oidc_token=oidc_token,
            service_account=gcp_service_account,
            project_id=gcp_project_id
        )

        return gcp_credentials

    def exchange_vc_for_azure_token(
        self,
        vc_jwt: str,
        azure_client_id: str,
        azure_tenant_id: str,
        session_duration: int = 3600
    ) -> Dict:
        """Exchange Verifiable Credential for Azure Managed Identity token.

        Args:
            vc_jwt: Verifiable Credential (JWT format)
            azure_client_id: Azure AD application client ID
            azure_tenant_id: Azure AD tenant ID
            session_duration: Token validity in seconds

        Returns:
            Dict with Azure access token
        """
        # Verify VC
        verified_payload = self.vc_issuer.verify_vc(vc_jwt)
        agent_did = verified_payload.get("sub")
        capabilities = self.vc_issuer.extract_capabilities(vc_jwt)

        print(f"✓ VC verified for agent: {agent_did[:50]}...")

        # Create OIDC token for Azure
        oidc_token = self._create_oidc_token_for_azure(
            agent_did=agent_did,
            capabilities=capabilities,
            client_id=azure_client_id,
            tenant_id=azure_tenant_id,
            duration=session_duration
        )

        # Exchange for Azure token
        azure_credentials = self._call_azure_sts(
            oidc_token=oidc_token,
            client_id=azure_client_id,
            tenant_id=azure_tenant_id
        )

        return azure_credentials

    def _create_oidc_token_for_aws(
        self,
        agent_did: str,
        capabilities: list,
        duration: int
    ) -> str:
        """Create OIDC-compliant JWT for AWS STS.

        AWS AssumeRoleWithWebIdentity expects specific claims.
        """
        now = datetime.utcnow()
        expiration = now + timedelta(seconds=duration)

        # AWS expects these claims
        claims = {
            "iss": "https://agent-identity.example.com",  # Your identity provider
            "sub": agent_did,  # Agent's DID as subject
            "aud": "sts.amazonaws.com",  # AWS STS audience
            "iat": int(now.timestamp()),
            "exp": int(expiration.timestamp()),

            # Custom claims for audit trail
            "agent_did": agent_did,
            "capabilities": capabilities,
            "token_use": "cloud_access"
        }

        # Sign with your identity provider's key
        # In production, use a dedicated OIDC signing key
        token = jwt.encode(claims, "your-oidc-signing-key", algorithm="HS256")

        return token

    def _call_aws_sts(
        self,
        oidc_token: str,
        role_arn: str,
        region: str,
        duration: int
    ) -> Dict:
        """Call AWS STS AssumeRoleWithWebIdentity.

        In production, this uses boto3:

        ```python
        import boto3

        sts_client = boto3.client('sts', region_name=region)
        response = sts_client.assume_role_with_web_identity(
            RoleArn=role_arn,
            RoleSessionName='agent-session',
            WebIdentityToken=oidc_token,
            DurationSeconds=duration
        )
        return response['Credentials']
        ```

        For POC, we simulate the response.
        """
        # PRODUCTION CODE (commented for POC):
        # import boto3
        # sts = boto3.client('sts', region_name=region)
        # response = sts.assume_role_with_web_identity(
        #     RoleArn=role_arn,
        #     RoleSessionName=f'agent-session-{int(datetime.utcnow().timestamp())}',
        #     WebIdentityToken=oidc_token,
        #     DurationSeconds=duration
        # )
        # return response['Credentials']

        # POC SIMULATION:
        print(f"📡 [SIMULATED] Calling AWS STS AssumeRoleWithWebIdentity")
        print(f"   Role ARN: {role_arn}")
        print(f"   Duration: {duration}s")

        return {
            "AccessKeyId": "ASIA_SIMULATED_KEY_ID",
            "SecretAccessKey": "simulated_secret_key",
            "SessionToken": "simulated_session_token_very_long_string...",
            "Expiration": (datetime.utcnow() + timedelta(seconds=duration)).isoformat() + "Z",
            "_note": "SIMULATED - In production, this comes from AWS STS"
        }

    def _create_oidc_token_for_gcp(
        self,
        agent_did: str,
        capabilities: list,
        service_account: str,
        duration: int
    ) -> str:
        """Create OIDC token for GCP Workload Identity."""
        now = datetime.utcnow()
        expiration = now + timedelta(seconds=duration)

        claims = {
            "iss": "https://agent-identity.example.com",
            "sub": agent_did,
            "aud": f"https://iam.googleapis.com/{service_account}",
            "iat": int(now.timestamp()),
            "exp": int(expiration.timestamp()),
            "agent_did": agent_did,
            "capabilities": capabilities
        }

        token = jwt.encode(claims, "your-oidc-signing-key", algorithm="HS256")
        return token

    def _call_gcp_sts(
        self,
        oidc_token: str,
        service_account: str,
        project_id: str
    ) -> Dict:
        """Call GCP STS (Security Token Service).

        Production code would use:
        ```python
        from google.auth import sts

        credentials = sts.Credentials(
            subject_token=oidc_token,
            subject_token_type='urn:ietf:params:oauth:token-type:jwt',
            audience=f'//iam.googleapis.com/projects/{project_id}/...'
        )
        credentials.refresh(Request())
        return {'access_token': credentials.token, ...}
        ```
        """
        print(f"📡 [SIMULATED] Calling GCP STS")
        print(f"   Service Account: {service_account}")

        return {
            "access_token": "ya29.simulated_gcp_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "_note": "SIMULATED - In production, this comes from GCP STS"
        }

    def _create_oidc_token_for_azure(
        self,
        agent_did: str,
        capabilities: list,
        client_id: str,
        tenant_id: str,
        duration: int
    ) -> str:
        """Create OIDC token for Azure AD."""
        now = datetime.utcnow()
        expiration = now + timedelta(seconds=duration)

        claims = {
            "iss": "https://agent-identity.example.com",
            "sub": agent_did,
            "aud": f"https://login.microsoftonline.com/{tenant_id}/v2.0",
            "iat": int(now.timestamp()),
            "exp": int(expiration.timestamp()),
            "client_id": client_id,
            "agent_did": agent_did,
            "capabilities": capabilities
        }

        token = jwt.encode(claims, "your-oidc-signing-key", algorithm="HS256")
        return token

    def _call_azure_sts(
        self,
        oidc_token: str,
        client_id: str,
        tenant_id: str
    ) -> Dict:
        """Call Azure AD token endpoint.

        Production: Use Azure Identity SDK
        """
        print(f"📡 [SIMULATED] Calling Azure AD")
        print(f"   Tenant: {tenant_id}")

        return {
            "access_token": "eyJ_simulated_azure_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "_note": "SIMULATED - In production, this comes from Azure AD"
        }


class CloudCredentialCache:
    """Cache cloud credentials to avoid repeated STS calls.

    Implements LRU cache with TTL awareness.
    """

    def __init__(self, max_size: int = 100):
        """Initialize cache.

        Args:
            max_size: Maximum number of cached credentials
        """
        self.cache = {}
        self.max_size = max_size

    def get(self, cache_key: str) -> Optional[Dict]:
        """Get cached credentials if not expired.

        Args:
            cache_key: Unique key (e.g., agent_did + role_arn)

        Returns:
            Cached credentials or None if expired/missing
        """
        if cache_key not in self.cache:
            return None

        entry = self.cache[cache_key]
        expiration = datetime.fromisoformat(entry["Expiration"].replace("Z", ""))

        # Return if still valid (with 5-minute buffer)
        if datetime.utcnow() < expiration - timedelta(minutes=5):
            return entry

        # Expired, remove from cache
        del self.cache[cache_key]
        return None

    def set(self, cache_key: str, credentials: Dict):
        """Cache credentials.

        Args:
            cache_key: Unique key
            credentials: Cloud credentials to cache
        """
        # Simple LRU: if full, remove oldest
        if len(self.cache) >= self.max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]

        self.cache[cache_key] = credentials
