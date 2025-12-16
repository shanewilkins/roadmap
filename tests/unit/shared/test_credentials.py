"""Tests for credential management."""

import platform
from unittest.mock import MagicMock, patch

import pytest

from roadmap.common.errors.exceptions import DeleteError, RoadmapException
from roadmap.infrastructure.security.credentials import (
    CredentialManager,
    get_credential_manager,
    mask_token,
)

pytestmark = pytest.mark.unit


class TestCredentialManager:
    """Test cases for CredentialManager."""

    @pytest.fixture
    def credential_manager(self):
        """Create credential manager for testing."""
        return CredentialManager()

    def test_initialization(self, credential_manager):
        """Test credential manager initialization."""
        assert credential_manager.SERVICE_NAME == "roadmap-cli"
        assert credential_manager.ACCOUNT_NAME == "github-token"
        assert credential_manager.system == platform.system().lower()

    def test_get_credential_manager(self):
        """Test get_credential_manager factory function."""
        manager = get_credential_manager()
        assert isinstance(manager, CredentialManager)

    def test_mask_token_normal(self):
        """Test token masking with normal token."""
        token = "ghp_1234567890abcdef"
        masked = mask_token(token)
        assert masked == "****cdef"

    def test_mask_token_short(self):
        """Test token masking with short token."""
        token = "short"
        masked = mask_token(token)
        assert masked == "****"

    def test_mask_token_empty(self):
        """Test token masking with empty token."""
        token = ""
        masked = mask_token(token)
        assert masked == "****"

    @patch.dict("os.environ", {"GITHUB_TOKEN": "env_token_value"})
    def test_get_token_environment_priority(self, credential_manager):
        """Test that environment variable takes priority."""
        token = credential_manager.get_token()
        assert token == "env_token_value"

    @patch.dict("os.environ", {}, clear=True)
    def test_get_token_no_environment(self, credential_manager):
        """Test token retrieval when no environment variable is set."""
        with patch.object(
            credential_manager, "_get_token_keychain", return_value="keychain_token"
        ):
            with patch.object(credential_manager, "system", "darwin"):
                token = credential_manager.get_token()
                assert token == "keychain_token"

    def test_get_token_exception_handling(self, credential_manager):
        """Test that exceptions in token retrieval are handled gracefully."""
        with patch.object(
            credential_manager,
            "_get_token_keychain",
            side_effect=Exception("Test error"),
        ):
            with patch.object(credential_manager, "system", "darwin"):
                token = credential_manager.get_token()
                assert token is None


