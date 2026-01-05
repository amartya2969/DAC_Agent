"""ANS Registry - Store and query agent registrations.

Similar to DNS, allows discovering agents by capability, protocol, provider, etc.
"""
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy import create_engine, Column, String, Text, DateTime, Index
from sqlalchemy.orm import sessionmaker
from src.models.base import Base


class ANSEntry(Base):
    """ANS registry entry model."""

    __tablename__ = 'ans_registry'

    ans_name = Column(String, primary_key=True)  # e.g., "financial://agent-alpha.analysis.acme.v1"
    agent_did = Column(String, nullable=False, index=True)
    service_endpoint = Column(String, nullable=False)
    capabilities = Column(Text, nullable=False)  # JSON array
    required_attestations = Column(Text, nullable=True)  # JSON array
    protocol_extensions = Column(Text, nullable=True)  # JSON object
    provider = Column(String, nullable=True, index=True)
    version = Column(String, nullable=True)
    status = Column(String, default='active', nullable=False, index=True)
    registered_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Composite indexes for efficient queries
    __table_args__ = (
        Index('idx_ans_capability', 'capabilities'),
        Index('idx_ans_provider_status', 'provider', 'status'),
    )


class ANSRegistry:
    """Agent Naming Service Registry."""

    def __init__(self, database_url: str = "sqlite:///data/ans.db"):
        """Initialize ANS Registry.

        Args:
            database_url: Database connection string
        """
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def register(
        self,
        ans_name: str,
        agent_did: str,
        capabilities: List[str],
        service_endpoint: str,
        provider: Optional[str] = None,
        version: Optional[str] = "1.0",
        required_attestations: Optional[List[str]] = None,
        protocol_extensions: Optional[Dict] = None
    ) -> Dict:
        """Register an agent in ANS.

        Args:
            ans_name: ANS name (e.g., "financial://agent-alpha.analysis.acme.v1")
            agent_did: Agent's DID
            capabilities: List of capability names
            service_endpoint: HTTP endpoint for the agent
            provider: Provider/organization name
            version: Agent version
            required_attestations: Required compliance attestations
            protocol_extensions: Protocol-specific extensions (MCP, A2A, etc.)

        Returns:
            Registration details
        """
        # Validate ANS name format
        if not self._validate_ans_name(ans_name):
            raise ValueError(f"Invalid ANS name format: {ans_name}")

        # Check if already registered
        existing = self.session.query(ANSEntry).filter_by(ans_name=ans_name).first()
        if existing:
            raise ValueError(f"ANS name already registered: {ans_name}")

        # Create entry
        entry = ANSEntry(
            ans_name=ans_name,
            agent_did=agent_did,
            service_endpoint=service_endpoint,
            capabilities=json.dumps(capabilities),
            required_attestations=json.dumps(required_attestations or []),
            protocol_extensions=json.dumps(protocol_extensions or {}),
            provider=provider,
            version=version,
            status='active'
        )

        self.session.add(entry)
        self.session.commit()

        return {
            "ans_name": ans_name,
            "agent_did": agent_did,
            "capabilities": capabilities,
            "registered_at": entry.registered_at.isoformat()
        }

    def resolve(self, ans_name: str) -> Optional[Dict]:
        """Resolve an ANS name to agent details.

        Args:
            ans_name: ANS name to resolve

        Returns:
            Agent details or None if not found
        """
        entry = self.session.query(ANSEntry).filter_by(
            ans_name=ans_name,
            status='active'
        ).first()

        if not entry:
            return None

        return self._entry_to_dict(entry)

    def resolve_by_capability(
        self,
        capability: str,
        provider: Optional[str] = None,
        version: Optional[str] = None
    ) -> List[Dict]:
        """Find agents by capability.

        Args:
            capability: Capability name to search for
            provider: Optional provider filter
            version: Optional version filter

        Returns:
            List of matching agent details
        """
        query = self.session.query(ANSEntry).filter(
            ANSEntry.status == 'active',
            ANSEntry.capabilities.like(f'%"{capability}"%')
        )

        if provider:
            query = query.filter(ANSEntry.provider == provider)

        if version:
            query = query.filter(ANSEntry.version == version)

        entries = query.all()

        return [self._entry_to_dict(e) for e in entries]

    def resolve_by_did(self, agent_did: str) -> List[Dict]:
        """Find all registrations for a DID.

        Args:
            agent_did: Agent DID

        Returns:
            List of registrations
        """
        entries = self.session.query(ANSEntry).filter_by(
            agent_did=agent_did,
            status='active'
        ).all()

        return [self._entry_to_dict(e) for e in entries]

    def update(
        self,
        ans_name: str,
        updates: Dict
    ) -> Dict:
        """Update an ANS registration.

        Args:
            ans_name: ANS name to update
            updates: Fields to update

        Returns:
            Updated registration details
        """
        entry = self.session.query(ANSEntry).filter_by(ans_name=ans_name).first()
        if not entry:
            raise ValueError(f"ANS name not found: {ans_name}")

        # Update allowed fields
        if "capabilities" in updates:
            entry.capabilities = json.dumps(updates["capabilities"])

        if "service_endpoint" in updates:
            entry.service_endpoint = updates["service_endpoint"]

        if "protocol_extensions" in updates:
            entry.protocol_extensions = json.dumps(updates["protocol_extensions"])

        if "status" in updates:
            entry.status = updates["status"]

        entry.updated_at = datetime.utcnow()
        self.session.commit()

        return self._entry_to_dict(entry)

    def unregister(self, ans_name: str):
        """Remove an agent from ANS (soft delete).

        Args:
            ans_name: ANS name to unregister
        """
        entry = self.session.query(ANSEntry).filter_by(ans_name=ans_name).first()
        if entry:
            entry.status = 'deactivated'
            entry.updated_at = datetime.utcnow()
            self.session.commit()

    def list_all(self, status: str = 'active') -> List[Dict]:
        """List all registered agents.

        Args:
            status: Filter by status (default 'active')

        Returns:
            List of all registrations
        """
        entries = self.session.query(ANSEntry).filter_by(status=status).all()
        return [self._entry_to_dict(e) for e in entries]

    def _entry_to_dict(self, entry: ANSEntry) -> Dict:
        """Convert ANS entry to dictionary.

        Args:
            entry: ANS entry object

        Returns:
            Dict representation
        """
        return {
            "ans_name": entry.ans_name,
            "agent_did": entry.agent_did,
            "service_endpoint": entry.service_endpoint,
            "capabilities": json.loads(entry.capabilities),
            "required_attestations": json.loads(entry.required_attestations or "[]"),
            "protocol_extensions": json.loads(entry.protocol_extensions or "{}"),
            "provider": entry.provider,
            "version": entry.version,
            "status": entry.status,
            "registered_at": entry.registered_at.isoformat(),
            "updated_at": entry.updated_at.isoformat()
        }

    def _validate_ans_name(self, ans_name: str) -> bool:
        """Validate ANS name format.

        Expected format: protocol://AgentID.Capability.Provider.Version
        Example: financial://agent-alpha.analysis.acme.v1

        Args:
            ans_name: ANS name to validate

        Returns:
            True if valid, False otherwise
        """
        # Basic validation: must contain ://
        if "://" not in ans_name:
            return False

        # Must have at least 2 parts after protocol
        parts = ans_name.split("://")
        if len(parts) != 2:
            return False

        return True


