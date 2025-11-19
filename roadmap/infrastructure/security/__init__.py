"""
Security Layer - Credential Management and Security Utilities

This layer handles security-related functionality including:
- Credential management (keyring integration)
- Token storage and retrieval

Modules:
- credentials.py: Credential management with keyring support
"""

from .credentials import (
    CredentialManager,
    CredentialManagerError,
    get_credential_manager,
    mask_token,
)

__all__ = [
    "CredentialManager",
    "CredentialManagerError",
    "get_credential_manager",
    "mask_token",
]