class TestMacOSKeychain:
    """Test macOS Keychain integration."""

    @pytest.fixture
    def macos_manager(self):
        """Create credential manager for macOS testing."""
        manager = CredentialManager()
        manager.system = "darwin"
        return manager

    @patch("subprocess.run")
    def test_store_token_keychain_success(self, mock_run, macos_manager):
        """Test successful token storage in keychain."""
        mock_run.return_value.returncode = 0

        result = macos_manager._store_token_keychain("test_token")
        assert result is True

        # Verify correct command was called
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "security" in args
        assert "add-generic-password" in args
        assert "test_token" in args

    @patch("subprocess.run")
    def test_store_token_keychain_with_repo_info(self, mock_run, macos_manager):
        """Test token storage with repository information."""
        mock_run.return_value.returncode = 0
        repo_info = {"owner": "testuser", "repo": "testrepo"}

        result = macos_manager._store_token_keychain("test_token", repo_info)
        assert result is True

        # Verify repository info is included in comment
        args = mock_run.call_args[0][0]
        assert "-j" in args
        comment_index = args.index("-j") + 1
        assert "testuser/testrepo" in args[comment_index]

    @patch("subprocess.run")
    def test_store_token_keychain_failure(self, mock_run, macos_manager):
        """Test failed token storage in keychain."""
        mock_run.return_value.returncode = 1

        result = macos_manager._store_token_keychain("test_token")
        assert result is False

    @patch("subprocess.run")
    def test_get_token_keychain_success(self, mock_run, macos_manager):
        """Test successful token retrieval from keychain."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "test_token_value\n"

        result = macos_manager._get_token_keychain()
        assert result == "test_token_value"

        # Verify correct command was called
        args = mock_run.call_args[0][0]
        assert "security" in args
        assert "find-generic-password" in args
        assert "-w" in args

    @patch("subprocess.run")
    def test_get_token_keychain_not_found(self, mock_run, macos_manager):
        """Test token retrieval when not found in keychain."""
        mock_run.return_value.returncode = 44  # Keychain item not found

        result = macos_manager._get_token_keychain()
        assert result is None

    @patch("subprocess.run")
    def test_delete_token_keychain_success(self, mock_run, macos_manager):
        """Test successful token deletion from keychain."""
        mock_run.return_value.returncode = 0

        result = macos_manager._delete_token_keychain()
        assert result is True

        # Verify correct command was called
        args = mock_run.call_args[0][0]
        assert "security" in args
        assert "delete-generic-password" in args

    @patch("subprocess.run")
    def test_check_keychain_available_success(self, mock_run, macos_manager):
        """Test keychain availability check success."""
        mock_run.return_value.returncode = 0

        result = macos_manager._check_keychain_available()
        assert result is True

    @patch("subprocess.run")
    def test_check_keychain_available_failure(self, mock_run, macos_manager):
        """Test keychain availability check failure."""
        mock_run.side_effect = FileNotFoundError()

        result = macos_manager._check_keychain_available()
        assert result is False


class TestWindowsCredentialManager:
    """Test Windows Credential Manager integration."""

    @pytest.fixture
    def windows_manager(self):
        """Create credential manager for Windows testing."""
        manager = CredentialManager()
        manager.system = "windows"
        return manager

    def test_store_token_wincred_with_keyring(self, windows_manager):
        """Test token storage with keyring library."""
        mock_keyring = MagicMock()

        with patch.dict("sys.modules", {"keyring": mock_keyring}):
            result = windows_manager._store_token_wincred("test_token")
            assert result is True
            mock_keyring.set_password.assert_called_once()

    def test_store_token_wincred_without_keyring(self, windows_manager):
        """Test token storage fallback without keyring."""
        with patch.object(
            windows_manager, "_store_token_cmdkey", return_value=True
        ) as mock_cmdkey:
            with patch("builtins.__import__", side_effect=ImportError()):
                result = windows_manager._store_token_wincred("test_token")
                assert result is True
                mock_cmdkey.assert_called_once()

    def test_get_token_wincred_with_keyring(self, windows_manager):
        """Test token retrieval with keyring library."""
        mock_keyring = MagicMock()
        mock_keyring.get_password.return_value = "stored_token"

        with patch.dict("sys.modules", {"keyring": mock_keyring}):
            result = windows_manager._get_token_wincred()
            assert result == "stored_token"

    def test_check_wincred_available_with_keyring(self, windows_manager):
        """Test credential manager availability with keyring."""
        mock_keyring = MagicMock()

        with patch.dict("sys.modules", {"keyring": mock_keyring}):
            result = windows_manager._check_wincred_available()
            assert result is True

    @patch("subprocess.run")
    def test_check_wincred_available_with_cmdkey(self, mock_run, windows_manager):
        """Test credential manager availability with cmdkey fallback."""
        mock_run.return_value.returncode = 0

        with patch("builtins.__import__", side_effect=ImportError()):
            result = windows_manager._check_wincred_available()
            assert result is True


class TestLinuxSecretService:
    """Test Linux Secret Service integration."""

    @pytest.fixture
    def linux_manager(self):
        """Create credential manager for Linux testing."""
        manager = CredentialManager()
        manager.system = "linux"
        return manager

    def test_store_token_secretservice_with_keyring(self, linux_manager):
        """Test token storage with keyring library."""
        mock_keyring = MagicMock()

        with patch.dict("sys.modules", {"keyring": mock_keyring}):
            result = linux_manager._store_token_secretservice("test_token")
            assert result is True
            mock_keyring.set_password.assert_called_once()

    def test_store_token_secretservice_without_keyring(self, linux_manager):
        """Test token storage fallback without keyring."""
        with patch.object(
            linux_manager, "_store_token_fallback", return_value=False
        ) as mock_fallback:
            with patch("builtins.__import__", side_effect=ImportError()):
                result = linux_manager._store_token_secretservice("test_token")
                assert result is False
                mock_fallback.assert_called_once()

    def test_check_secretservice_available_with_keyring(self, linux_manager):
        """Test secret service availability with keyring."""
        mock_keyring = MagicMock()
        mock_keyring.get_keyring.return_value = MagicMock()

        with patch.dict("sys.modules", {"keyring": mock_keyring}):
            result = linux_manager._check_secretservice_available()
            assert result is True


class TestFallbackImplementation:
    """Test fallback implementation for unsupported systems."""

    @pytest.fixture
    def unsupported_manager(self):
        """Create credential manager for unsupported system."""
        manager = CredentialManager()
        manager.system = "unsupported"
        return manager

    def test_store_token_fallback(self, unsupported_manager):
        """Test fallback token storage."""
        result = unsupported_manager._store_token_fallback("test_token")
        assert result is False

    @patch.dict("os.environ", {"GITHUB_TOKEN": "env_token"})
    def test_get_token_fallback_with_env(self, unsupported_manager):
        """Test fallback token retrieval with environment variable."""
        result = unsupported_manager._get_token_fallback()
        assert result == "env_token"

    @patch.dict("os.environ", {}, clear=True)
    def test_get_token_fallback_without_env(self, unsupported_manager):
        """Test fallback token retrieval without environment variable."""
        result = unsupported_manager._get_token_fallback()
        assert result is None

    def test_delete_token_fallback(self, unsupported_manager):
        """Test fallback token deletion."""
        result = unsupported_manager._delete_token_fallback()
        assert result is True

    def test_is_available_unsupported(self, unsupported_manager):
        """Test availability check for unsupported system."""
        result = unsupported_manager.is_available()
        assert result is False


class TestIntegrationScenarios:
    """Test integration scenarios for credential management."""

    @pytest.fixture
    def credential_manager(self):
        """Create credential manager for testing."""
        return CredentialManager()

    def test_store_and_retrieve_token_flow(self, credential_manager):
        """Test complete store and retrieve flow."""
        with patch.object(credential_manager, "is_available", return_value=True):
            with patch.object(
                credential_manager, "_store_token_keychain", return_value=True
            ):
                with patch.object(
                    credential_manager,
                    "_get_token_keychain",
                    return_value="stored_token",
                ):
                    with patch.object(credential_manager, "system", "darwin"):
                        # Store token
                        result = credential_manager.store_token("test_token")
                        assert result is True

                        # Retrieve token (with no environment variable)
                        with patch.dict("os.environ", {}, clear=True):
                            token = credential_manager.get_token()
                            assert token == "stored_token"

    def test_error_handling_in_store_token(self, credential_manager):
        """Test error handling during token storage."""
        with patch.object(
            credential_manager,
            "_store_token_keychain",
            side_effect=Exception("Storage error"),
        ):
            with patch.object(credential_manager, "system", "darwin"):
                with pytest.raises(RoadmapException, match="Failed to save"):
                    credential_manager.store_token("test_token")

    def test_error_handling_in_delete_token(self, credential_manager):
        """Test error handling during token deletion."""
        with patch.object(
            credential_manager,
            "_delete_token_keychain",
            side_effect=Exception("Delete error"),
        ):
            with patch.object(credential_manager, "system", "darwin"):
                with pytest.raises(DeleteError, match="Failed to delete"):
                    credential_manager.delete_token()