class ANSResolver:
    """Resolve ANS queries with advanced filtering."""

    def __init__(self, registry: ANSRegistry):
        """Initialize resolver.

        Args:
            registry: ANS Registry instance
        """
        self.registry = registry

    def resolve_best_match(
        self,
        capability: str,
        required_attestations: Optional[List[str]] = None,
        preferred_provider: Optional[str] = None
    ) -> Optional[Dict]:
        """Find best matching agent for a capability.

        Args:
            capability: Required capability
            required_attestations: Required compliance attestations
            preferred_provider: Preferred provider

        Returns:
            Best matching agent or None
        """
        # Get all agents with the capability
        candidates = self.registry.resolve_by_capability(capability)

        if not candidates:
            return None

        # Filter by required attestations
        if required_attestations:
            candidates = [
                c for c in candidates
                if all(att in c.get("required_attestations", [])
                      for att in required_attestations)
            ]

        if not candidates:
            return None

        # Prefer specific provider
        if preferred_provider:
            provider_matches = [c for c in candidates if c.get("provider") == preferred_provider]
            if provider_matches:
                return provider_matches[0]

        # Return first candidate
        return candidates[0]

    def query(
        self,
        capability: Optional[str] = None,
        provider: Optional[str] = None,
        protocol: Optional[str] = None
    ) -> List[Dict]:
        """Advanced query with multiple filters.

        Args:
            capability: Filter by capability
            provider: Filter by provider
            protocol: Filter by protocol

        Returns:
            List of matching agents
        """
        results = []

        if capability:
            results = self.registry.resolve_by_capability(
                capability,
                provider=provider
            )
        else:
            results = self.registry.list_all()

        # Filter by protocol if specified
        if protocol:
            results = [
                r for r in results
                if r.get("ans_name", "").startswith(protocol + "://")
            ]

        return results
