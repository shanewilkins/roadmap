"""Secure credential management for GitHub tokens."""

import json
import os
import platform
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional


class CredentialManagerError(Exception):
    """Exception raised for credential manager errors."""

    pass


class CredentialManager:
    """Cross-platform secure credential manager."""

    SERVICE_NAME = "roadmap-cli"
    ACCOUNT_NAME = "github-token"

    def __init__(self):
        """Initialize credential manager."""
        self.system = platform.system().lower()

    def store_token(
        self, token: str, repo_info: Optional[Dict[str, str]] = None
    ) -> bool:
        """Store GitHub token securely.

        Args:
            token: GitHub personal access token
            repo_info: Optional repository information (owner, repo)

        Returns:
            True if stored successfully, False otherwise
        """
        try:
            if self.system == "darwin":
                return self._store_token_keychain(token, repo_info)
            elif self.system == "windows":
                return self._store_token_wincred(token, repo_info)
            elif self.system == "linux":
                return self._store_token_secretservice(token, repo_info)
            else:
                # Fallback for unsupported systems
                return self._store_token_fallback(token, repo_info)
        except Exception as e:
            raise CredentialManagerError(f"Failed to store token: {e}")

    def get_token(self) -> Optional[str]:
        """Retrieve GitHub token securely.

        Returns:
            GitHub token if found, None otherwise
        """
        try:
            # Always check environment variable first
            env_token = os.getenv("GITHUB_TOKEN")
            if env_token:
                return env_token

            if self.system == "darwin":
                return self._get_token_keychain()
            elif self.system == "windows":
                return self._get_token_wincred()
            elif self.system == "linux":
                return self._get_token_secretservice()
            else:
                # Fallback for unsupported systems
                return self._get_token_fallback()
        except Exception:
            # Silently fail and return None - credential retrieval should be non-blocking
            return None

    def delete_token(self) -> bool:
        """Delete stored GitHub token.

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            if self.system == "darwin":
                return self._delete_token_keychain()
            elif self.system == "windows":
                return self._delete_token_wincred()
            elif self.system == "linux":
                return self._delete_token_secretservice()
            else:
                # Fallback for unsupported systems
                return self._delete_token_fallback()
        except Exception as e:
            raise CredentialManagerError(f"Failed to delete token: {e}")

    def is_available(self) -> bool:
        """Check if credential manager is available on this system.

        Returns:
            True if credential manager is available, False otherwise
        """
        try:
            if self.system == "darwin":
                return self._check_keychain_available()
            elif self.system == "windows":
                return self._check_wincred_available()
            elif self.system == "linux":
                return self._check_secretservice_available()
            else:
                return False
        except Exception:
            return False

    # macOS Keychain implementation
    def _store_token_keychain(
        self, token: str, repo_info: Optional[Dict[str, str]] = None
    ) -> bool:
        """Store token in macOS Keychain."""
        cmd = [
            "security",
            "add-generic-password",
            "-s",
            self.SERVICE_NAME,
            "-a",
            self.ACCOUNT_NAME,
            "-w",
            token,
            "-U",  # Update if exists
        ]

        if repo_info:
            # Add repository info as a comment
            comment = f"GitHub token for {repo_info.get('owner', '')}/{repo_info.get('repo', '')}"
            cmd.extend(["-j", comment])

        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0

    def _get_token_keychain(self) -> Optional[str]:
        """Get token from macOS Keychain."""
        cmd = [
            "security",
            "find-generic-password",
            "-s",
            self.SERVICE_NAME,
            "-a",
            self.ACCOUNT_NAME,
            "-w",  # Output password only
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        return None

    def _delete_token_keychain(self) -> bool:
        """Delete token from macOS Keychain."""
        cmd = [
            "security",
            "delete-generic-password",
            "-s",
            self.SERVICE_NAME,
            "-a",
            self.ACCOUNT_NAME,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0

    def _check_keychain_available(self) -> bool:
        """Check if macOS Keychain is available."""
        try:
            result = subprocess.run(["security", "-h"], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False

    # Windows Credential Manager implementation
    def _store_token_wincred(
        self, token: str, repo_info: Optional[Dict[str, str]] = None
    ) -> bool:
        """Store token in Windows Credential Manager."""
        try:
            import keyring

            target_name = f"{self.SERVICE_NAME}:{self.ACCOUNT_NAME}"
            if repo_info:
                target_name += (
                    f":{repo_info.get('owner', '')}/{repo_info.get('repo', '')}"
                )

            keyring.set_password(self.SERVICE_NAME, target_name, token)
            return True
        except ImportError:
            # Fallback to cmdkey if keyring not available
            return self._store_token_cmdkey(token, repo_info)

    def _get_token_wincred(self) -> Optional[str]:
        """Get token from Windows Credential Manager."""
        try:
            import keyring

            target_name = f"{self.SERVICE_NAME}:{self.ACCOUNT_NAME}"
            return keyring.get_password(self.SERVICE_NAME, target_name)
        except ImportError:
            # Fallback to cmdkey if keyring not available
            return self._get_token_cmdkey()

    def _delete_token_wincred(self) -> bool:
        """Delete token from Windows Credential Manager."""
        try:
            import keyring

            target_name = f"{self.SERVICE_NAME}:{self.ACCOUNT_NAME}"
            keyring.delete_password(self.SERVICE_NAME, target_name)
            return True
        except ImportError:
            # Fallback to cmdkey if keyring not available
            return self._delete_token_cmdkey()
        except Exception:
            return False

    def _check_wincred_available(self) -> bool:
        """Check if Windows Credential Manager is available."""
        try:
            import keyring

            return True
        except ImportError:
            try:
                result = subprocess.run(
                    ["cmdkey", "/?"], capture_output=True, text=True
                )
                return result.returncode == 0
            except FileNotFoundError:
                return False

    def _store_token_cmdkey(
        self, token: str, repo_info: Optional[Dict[str, str]] = None
    ) -> bool:
        """Store token using Windows cmdkey."""
        target_name = self.SERVICE_NAME
        if repo_info:
            target_name += f":{repo_info.get('owner', '')}/{repo_info.get('repo', '')}"

        cmd = [
            "cmdkey",
            f"/generic:{target_name}",
            f"/user:{self.ACCOUNT_NAME}",
            f"/pass:{token}",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0

    def _get_token_cmdkey(self) -> Optional[str]:
        """Get token using Windows cmdkey (limited functionality)."""
        # cmdkey doesn't provide a way to retrieve passwords, only store/delete
        # This is a limitation of the cmdkey approach
        return None

    def _delete_token_cmdkey(self) -> bool:
        """Delete token using Windows cmdkey."""
        cmd = ["cmdkey", f"/delete:{self.SERVICE_NAME}"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0

    # Linux Secret Service implementation
    def _store_token_secretservice(
        self, token: str, repo_info: Optional[Dict[str, str]] = None
    ) -> bool:
        """Store token in Linux Secret Service."""
        try:
            import keyring

            target_name = f"{self.SERVICE_NAME}:{self.ACCOUNT_NAME}"
            if repo_info:
                target_name += (
                    f":{repo_info.get('owner', '')}/{repo_info.get('repo', '')}"
                )

            keyring.set_password(self.SERVICE_NAME, target_name, token)
            return True
        except ImportError:
            # Fallback if keyring not available
            return self._store_token_fallback(token, repo_info)

    def _get_token_secretservice(self) -> Optional[str]:
        """Get token from Linux Secret Service."""
        try:
            import keyring

            target_name = f"{self.SERVICE_NAME}:{self.ACCOUNT_NAME}"
            return keyring.get_password(self.SERVICE_NAME, target_name)
        except ImportError:
            # Fallback if keyring not available
            return self._get_token_fallback()

    def _delete_token_secretservice(self) -> bool:
        """Delete token from Linux Secret Service."""
        try:
            import keyring

            target_name = f"{self.SERVICE_NAME}:{self.ACCOUNT_NAME}"
            keyring.delete_password(self.SERVICE_NAME, target_name)
            return True
        except ImportError:
            # Fallback if keyring not available
            return self._delete_token_fallback()
        except Exception:
            return False

    def _check_secretservice_available(self) -> bool:
        """Check if Linux Secret Service is available."""
        try:
            import keyring

            # Try to access the keyring to see if it's functional
            keyring.get_keyring()
            return True
        except ImportError:
            return False
        except Exception:
            return False

    # Fallback implementation for unsupported systems
    def _store_token_fallback(
        self, token: str, repo_info: Optional[Dict[str, str]] = None
    ) -> bool:
        """Fallback token storage (warns user to use environment variable)."""
        # Don't actually store - just return False to indicate secure storage unavailable
        return False

    def _get_token_fallback(self) -> Optional[str]:
        """Fallback token retrieval (environment variable only)."""
        return os.getenv("GITHUB_TOKEN")

    def _delete_token_fallback(self) -> bool:
        """Fallback token deletion (no-op)."""
        return True


def get_credential_manager() -> CredentialManager:
    """Get a credential manager instance."""
    return CredentialManager()


def mask_token(token: str) -> str:
    """Mask a token for display purposes.

    Args:
        token: Token to mask

    Returns:
        Masked token showing only last 4 characters
    """
    if not token or len(token) < 8:
        return "****"

    return f"****{token[-4:]}"
