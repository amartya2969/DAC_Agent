"""AWS OIDC Bridge - Exchange Agent VCs for AWS Temporary Credentials.

This is the "OIDC Integration" layer that solves the "Static Key Problem."
Agents present their internal DAC Passport (VC), and receive short-lived AWS credentials.

This is the CORE VALUE PROPOSITION:
- Before: API keys hardcoded in agent code
- After: Agents trade VCs for 1-hour AWS tokens (auto-rotating)
"""
import boto3
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.identity.vc_issuer import VCIssuer
from src.identity.did_manager import DIDManager


class AWSCredentialAdapter:
    """Bridge between Agent VCs and AWS Temporary Credentials.

    This is the specific code block that proves you solve the 'Secret Sprawl' problem.
    """

    def __init__(self, vc_issuer: VCIssuer, did_manager: DIDManager):
        """Initialize AWS adapter.

        Args:
            vc_issuer: VC Issuer for verifying credentials
            did_manager: DID Manager for identity resolution
        """
        self.vc_issuer = vc_issuer
        self.did_manager = did_manager

        # In production, use actual AWS STS client
        # For demo, we simulate
        self.use_simulation = os.getenv('AWS_SIMULATION', 'true').lower() == 'true'

        if not self.use_simulation:
            self.sts_client = boto3.client('sts')
        else:
            self.sts_client = None

    def exchange_credential(
        self,
        agent_vc_jwt: str,
        user_context: Optional[str],
        target_role_arn: str,
        session_duration_seconds: int = 3600
    ) -> Dict:
        """Exchange Agent VC for AWS Temporary Credentials.

        This is the CRITICAL function that implements the "VC → AWS Token" flow.

        Args:
            agent_vc_jwt: The agent's Verifiable Credential (JWT)
            user_context: Optional user context for attribution
            target_role_arn: AWS IAM Role ARN to assume
            session_duration_seconds: Credential lifetime (default 1 hour)

        Returns:
            AWS Temporary Credentials (AccessKeyId, SecretAccessKey, SessionToken)

        Raises:
            ValueError: If VC verification fails
        """
        # STEP 1: Verify the Agent's Internal Passport (VC)
        print(f"\n🔐 [AWS Bridge] Verifying Agent VC...")

        try:
            verified_payload = self.vc_issuer.verify_vc(agent_vc_jwt)
        except Exception as e:
            raise ValueError(f"Invalid Agent Identity: {str(e)}")

        # Extract agent DID and capabilities
        agent_did = verified_payload.get('sub')
        vc_data = verified_payload.get('vc', {})
        capabilities = vc_data.get('credentialSubject', {}).get('capability', 'Unknown')

        print(f"✓ Agent verified: {agent_did[:60]}...")
        print(f"  Capabilities: {capabilities}")

        # STEP 2: Create session name for attribution
        # This is CRITICAL for audit trails - every AWS action will be attributed to this session
        session_name = self._create_session_name(agent_did, user_context)

        print(f"\n📝 [AWS Bridge] Creating attributed session...")
        print(f"  Session Name: {session_name}")
        print(f"  Role ARN: {target_role_arn}")
        print(f"  Duration: {session_duration_seconds}s ({session_duration_seconds//3600}h)")

        # STEP 3: Generate OIDC token from VC
        # This bridges Web3 (DIDs) to Web2 (OIDC)
        oidc_token = self._generate_oidc_token_from_vc(agent_vc_jwt, agent_did, capabilities)

        # STEP 4: Call AWS STS to assume the role
        if self.use_simulation:
            # Simulated response for demo purposes
            credentials = self._simulate_sts_call(
                role_arn=target_role_arn,
                session_name=session_name,
                duration_seconds=session_duration_seconds
            )
        else:
            # Real AWS STS call
            credentials = self._call_aws_sts(
                oidc_token=oidc_token,
                role_arn=target_role_arn,
                session_name=session_name,
                duration_seconds=session_duration_seconds
            )

        print(f"\n✅ [AWS Bridge] Credentials issued successfully")
        print(f"  Access Key: {credentials['AccessKeyId'][:20]}...")
        print(f"  Expires: {credentials['Expiration']}")
        print(f"  Attribution: {session_name}")

        return credentials

    def _create_session_name(self, agent_did: str, user_context: Optional[str]) -> str:
        """Create session name for AWS attribution.

        Format: agent-<short_did>-<user>-<timestamp>
        This ensures every AWS CloudTrail log shows WHO (agent) did WHAT for WHOM (user).

        Args:
            agent_did: Agent DID
            user_context: Optional user identifier

        Returns:
            Session name (max 64 chars for AWS)
        """
        # Extract short identifier from DID
        did_short = agent_did.split(':')[-1][:16] if ':' in agent_did else agent_did[:16]

        # Add user context if provided
        if user_context:
            user_short = user_context[:16]
            session_name = f"agent-{did_short}-user-{user_short}"
        else:
            session_name = f"agent-{did_short}"

        # Ensure it's valid AWS session name (alphanumeric, =,.@-)
        session_name = session_name.replace(':', '-').replace('/', '-')

        return session_name[:64]  # AWS limit

    def _generate_oidc_token_from_vc(
        self,
        vc_jwt: str,
        agent_did: str,
        capabilities: str
    ) -> str:
        """Generate OIDC-compatible JWT from VC.

        This bridges Web3 (Verifiable Credentials) to Web2 (OIDC).
        AWS expects OIDC format, so we transform our VC into that format.

        Args:
            vc_jwt: Original VC JWT
            agent_did: Agent DID
            capabilities: Agent capabilities

        Returns:
            OIDC-formatted JWT
        """
        # For MVP, we can reuse the VC JWT as OIDC token
        # In production, you'd create a separate OIDC provider
        # and issue proper OIDC tokens

        # The VC already has iss, sub, exp which OIDC requires
        return vc_jwt

    def _simulate_sts_call(
        self,
        role_arn: str,
        session_name: str,
        duration_seconds: int
    ) -> Dict:
        """Simulate AWS STS AssumeRoleWithWebIdentity call.

        Args:
            role_arn: Role ARN
            session_name: Session name
            duration_seconds: Duration

        Returns:
            Simulated AWS credentials
        """
        print(f"\n📡 [SIMULATED] Calling AWS STS AssumeRoleWithWebIdentity")
        print(f"   Role ARN: {role_arn}")
        print(f"   Session: {session_name}")
        print(f"   Duration: {duration_seconds}s")

        expiration = datetime.utcnow() + timedelta(seconds=duration_seconds)

        return {
            'AccessKeyId': f'ASIA_SIMULATED_{session_name[:16].upper()}',
            'SecretAccessKey': f'simulated_secret_key_{hash(session_name) % 10000}',
            'SessionToken': f'simulated_session_token_{session_name}_{int(datetime.utcnow().timestamp())}',
            'Expiration': expiration.isoformat() + 'Z',
            'AssumedRoleUser': {
                'AssumedRoleId': f'AROA_SIMULATED::{session_name}',
                'Arn': f'{role_arn.replace(":role/", ":assumed-role/")}/{session_name}'
            }
        }

    def _call_aws_sts(
        self,
        oidc_token: str,
        role_arn: str,
        session_name: str,
        duration_seconds: int
    ) -> Dict:
        """Call real AWS STS AssumeRoleWithWebIdentity.

        Args:
            oidc_token: OIDC token
            role_arn: Role ARN
            session_name: Session name
            duration_seconds: Duration

        Returns:
            AWS credentials
        """
        print(f"\n📡 Calling AWS STS AssumeRoleWithWebIdentity")

        response = self.sts_client.assume_role_with_web_identity(
            RoleArn=role_arn,
            RoleSessionName=session_name,
            WebIdentityToken=oidc_token,
            DurationSeconds=duration_seconds
        )

        return {
            'AccessKeyId': response['Credentials']['AccessKeyId'],
            'SecretAccessKey': response['Credentials']['SecretAccessKey'],
            'SessionToken': response['Credentials']['SessionToken'],
            'Expiration': response['Credentials']['Expiration'].isoformat() + 'Z',
            'AssumedRoleUser': response['AssumedRoleUser']
        }

    def revoke_session(self, session_name: str) -> bool:
        """Revoke AWS session (surgical kill switch).

        In production, this would:
        1. Add session to DenyList in IAM policy
        2. Trigger immediate credential invalidation

        Args:
            session_name: Session to revoke

        Returns:
            True if revoked successfully
        """
        print(f"\n🔪 [AWS Bridge] Revoking session: {session_name}")

        # In production, you would:
        # 1. Update IAM policy to deny this session
        # 2. Or use AWS STS GetSessionToken with a revocation list

        print(f"✓ Session revoked (simulated)")
        return True


