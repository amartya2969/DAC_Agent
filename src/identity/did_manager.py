"""DID Manager for creating and resolving Decentralized Identifiers.

Supports did:key method for Ed25519 keys.
"""
import base58
import hashlib
import json
from datetime import datetime
from typing import Dict, Optional
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization


class DIDManager:
    """Manage DID creation, resolution, and DID Documents."""

    def __init__(self, storage_path: str = "data/dids"):
        """Initialize DID Manager.

        Args:
            storage_path: Directory to store DID Documents
        """
        self.storage_path = storage_path
        import os
        os.makedirs(storage_path, exist_ok=True)

    def create_did(self, agent_name: str, metadata: Optional[Dict] = None) -> Dict:
        """Create a new DID with did:key method.

        Args:
            agent_name: Human-readable agent name
            metadata: Optional agent metadata (model, version, capabilities, etc.)

        Returns:
            Dict containing DID, DID Document, and private key (PEM)
        """
        # Generate Ed25519 keypair
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        # Get public key bytes
        public_key_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )

        # Create did:key identifier
        # Multicodec prefix for Ed25519 public key: 0xed01
        multicodec_prefix = b'\xed\x01'
        multicodec_key = multicodec_prefix + public_key_bytes

        # Base58 encode
        did_key_specific = base58.b58encode(multicodec_key).decode('ascii')
        did = f"did:key:z{did_key_specific}"

        # Create DID Document
        did_document = self._create_did_document(
            did=did,
            public_key_bytes=public_key_bytes,
            agent_name=agent_name,
            metadata=metadata or {}
        )

        # Export private key
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')

        # Store DID Document
        self._store_did_document(did, did_document)

        return {
            "did": did,
            "did_document": did_document,
            "private_key_pem": private_key_pem
        }

    def _create_did_document(
        self,
        did: str,
        public_key_bytes: bytes,
        agent_name: str,
        metadata: Dict
    ) -> Dict:
        """Create a DID Document conforming to W3C spec.

        Args:
            did: The DID identifier
            public_key_bytes: Raw public key bytes
            agent_name: Agent name
            metadata: Agent metadata

        Returns:
            DID Document dict
        """
        # Convert public key to multibase format for verification method
        multicodec_prefix = b'\xed\x01'
        multicodec_key = multicodec_prefix + public_key_bytes
        multibase_key = 'z' + base58.b58encode(multicodec_key).decode('ascii')

        verification_method_id = f"{did}#{multibase_key}"

        doc = {
            "@context": [
                "https://www.w3.org/ns/did/v1",
                "https://w3id.org/security/suites/ed25519-2020/v1"
            ],
            "id": did,
            "verificationMethod": [{
                "id": verification_method_id,
                "type": "Ed25519VerificationKey2020",
                "controller": did,
                "publicKeyMultibase": multibase_key
            }],
            "authentication": [verification_method_id],
            "assertionMethod": [verification_method_id],
            "capabilityInvocation": [verification_method_id],
            "capabilityDelegation": [verification_method_id],

            # Agent-specific extensions
            "agentMetadata": {
                "name": agent_name,
                "model": metadata.get("model", "unknown"),
                "version": metadata.get("version", "1.0"),
                "provider": metadata.get("provider", "unknown"),
                "capabilities": metadata.get("capabilities", []),
                "toolset": metadata.get("toolset", []),
                "scopeOfBehavior": metadata.get("scopeOfBehavior", "")
            },
            "lifecycleStatus": "active",
            "created": datetime.utcnow().isoformat() + "Z",
            "updated": datetime.utcnow().isoformat() + "Z"
        }

        return doc

    def resolve_did(self, did: str) -> Optional[Dict]:
        """Resolve a DID to its DID Document.

        Args:
            did: The DID to resolve

        Returns:
            DID Document or None if not found
        """
        if not did.startswith("did:key:"):
            raise ValueError("Only did:key method is supported")

        # Try to load from storage
        doc = self._load_did_document(did)
        if doc:
            return doc

        # For did:key, we can derive the document from the DID itself
        # (though we prefer stored version for metadata)
        return self._derive_did_document_from_key(did)

    def _derive_did_document_from_key(self, did: str) -> Dict:
        """Derive minimal DID Document from did:key identifier.

        Args:
            did: did:key identifier

        Returns:
            Minimal DID Document
        """
        # Extract the multibase key
        if not did.startswith("did:key:z"):
            raise ValueError("Invalid did:key format")

        multibase_key = did.split("did:key:")[1]
        verification_method_id = f"{did}#{multibase_key}"

        # Create minimal document
        doc = {
            "@context": [
                "https://www.w3.org/ns/did/v1",
                "https://w3id.org/security/suites/ed25519-2020/v1"
            ],
            "id": did,
            "verificationMethod": [{
                "id": verification_method_id,
                "type": "Ed25519VerificationKey2020",
                "controller": did,
                "publicKeyMultibase": multibase_key
            }],
            "authentication": [verification_method_id],
            "assertionMethod": [verification_method_id],
        }

        return doc

    def update_did_document(self, did: str, updates: Dict) -> Dict:
        """Update a DID Document.

        Args:
            did: The DID to update
            updates: Fields to update

        Returns:
            Updated DID Document
        """
        doc = self._load_did_document(did)
        if not doc:
            raise ValueError(f"DID not found: {did}")

        # Update allowed fields
        if "agentMetadata" in updates:
            doc["agentMetadata"].update(updates["agentMetadata"])

        if "lifecycleStatus" in updates:
            doc["lifecycleStatus"] = updates["lifecycleStatus"]

        doc["updated"] = datetime.utcnow().isoformat() + "Z"

        # Store updated document
        self._store_did_document(did, doc)

        return doc

    def deactivate_did(self, did: str) -> Dict:
        """Deactivate a DID.

        Args:
            did: The DID to deactivate

        Returns:
            Updated DID Document
        """
        return self.update_did_document(did, {"lifecycleStatus": "deactivated"})

    def _store_did_document(self, did: str, doc: Dict):
        """Store DID Document to filesystem.

        Args:
            did: DID identifier
            doc: DID Document
        """
        # Use hash of DID as filename to avoid filesystem issues
        did_hash = hashlib.sha256(did.encode()).hexdigest()[:16]
        filepath = f"{self.storage_path}/{did_hash}.json"

        with open(filepath, 'w') as f:
            json.dump({
                "did": did,
                "document": doc
            }, f, indent=2)

    def _load_did_document(self, did: str) -> Optional[Dict]:
        """Load DID Document from filesystem.

        Args:
            did: DID identifier

        Returns:
            DID Document or None
        """
        did_hash = hashlib.sha256(did.encode()).hexdigest()[:16]
        filepath = f"{self.storage_path}/{did_hash}.json"

        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                return data.get("document")
        except FileNotFoundError:
            return None

    def get_public_key_from_did(self, did: str) -> bytes:
        """Extract public key bytes from a did:key.

        Args:
            did: did:key identifier

        Returns:
            Raw Ed25519 public key bytes
        """
        if not did.startswith("did:key:z"):
            raise ValueError("Invalid did:key format")

        # Extract multibase key (remove 'z' prefix)
        multibase_key = did.split("did:key:z")[1]

        # Base58 decode
        multicodec_key = base58.b58decode(multibase_key)

        # Remove multicodec prefix (0xed01)
        if not multicodec_key.startswith(b'\xed\x01'):
            raise ValueError("Invalid Ed25519 multicodec prefix")

        public_key_bytes = multicodec_key[2:]

        return public_key_bytes
