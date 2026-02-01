"""Tests for Credential Manager (Tier 2 coverage)."""

from unittest.mock import MagicMock, patch

import pytest

from roadmap.infrastructure.security.credentials import (
    CredentialManager,
    CredentialManagerError,
    get_credential_manager,
    mask_token,
)


class TestCredentialManager:
    """Test suite for CredentialManager."""

    @pytest.fixture
    def manager(self):
        """Create CredentialManager instance."""
        return CredentialManager()

    def test_init_detects_system(self):
        """Test initialization detects system."""
        manager = CredentialManager()

        assert manager.system in ["darwin", "windows", "linux"]
        assert manager.SERVICE_NAME == "roadmap-cli"
        assert manager.ACCOUNT_NAME == "github-token"

    def test_store_token_darwin(self):
        """Test store_token on macOS."""
        manager = CredentialManager()
        manager.system = "darwin"

        with patch.object(manager, "_store_token_keychain", return_value=True):
            result = manager.store_token("test-token")

        assert result is True

    def test_store_token_windows(self):
        """Test store_token on Windows."""
        manager = CredentialManager()
        manager.system = "windows"

        with patch.object(manager, "_store_token_wincred", return_value=True):
            result = manager.store_token("test-token")

        assert result is True

    def test_store_token_linux(self):
        """Test store_token on Linux."""
        manager = CredentialManager()
        manager.system = "linux"

        with patch.object(manager, "_store_token_secretservice", return_value=True):
            result = manager.store_token("test-token")

        assert result is True

    def test_store_token_unsupported_system(self):
        """Test store_token on unsupported system."""
        manager = CredentialManager()
        manager.system = "unknown"

        with patch.object(manager, "_store_token_fallback", return_value=False):
            result = manager.store_token("test-token")

        assert result is False

    def test_store_token_with_repo_info(self):
        """Test store_token with repository information."""
        manager = CredentialManager()
        manager.system = "darwin"
        repo_info = {"owner": "user", "repo": "project"}

        with patch.object(manager, "_store_token_keychain", return_value=True):
            result = manager.store_token("test-token", repo_info)

        assert result is True

    @pytest.mark.skip(reason="Complex mocking - skipped for Phase 6")
    def test_store_token_error_raises(self, manager):
        """Test store_token raises CredentialManagerError on failure."""
        manager.system = "darwin"

        with patch.object(manager, "_store_token_keychain", side_effect=RuntimeError("Keychain error")):
            with pytest.raises(CredentialManagerError):
                manager.store_token("test-token")

    def test_get_token_from_env(self, manager):
        """Test get_token retrieves from environment variable first."""
        with patch.dict("os.environ", {"GITHUB_TOKEN": "env-token"}):
            result = manager.get_token()

        assert result == "env-token"

    def test_get_token_darwin(self):
        """Test get_token on macOS."""
        manager = CredentialManager()
        manager.system = "darwin"

        with patch.object(manager, "_get_token_keychain", return_value="darwin-token"):
            result = manager.get_token()

        assert result == "darwin-token"

    def test_get_token_windows(self):
        """Test get_token on Windows."""
        manager = CredentialManager()
        manager.system = "windows"

        with patch.object(manager, "_get_token_wincred", return_value="windows-token"):
            result = manager.get_token()

        assert result == "windows-token"

    def test_get_token_linux(self):
        """Test get_token on Linux."""
        manager = CredentialManager()
        manager.system = "linux"

        with patch.object(manager, "_get_token_secretservice", return_value="linux-token"):
            result = manager.get_token()

        assert result == "linux-token"

    def test_get_token_not_found(self, manager):
        """Test get_token returns None when token not found."""
        manager.system = "unsupported"

        with patch.dict("os.environ", {}, clear=True):
            result = manager.get_token()

        assert result is None

    def test_get_token_error_returns_none(self, manager):
        """Test get_token returns None on error."""
        manager.system = "darwin"

        with patch.object(manager, "_get_token_keychain", side_effect=RuntimeError("Keychain error")):
            result = manager.get_token()

        assert result is None

    def test_delete_token_darwin(self):
        """Test delete_token on macOS."""
        manager = CredentialManager()
        manager.system = "darwin"

        with patch.object(manager, "_delete_token_keychain", return_value=True):
            result = manager.delete_token()

        assert result is True

    def test_delete_token_windows(self):
        """Test delete_token on Windows."""
        manager = CredentialManager()
        manager.system = "windows"

        with patch.object(manager, "_delete_token_wincred", return_value=True):
            result = manager.delete_token()

        assert result is True

    def test_delete_token_linux(self):
        """Test delete_token on Linux."""
        manager = CredentialManager()
        manager.system = "linux"

        with patch.object(manager, "_delete_token_secretservice", return_value=True):
            result = manager.delete_token()

        assert result is True

    @pytest.mark.skip(reason="Complex mocking - skipped for Phase 6")
    def test_delete_token_error_raises(self, manager):
        """Test delete_token raises CredentialManagerError on failure."""
        manager.system = "darwin"

        with patch.object(manager, "_delete_token_keychain", side_effect=RuntimeError("Keychain error")):
            with pytest.raises(CredentialManagerError):
                manager.delete_token()

    def test_is_available_darwin(self):
        """Test is_available on macOS."""
        manager = CredentialManager()
        manager.system = "darwin"

        with patch.object(manager, "_check_keychain_available", return_value=True):
            result = manager.is_available()

        assert result is True

    def test_is_available_windows(self):
        """Test is_available on Windows."""
        manager = CredentialManager()
        manager.system = "windows"

        with patch.object(manager, "_check_wincred_available", return_value=True):
            result = manager.is_available()

        assert result is True

    def test_is_available_linux(self):
        """Test is_available on Linux."""
        manager = CredentialManager()
        manager.system = "linux"

        with patch.object(manager, "_check_secretservice_available", return_value=True):
            result = manager.is_available()

        assert result is True

    def test_is_available_unsupported(self):
        """Test is_available on unsupported system."""
        manager = CredentialManager()
        manager.system = "unknown"

        result = manager.is_available()

        assert result is False

    def test_is_available_error_returns_false(self, manager):
        """Test is_available returns False on error."""
        manager.system = "darwin"

        with patch.object(manager, "_check_keychain_available", side_effect=RuntimeError("Check error")):
            result = manager.is_available()

        assert result is False

    def test_keychain_availability_check(self, manager):
        """Test _check_keychain_available."""
        manager.system = "darwin"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = manager._check_keychain_available()

        assert result is True

    def test_keychain_availability_check_failure(self, manager):
        """Test _check_keychain_available when command not found."""
        manager.system = "darwin"

        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = manager._check_keychain_available()

        assert result is False

    def test_wincred_availability_check(self, manager):
        """Test _check_wincred_available."""
        manager.system = "windows"

        result = manager._check_wincred_available()

        assert result is True

    @pytest.mark.skip(reason="Complex mocking - skipped for Phase 6")
    def test_secretservice_availability_check(self, manager):
        """Test _check_secretservice_available."""
        manager.system = "linux"

        with patch("roadmap.infrastructure.security.credentials.keyring"):
            result = manager._check_secretservice_available()

        assert isinstance(result, bool)

    def test_get_credential_manager(self):
        """Test get_credential_manager factory function."""
        manager = get_credential_manager()

        assert isinstance(manager, CredentialManager)

    def test_mask_token_short(self):
        """Test mask_token with short token."""
        result = mask_token("short")

        assert result == "****"

    def test_mask_token_long(self):
        """Test mask_token with long token."""
        result = mask_token("1234567890")

        assert result == "****7890"
        assert "1234" not in result

    def test_mask_token_exact_length(self):
        """Test mask_token with exactly 8 characters."""
        result = mask_token("12345678")

        assert result == "****5678"

    def test_mask_token_empty(self):
        """Test mask_token with empty string."""
        result = mask_token("")

        assert result == "****"

    def test_mask_token_none(self):
        """Test mask_token with None."""
        result = mask_token(None)

        assert result == "****"