class GCPCredentialAdapter:
    """GCP Workload Identity Bridge.

    Similar to AWS adapter but for GCP.
    """

    def __init__(self, vc_issuer: VCIssuer):
        """Initialize GCP adapter.

        Args:
            vc_issuer: VC Issuer for verification
        """
        self.vc_issuer = vc_issuer
        self.use_simulation = os.getenv('GCP_SIMULATION', 'true').lower() == 'true'

    def exchange_credential(
        self,
        agent_vc_jwt: str,
        service_account_email: str,
        scopes: list = None
    ) -> Dict:
        """Exchange VC for GCP access token.

        Args:
            agent_vc_jwt: Agent VC
            service_account_email: GCP service account
            scopes: OAuth scopes

        Returns:
            GCP access token
        """
        # Verify VC
        verified_payload = self.vc_issuer.verify_vc(agent_vc_jwt)
        agent_did = verified_payload.get('sub')

        print(f"\n🔐 [GCP Bridge] Exchanging VC for GCP token...")
        print(f"  Agent: {agent_did[:60]}...")
        print(f"  Service Account: {service_account_email}")

        if self.use_simulation:
            return {
                'access_token': f'ya29.simulated_gcp_token_{hash(agent_did) % 10000}',
                'token_type': 'Bearer',
                'expires_in': 3600
            }
        else:
            # Real GCP STS call would go here
            # Using google.auth and google.oauth2
            pass


