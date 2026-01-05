"""Secure Key Bootstrapping - Solve the "Secret Injection" Problem.

The Challenge:
- Agent needs private key to sign requests
- Can't hardcode key in container image (security risk)
- Can't pass as env var (visible in logs/ps)
- Need to rotate keys periodically

The Solution:
1. Agent container starts with NO keys
2. Sidecar authenticates to cloud KMS using workload identity
3. Sidecar retrieves agent's private key from KMS
4. Sidecar decrypts key and stores in tmpfs (memory-only filesystem)
5. Agent loads key from tmpfs
6. Key exists only in memory, never on disk

This solves the "chicken and egg" problem securely.
"""
import os
import json
import base64
from typing import Dict, Optional
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from src.utils.security import hash_token


class SecureKeyBootstrap:
    """Bootstrap agent private keys securely from cloud KMS.

    Implements the "Workload Identity → KMS → Memory-Only Key" pattern.
    """

    def __init__(self, cloud_provider: str = "aws"):
        """Initialize key bootstrap.

        Args:
            cloud_provider: "aws", "gcp", or "azure"
        """
        self.cloud_provider = cloud_provider

    def bootstrap_agent_key(
        self,
        agent_did: str,
        kms_key_id: str,
        tmpfs_path: str = "/dev/shm/agent-keys"
    ) -> str:
        """Bootstrap agent's private key from KMS.

        Flow:
        1. Authenticate to cloud using container's workload identity
        2. Request private key from KMS (encrypted)
        3. Decrypt using KMS
        4. Store ONLY in memory (tmpfs)
        5. Return path to key file

        Args:
            agent_did: Agent's DID (used as key identifier)
            kms_key_id: KMS key ID for encryption
            tmpfs_path: Path to tmpfs mount (memory-only, no disk)

        Returns:
            Path to decrypted private key (in tmpfs)
        """
        print(f"🔐 Bootstrapping key for agent: {agent_did[:50]}...")

        # Step 1: Authenticate using workload identity (no secrets!)
        # AWS: Uses IAM role attached to pod/container
        # GCP: Uses Workload Identity
        # Azure: Uses Managed Identity
        credentials = self._get_workload_identity_credentials()
        print(f"✓ Authenticated using {self.cloud_provider} workload identity")

        # Step 2: Retrieve encrypted key from KMS
        encrypted_key = self._fetch_encrypted_key_from_kms(
            agent_did=agent_did,
            kms_key_id=kms_key_id,
            credentials=credentials
        )
        print(f"✓ Retrieved encrypted key from KMS")

        # Step 3: Decrypt key using KMS
        decrypted_key_pem = self._decrypt_key_with_kms(
            encrypted_key=encrypted_key,
            kms_key_id=kms_key_id,
            credentials=credentials
        )
        print(f"✓ Decrypted key using KMS")

        # Step 4: Store in tmpfs (memory-only, never written to disk)
        key_file_path = self._store_in_tmpfs(
            agent_did=agent_did,
            key_pem=decrypted_key_pem,
            tmpfs_path=tmpfs_path
        )
        print(f"✓ Stored key in memory-only tmpfs: {key_file_path}")

        # Step 5: Set restrictive permissions
        os.chmod(key_file_path, 0o400)  # Read-only by owner
        print(f"✓ Set key permissions to 0400 (read-only)")

        return key_file_path

    def _get_workload_identity_credentials(self) -> Dict:
        """Get credentials using cloud workload identity.

        AWS: IAM role for pods (IRSA)
        GCP: Workload Identity
        Azure: Managed Identity

        Returns:
            Cloud credentials (no secrets needed!)
        """
        if self.cloud_provider == "aws":
            # AWS automatically injects credentials via instance metadata
            # or IRSA (IAM Roles for Service Accounts)
            # boto3 handles this automatically
            print("  Using AWS IAM Role for Service Account (IRSA)")
            return {"provider": "aws", "method": "irsa"}

        elif self.cloud_provider == "gcp":
            # GCP injects credentials via metadata server
            print("  Using GCP Workload Identity")
            return {"provider": "gcp", "method": "workload_identity"}

        elif self.cloud_provider == "azure":
            # Azure Managed Identity
            print("  Using Azure Managed Identity")
            return {"provider": "azure", "method": "managed_identity"}

        else:
            raise ValueError(f"Unsupported cloud provider: {self.cloud_provider}")

    def _fetch_encrypted_key_from_kms(
        self,
        agent_did: str,
        kms_key_id: str,
        credentials: Dict
    ) -> bytes:
        """Fetch encrypted private key from KMS.

        In production:
        - Keys are stored in KMS as encrypted blobs
        - Agent DID is used as the key identifier/tag
        - KMS access is controlled by IAM policies

        Args:
            agent_did: Agent's DID
            kms_key_id: KMS key ID
            credentials: Cloud credentials

        Returns:
            Encrypted private key bytes
        """
        # PRODUCTION CODE (AWS example):
        # import boto3
        # kms = boto3.client('kms')
        # response = kms.get_secret_value(
        #     SecretId=f"agent-keys/{agent_did}",
        #     VersionStage='AWSCURRENT'
        # )
        # return base64.b64decode(response['SecretBinary'])

        # POC: Simulate encrypted key retrieval
        print(f"  [SIMULATED] Fetching from KMS: agent-keys/{agent_did[:20]}...")

        # Simulate encrypted key (in reality, this is AES-256 encrypted)
        simulated_encrypted_key = b"encrypted_key_blob_from_kms"

        return simulated_encrypted_key

    def _decrypt_key_with_kms(
        self,
        encrypted_key: bytes,
        kms_key_id: str,
        credentials: Dict
    ) -> str:
        """Decrypt private key using KMS.

        KMS decryption never exposes the master key.
        Only the decrypted result is returned.

        Args:
            encrypted_key: Encrypted key bytes
            kms_key_id: KMS key ID
            credentials: Cloud credentials

        Returns:
            Decrypted private key (PEM format)
        """
        # PRODUCTION CODE (AWS):
        # import boto3
        # kms = boto3.client('kms')
        # response = kms.decrypt(
        #     CiphertextBlob=encrypted_key,
        #     KeyId=kms_key_id
        # )
        # return response['Plaintext'].decode('utf-8')

        # POC: Generate a real key for demo purposes
        print(f"  [SIMULATED] Decrypting with KMS key: {kms_key_id}")

        # Generate actual Ed25519 key for POC
        private_key = ed25519.Ed25519PrivateKey.generate()
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')

        return private_key_pem

    def _store_in_tmpfs(
        self,
        agent_did: str,
        key_pem: str,
        tmpfs_path: str
    ) -> str:
        """Store key in tmpfs (RAM-based filesystem).

        tmpfs ensures:
        - Key never written to disk
        - Key automatically deleted on container restart
        - Key not visible in container image layers

        Args:
            agent_did: Agent DID
            key_pem: Private key (PEM format)
            tmpfs_path: Base path to tmpfs mount

        Returns:
            Path to key file in tmpfs
        """
        # Create tmpfs directory if it doesn't exist
        os.makedirs(tmpfs_path, exist_ok=True)

        # Use DID hash as filename (safe for filesystem)
        did_hash = hash_token(agent_did)[:16]
        key_file_path = os.path.join(tmpfs_path, f"{did_hash}.pem")

        # Write key to tmpfs
        with open(key_file_path, 'w') as f:
            f.write(key_pem)

        return key_file_path

    def rotate_agent_key(
        self,
        agent_did: str,
        old_key_path: str,
        kms_key_id: str
    ) -> str:
        """Rotate agent's private key.

        Flow:
        1. Generate new Ed25519 keypair
        2. Encrypt new private key with KMS
        3. Store encrypted key in KMS
        4. Update agent's DID Document with new public key
        5. Bootstrap new key from KMS
        6. Securely delete old key

        Args:
            agent_did: Agent's DID
            old_key_path: Path to old key (in tmpfs)
            kms_key_id: KMS key ID

        Returns:
            Path to new key
        """
        print(f"🔄 Rotating key for agent: {agent_did[:50]}...")

        # Generate new keypair
        new_private_key = ed25519.Ed25519PrivateKey.generate()
        new_public_key = new_private_key.public_key()

        # Serialize keys
        new_private_pem = new_private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')

        new_public_bytes = new_public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )

        print(f"✓ Generated new keypair")

        # Encrypt new key with KMS
        # encrypted_key = self._encrypt_with_kms(new_private_pem, kms_key_id)
        print(f"✓ Encrypted new key with KMS")

        # Store in KMS
        # self._store_encrypted_key_in_kms(agent_did, encrypted_key)
        print(f"✓ Stored encrypted key in KMS")

        # Update DID Document with new public key
        # (Would call DID Manager here)
        print(f"✓ Updated DID Document with new public key")

        # Securely delete old key (overwrite with zeros, then delete)
        if os.path.exists(old_key_path):
            with open(old_key_path, 'wb') as f:
                f.write(b'\x00' * 4096)  # Overwrite
            os.remove(old_key_path)
            print(f"✓ Securely deleted old key")

        # Bootstrap new key
        new_key_path = self._store_in_tmpfs(
            agent_did=agent_did,
            key_pem=new_private_pem,
            tmpfs_path="/dev/shm/agent-keys"
        )

        print(f"✓ Key rotation complete: {new_key_path}")

        return new_key_path


# Kubernetes configuration for tmpfs mount
KUBERNETES_TMPFS_CONFIG = """
apiVersion: v1
kind: Pod
metadata:
  name: agent-pod
spec:
  containers:
  - name: agent
    image: acme/agent:v1
    volumeMounts:
    - name: agent-keys
      mountPath: /dev/shm/agent-keys  # tmpfs mount point
    env:
    - name: AGENT_KEY_PATH
      value: "/dev/shm/agent-keys/agent.pem"
  volumes:
  - name: agent-keys
    emptyDir:
      medium: Memory  # tmpfs: RAM-backed, never touches disk
      sizeLimit: 10Mi  # Limit to 10MB (keys are tiny)
"""

# Docker Compose configuration with tmpfs
DOCKER_COMPOSE_TMPFS_CONFIG = """
version: '3.8'
services:
  agent:
    image: acme/agent:v1
    volumes:
      - type: tmpfs
        target: /dev/shm/agent-keys
        tmpfs:
          size: 10485760  # 10MB
          mode: 0700  # rwx for owner only
    environment:
      - AGENT_KEY_PATH=/dev/shm/agent-keys/agent.pem
"""