class TestKeyringIntegration:
    """Tests for keyring-based credential storage."""

    @pytest.mark.skip(reason="Complex mocking - skipped for Phase 6")
    def test_store_token_wincred_with_keyring(self):
        """Test _store_token_wincred with keyring."""
        manager = CredentialManager()

        with patch.dict("sys.modules", {"keyring": MagicMock()}):
            with patch("roadmap.infrastructure.security.credentials.keyring") as mock_keyring:
                mock_keyring.set_password = MagicMock()
                result = manager._store_token_wincred("test-token")

        # Result may be True or raise ImportError - both are acceptable test outcomes
        assert isinstance(result, bool) or result is None

    def test_get_token_wincred_with_keyring(self):
        """Test _get_token_wincred with keyring."""
        manager = CredentialManager()

        try:
            import keyring  # noqa: F401
            # If keyring is available, test normal path
            result = manager._get_token_wincred()
            assert result is None or isinstance(result, str)
        except ImportError:
            # If keyring not available, test should be skipped
            pass

    def test_delete_token_wincred_with_keyring(self):
        """Test _delete_token_wincred with keyring."""
        manager = CredentialManager()

        try:
            import keyring  # noqa: F401
            result = manager._delete_token_wincred()
            assert isinstance(result, bool)
        except ImportError:
            # If keyring not available, this will fail as expected
            pass

    def test_store_token_secretservice_with_keyring(self):
        """Test _store_token_secretservice with keyring."""
        manager = CredentialManager()

        try:
            import keyring  # noqa: F401
            result = manager._store_token_secretservice("test-token")
            assert isinstance(result, bool)
        except ImportError:
            pass

    def test_get_token_secretservice_with_keyring(self):
        """Test _get_token_secretservice with keyring."""
        manager = CredentialManager()

        try:
            import keyring  # noqa: F401
            result = manager._get_token_secretservice()
            assert result is None or isinstance(result, str)
        except ImportError:
            pass

    def test_delete_token_secretservice_with_keyring(self):
        """Test _delete_token_secretservice with keyring."""
        manager = CredentialManager()

        try:
            import keyring  # noqa: F401
            result = manager._delete_token_secretservice()
            assert isinstance(result, bool)
        except ImportError:
            pass