class AzureCredentialAdapter:
    """Azure Managed Identity Bridge.

    Similar to AWS adapter but for Azure.
    """

    def __init__(self, vc_issuer: VCIssuer):
        """Initialize Azure adapter.

        Args:
            vc_issuer: VC Issuer for verification
        """
        self.vc_issuer = vc_issuer
        self.use_simulation = os.getenv('AZURE_SIMULATION', 'true').lower() == 'true'

    def exchange_credential(
        self,
        agent_vc_jwt: str,
        resource_id: str
    ) -> Dict:
        """Exchange VC for Azure access token.

        Args:
            agent_vc_jwt: Agent VC
            resource_id: Azure resource ID

        Returns:
            Azure access token
        """
        # Verify VC
        verified_payload = self.vc_issuer.verify_vc(agent_vc_jwt)
        agent_did = verified_payload.get('sub')

        print(f"\n🔐 [Azure Bridge] Exchanging VC for Azure token...")
        print(f"  Agent: {agent_did[:60]}...")
        print(f"  Resource: {resource_id}")

        if self.use_simulation:
            return {
                'access_token': f'eyJ0eXAi_simulated_azure_token_{hash(agent_did) % 10000}',
                'token_type': 'Bearer',
                'expires_in': 3600,
                'resource': resource_id
            }
        else:
            # Real Azure Managed Identity call would go here
            # Using azure.identity
            pass
