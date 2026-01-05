"""Verifiable Credentials Issuer and Verifier.

Handles issuing and verifying VCs in JWT format with Ed25519 signatures.
"""
import json
import jwt
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization


class VCIssuer:
    """Issue and verify Verifiable Credentials."""

    def __init__(self, did_manager=None):
        """Initialize VC Issuer.

        Args:
            did_manager: DIDManager instance for resolving DIDs
        """
        self.did_manager = did_manager

    def issue_capability_vc(
        self,
        issuer_did: str,
        issuer_private_key_pem: str,
        subject_did: str,
        capability: str,
        validity_days: int = 365,
        constraints: Optional[Dict] = None
    ) -> str:
        """Issue a Capability Verifiable Credential.

        Args:
            issuer_did: DID of the issuer
            issuer_private_key_pem: Private key of issuer (PEM format)
            subject_did: DID of the agent receiving the capability
            capability: Capability name (e.g., "FinancialAnalysis")
            validity_days: Number of days the VC is valid
            constraints: Optional constraints (resources, actions, etc.)

        Returns:
            JWT-encoded VC
        """
        vc = self._create_vc(
            issuer_did=issuer_did,
            subject_did=subject_did,
            vc_type="CapabilityCredential",
            claims={"capability": capability},
            validity_days=validity_days,
            constraints=constraints
        )

        return self._sign_vc(vc, issuer_private_key_pem)

    def issue_role_vc(
        self,
        issuer_did: str,
        issuer_private_key_pem: str,
        subject_did: str,
        role: str,
        validity_days: int = 365,
        constraints: Optional[Dict] = None
    ) -> str:
        """Issue a Role Verifiable Credential.

        Args:
            issuer_did: DID of the issuer
            issuer_private_key_pem: Private key of issuer (PEM format)
            subject_did: DID of the agent receiving the role
            role: Role name (e.g., "DataProcessor", "Orchestrator")
            validity_days: Number of days the VC is valid
            constraints: Optional constraints

        Returns:
            JWT-encoded VC
        """
        vc = self._create_vc(
            issuer_did=issuer_did,
            subject_did=subject_did,
            vc_type="RoleCredential",
            claims={"role": role},
            validity_days=validity_days,
            constraints=constraints
        )

        return self._sign_vc(vc, issuer_private_key_pem)

    def issue_jit_vc(
        self,
        issuer_did: str,
        issuer_private_key_pem: str,
        subject_did: str,
        scopes: List[str],
        validity_minutes: int = 15,
        max_usage_count: int = 1,
        allowed_resources: Optional[List[str]] = None
    ) -> str:
        """Issue a Just-In-Time (ephemeral) Verifiable Credential.

        Args:
            issuer_did: DID of the issuer (usually orchestrator agent)
            issuer_private_key_pem: Private key of issuer
            subject_did: DID of the ephemeral agent
            scopes: List of allowed scopes
            validity_minutes: Minutes until expiration (default 15)
            max_usage_count: Maximum number of times this can be used
            allowed_resources: List of specific resources allowed

        Returns:
            JWT-encoded JIT VC
        """
        constraints = {
            "maxUsageCount": max_usage_count,
            "allowedResources": allowed_resources or [],
            "scopes": scopes
        }

        vc = self._create_vc(
            issuer_did=issuer_did,
            subject_did=subject_did,
            vc_type="JITCredential",
            claims={"scopes": scopes, "ephemeral": True},
            validity_days=validity_minutes / (60 * 24),  # Convert to fractional days
            constraints=constraints
        )

        return self._sign_vc(vc, issuer_private_key_pem)

    def _create_vc(
        self,
        issuer_did: str,
        subject_did: str,
        vc_type: str,
        claims: Dict,
        validity_days: float,
        constraints: Optional[Dict]
    ) -> Dict:
        """Create VC structure.

        Args:
            issuer_did: Issuer DID
            subject_did: Subject DID
            vc_type: Type of credential
            claims: Claims to include
            validity_days: Validity period
            constraints: Optional constraints

        Returns:
            VC structure (before signing)
        """
        now = datetime.utcnow()
        expiration = now + timedelta(days=validity_days)

        credential_subject = {
            "id": subject_did,
            **claims
        }

        if constraints:
            credential_subject["constraints"] = constraints

        vc = {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://w3id.org/security/suites/ed25519-2020/v1"
            ],
            "type": ["VerifiableCredential", vc_type],
            "issuer": issuer_did,
            "issuanceDate": now.isoformat() + "Z",
            "expirationDate": expiration.isoformat() + "Z",
            "credentialSubject": credential_subject
        }

        return vc

    def _sign_vc(self, vc: Dict, private_key_pem: str) -> str:
        """Sign VC with Ed25519 key and encode as JWT.

        Args:
            vc: VC structure
            private_key_pem: Private key in PEM format

        Returns:
            JWT-encoded VC
        """
        # Load private key
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode(),
            password=None
        )

        # Create JWT payload
        # Convert datetime to timestamp
        iat = datetime.fromisoformat(vc["issuanceDate"].replace("Z", ""))
        exp = datetime.fromisoformat(vc["expirationDate"].replace("Z", ""))

        payload = {
            "vc": vc,
            "iss": vc["issuer"],
            "sub": vc["credentialSubject"]["id"],
            "iat": int(iat.timestamp()),
            "exp": int(exp.timestamp())
        }

        # Sign with EdDSA (Ed25519)
        token = jwt.encode(
            payload,
            private_key,
            algorithm="EdDSA"
        )

        return token

    def verify_vc(self, vc_jwt: str, expected_issuer_did: Optional[str] = None) -> Dict:
        """Verify a VC JWT.

        Args:
            vc_jwt: JWT-encoded VC
            expected_issuer_did: Optional DID to verify issuer

        Returns:
            Decoded and verified VC payload

        Raises:
            ValueError: If verification fails
        """
        # Decode without verification first to get issuer DID
        unverified = jwt.decode(vc_jwt, options={"verify_signature": False})
        issuer_did = unverified.get("iss")

        if expected_issuer_did and issuer_did != expected_issuer_did:
            raise ValueError(f"Issuer mismatch: expected {expected_issuer_did}, got {issuer_did}")

        # Get public key from issuer DID
        if not self.did_manager:
            raise ValueError("DIDManager required for verification")

        public_key_bytes = self.did_manager.get_public_key_from_did(issuer_did)
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)

        # Verify signature with clock skew tolerance
        try:
            payload = jwt.decode(
                vc_jwt,
                public_key,
                algorithms=["EdDSA"],
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "leeway": 10  # Allow 10 seconds of clock skew
                }
            )
        except jwt.ExpiredSignatureError:
            raise ValueError("VC has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid VC: {str(e)}")

        return payload

    def extract_capabilities(self, vc_jwt: str) -> List[str]:
        """Extract capabilities from a VC.

        Args:
            vc_jwt: JWT-encoded VC

        Returns:
            List of capability names
        """
        payload = self.verify_vc(vc_jwt)
        vc = payload.get("vc", {})
        cred_subject = vc.get("credentialSubject", {})

        capabilities = []

        # Check for capability claim
        if "capability" in cred_subject:
            capabilities.append(cred_subject["capability"])

        # Check for scopes (JIT credentials)
        if "scopes" in cred_subject:
            capabilities.extend(cred_subject["scopes"])

        return capabilities

    def is_vc_valid(self, vc_jwt: str) -> bool:
        """Check if VC is valid (not expired, valid signature).

        Args:
            vc_jwt: JWT-encoded VC

        Returns:
            True if valid, False otherwise
        """
        try:
            self.verify_vc(vc_jwt)
            return True
        except Exception:
            return False


class VCRevocationList:
    """Manage revoked VCs (simple in-memory list for MVP)."""

    def __init__(self):
        """Initialize revocation list."""
        self.revoked = set()

    def revoke(self, vc_id: str):
        """Add VC to revocation list.

        Args:
            vc_id: Unique identifier of the VC
        """
        self.revoked.add(vc_id)

    def is_revoked(self, vc_id: str) -> bool:
        """Check if VC is revoked.

        Args:
            vc_id: VC identifier

        Returns:
            True if revoked, False otherwise
        """
        return vc_id in self.revoked

    def unrevoke(self, vc_id: str):
        """Remove VC from revocation list (for testing).

        Args:
            vc_id: VC identifier
        """
        self.revoked.discard(vc_id)