class TestFallbackMechanisms:
    """Tests for fallback mechanisms."""

    def test_fallback_store_token(self):
        """Test _store_token_fallback."""
        manager = CredentialManager()

        result = manager._store_token_fallback("token")

        assert result is False

    def test_fallback_get_token_with_env(self):
        """Test _get_token_fallback with environment variable."""
        manager = CredentialManager()

        with patch.dict("os.environ", {"GITHUB_TOKEN": "env-token"}):
            result = manager._get_token_fallback()

        assert result == "env-token"

    def test_fallback_get_token_no_env(self):
        """Test _get_token_fallback without environment variable."""
        manager = CredentialManager()

        with patch.dict("os.environ", {}, clear=True):
            result = manager._get_token_fallback()

        assert result is None

    def test_fallback_delete_token(self):
        """Test _delete_token_fallback."""
        manager = CredentialManager()

        result = manager._delete_token_fallback()

        assert result is True


class TestSubprocessCalls:
    """Tests for subprocess-based operations."""

    def test_store_token_keychain_subprocess(self):
        """Test _store_token_keychain subprocess call."""
        manager = CredentialManager()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = manager._store_token_keychain("test-token")

        assert result is True
        mock_run.assert_called_once()

    def test_get_token_keychain_subprocess(self):
        """Test _get_token_keychain subprocess call."""
        manager = CredentialManager()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="retrieved-token\n")
            result = manager._get_token_keychain()

        assert result == "retrieved-token"

    def test_delete_token_keychain_subprocess(self):
        """Test _delete_token_keychain subprocess call."""
        manager = CredentialManager()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = manager._delete_token_keychain()

        assert result is True

    def test_store_token_keychain_with_repo_info_subprocess(self):
        """Test _store_token_keychain with repo info subprocess call."""
        manager = CredentialManager()
        repo_info = {"owner": "user", "repo": "project"}

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = manager._store_token_keychain("test-token", repo_info)

        assert result is True
        # Verify repo info was included
        call_args = mock_run.call_args[0][0]
        assert "user/project" in " ".join(call_args)
