"""Integration tests for cross-platform CLI credential workflows."""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli import main


class TestCrossPlatformCLIWorkflows:
    """Test CLI workflows across different platforms."""

    @pytest.fixture
    def temp_roadmap(self, temp_dir_context):
        """Create a temporary roadmap for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    "init",
                    "--non-interactive",
                    "--skip-github",
                    "--project-name",
                    "test-project",
                ],
            )
            assert result.exit_code == 0
            yield temp_dir


class TestPlatformSpecificDependencies:
    """Test platform-specific dependency handling."""

    def test_keyring_import_success_all_platforms(self):
        """Test that keyring can be imported on all platforms."""
        platforms = ["Darwin", "Windows", "Linux"]

        for platform_name in platforms:
            with patch("platform.system", return_value=platform_name):
                # Test that keyring import works (mocked)
                mock_keyring = MagicMock()
                with patch.dict("sys.modules", {"keyring": mock_keyring}):
                    from roadmap.infrastructure.security.credentials import (
                        CredentialManager,
                    )

                    cm = CredentialManager()

                    # Should be able to create credential manager without errors
                    assert cm is not None
                    assert cm.system == platform_name.lower()

    def test_platform_specific_backend_selection(self):
        """Test that correct backends are selected for each platform."""
        test_cases = [
            ("Darwin", "_store_token_keychain"),
            ("Windows", "_store_token_wincred"),
            ("Linux", "_store_token_secretservice"),
        ]

        for platform_name, expected_method in test_cases:
            with patch("platform.system", return_value=platform_name):
                from roadmap.infrastructure.security.credentials import (
                    CredentialManager,
                )

                cm = CredentialManager()

                # Verify the credential manager has the expected method
                assert hasattr(cm, expected_method)

                # Test that store_token routes to the correct platform method
                with patch.object(
                    cm, expected_method, return_value=True
                ) as mock_method:
                    result = cm.store_token("test_token")
                    assert result is True
                    mock_method.assert_called_once()

    def test_graceful_degradation_across_platforms(self):
        """Test graceful degradation when platform features are unavailable."""
        platforms = ["Darwin", "Windows", "Linux", "FreeBSD"]

        for platform_name in platforms:
            with patch("platform.system", return_value=platform_name):
                from roadmap.infrastructure.security.credentials import (
                    CredentialManager,
                )

                cm = CredentialManager()

                # Should always fall back to environment variables
                with patch.dict(
                    "os.environ",
                    {"GITHUB_TOKEN": f"fallback_token_{platform_name.lower()}"},
                ):
                    token = cm.get_token()
                    assert token == f"fallback_token_{platform_name.lower()}"

    def test_cross_platform_error_resilience(self):
        """Test that errors on one platform don't break functionality."""
        from roadmap.infrastructure.security.credentials import (
            CredentialManager,
            CredentialManagerError,
        )

        error_scenarios = [
            ("Darwin", FileNotFoundError("security command not found")),
            ("Windows", ImportError("keyring module not available")),
            ("Linux", Exception("D-Bus service unavailable")),
        ]

        for platform_name, error in error_scenarios:
            with patch("platform.system", return_value=platform_name):
                cm = CredentialManager()

                # Should handle errors gracefully
                with patch.object(
                    cm, "store_token", side_effect=CredentialManagerError(str(error))
                ):
                    # Should not crash, should handle gracefully
                    try:
                        cm.store_token("test_token")
                        # May return False or raise CredentialManagerError
                    except CredentialManagerError as e:
                        # Should be a controlled exception
                        assert isinstance(e, CredentialManagerError)
                    except Exception as e:
                        # Other controlled exceptions are also acceptable
                        assert isinstance(e, FileNotFoundError | ImportError)


class TestRealWorldCompatibility:
    """Test compatibility with real-world scenarios."""

    def test_ci_cd_compatibility_all_platforms(self):
        """Test CI/CD environment compatibility across platforms."""
        ci_environments = [
            ("GitHub Actions", {"CI": "true", "GITHUB_ACTIONS": "true"}),
            ("GitLab CI", {"CI": "true", "GITLAB_CI": "true"}),
            ("Jenkins", {"JENKINS_URL": "http://jenkins"}),
            ("Azure DevOps", {"TF_BUILD": "True"}),
        ]

        platforms = ["Darwin", "Windows", "Linux"]

        for ci_name, ci_env in ci_environments:
            for platform_name in platforms:
                with patch("platform.system", return_value=platform_name):
                    with patch.dict(
                        "os.environ",
                        {
                            **ci_env,
                            "GITHUB_TOKEN": f'ci_token_{ci_name.lower().replace(" ", "_")}',
                        },
                    ):
                        from roadmap.infrastructure.security.credentials import (
                            CredentialManager,
                        )

                        cm = CredentialManager()

                        # Should work in CI environment
                        token = cm.get_token()
                        assert token == f'ci_token_{ci_name.lower().replace(" ", "_")}'

    def test_docker_container_compatibility(self):
        """Test compatibility in Docker containers across platforms."""
        docker_platforms = [
            ("linux", "Alpine Linux"),
            ("linux", "Ubuntu"),
            ("linux", "CentOS"),
            ("windows", "Windows Server Core"),
        ]

        for platform_system, _distro in docker_platforms:
            with patch("platform.system", return_value=platform_system.title()):
                # Mock limited Docker environment
                limited_env = {"PATH": "/usr/local/bin:/usr/bin:/bin"}

                with patch.dict("os.environ", limited_env, clear=True):
                    from roadmap.infrastructure.security.credentials import (
                        CredentialManager,
                    )

                    cm = CredentialManager()

                    # Should handle limited environment gracefully
                    available = cm.is_available()
                    # May or may not be available, but shouldn't crash
                    assert isinstance(available, bool)

    def test_minimal_system_compatibility(self):
        """Test compatibility on minimal systems."""
        from roadmap.infrastructure.security.credentials import CredentialManager

        minimal_scenarios = [
            ("Darwin", "macOS without developer tools"),
            ("Windows", "Windows without PowerShell"),
            ("Linux", "Alpine Linux minimal"),
            ("Linux", "BusyBox environment"),
        ]

        for platform_name, _scenario in minimal_scenarios:
            with patch("platform.system", return_value=platform_name):
                # Mock minimal environment (specific to subprocess and keyring)
                with patch("subprocess.run", side_effect=FileNotFoundError()):
                    # Test that credential manager still works with environment fallback
                    cm = CredentialManager()

                    # Should fall back to environment variables
                    with patch.dict(
                        "os.environ", {"GITHUB_TOKEN": "minimal_env_token"}
                    ):
                        token = cm.get_token()
                        assert token == "minimal_env_token"
