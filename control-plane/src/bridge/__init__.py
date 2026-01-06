"""Bridge Module - OIDC Integration Layer.

This module bridges Web3 identity (DIDs, VCs) to Web2 cloud providers (AWS, GCP, Azure).

The CORE VALUE PROPOSITION:
- Agents present VCs → receive short-lived cloud tokens
- No hardcoded API keys
- Complete attribution in cloud audit logs
"""
from .aws_adapter import AWSCredentialAdapter, GCPCredentialAdapter, AzureCredentialAdapter

__all__ = ['AWSCredentialAdapter', 'GCPCredentialAdapter', 'AzureCredentialAdapter']
