"""Integration tests for cross-platform CLI credential workflows."""

import os
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest
from click.testing import CliRunner

from roadmap.cli import main


class TestCrossPlatformCLIWorkflows:
    """Test CLI workflows across different platforms."""

    @pytest.fixture
    def temp_roadmap(self):
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

    def test_macos_cli_secure_setup_workflow(self, temp_roadmap):
        """Test complete CLI workflow on macOS with secure storage."""
        with patch("platform.system", return_value="Darwin"):
            runner = CliRunner()

            # Mock macOS keychain operations
            with patch("subprocess.run") as mock_run:
                # Mock keychain availability and operations
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = "test_token_macos\n"

                # Mock sync manager operations
                with patch("roadmap.cli.sync.SyncManager") as mock_sync_class:
                    mock_instance = Mock()
                    mock_instance.store_token_secure.return_value = (
                        True,
                        "Token stored securely in system credential manager. Masked token: ****acos",
                    )
                    mock_instance.test_connection.return_value = (
                        True,
                        "Connected as testuser to testuser/testrepo",
                    )
                    mock_instance.setup_repository.return_value = (
                        True,
                        "Repository setup complete",
                    )
                    mock_sync_class.return_value = mock_instance

                    # Test secure setup
                    result = runner.invoke(
                        main,
                        [
                            "sync",
                            "setup",
                            "--token",
                            "test_token_macos",
                            "--repo",
                            "testuser/testrepo",
                        ],
                    )
                    assert result.exit_code == 0
                    assert "Token stored securely" in result.output
                    assert "Connected as testuser" in result.output

                    # Verify store_token_secure was called
                    mock_instance.store_token_secure.assert_called_once()

    def test_windows_cli_secure_setup_workflow(self, temp_roadmap):
        """Test complete CLI workflow on Windows with secure storage."""
        with patch("platform.system", return_value="Windows"):
            runner = CliRunner()

            # Mock Windows credential manager operations
            mock_keyring = MagicMock()
            with patch.dict("sys.modules", {"keyring": mock_keyring}):
                # Mock sync manager operations
                with patch("roadmap.cli.sync.SyncManager") as mock_sync_class:
                    mock_instance = Mock()
                    mock_instance.store_token_secure.return_value = (
                        True,
                        "Token stored securely in system credential manager. Masked token: ****dows",
                    )
                    mock_instance.test_connection.return_value = (
                        True,
                        "Connected as winuser to winuser/winrepo",
                    )
                    mock_instance.setup_repository.return_value = (
                        True,
                        "Repository setup complete",
                    )
                    mock_sync_class.return_value = mock_instance

                    # Test secure setup
                    result = runner.invoke(
                        main,
                        [
                            "sync",
                            "setup",
                            "--token",
                            "test_token_windows",
                            "--repo",
                            "winuser/winrepo",
                        ],
                    )
                    assert result.exit_code == 0
                    assert "Token stored securely" in result.output
                    assert "Connected as winuser" in result.output

    def test_linux_cli_secure_setup_workflow(self, temp_roadmap):
        """Test complete CLI workflow on Linux with secure storage."""
        with patch("platform.system", return_value="Linux"):
            runner = CliRunner()

            # Mock Linux secret service operations
            mock_keyring = MagicMock()
            mock_keyring.get_keyring.return_value = MagicMock()
            with patch.dict("sys.modules", {"keyring": mock_keyring}):
                # Mock sync manager operations
                with patch("roadmap.cli.sync.SyncManager") as mock_sync_class:
                    mock_instance = Mock()
                    mock_instance.store_token_secure.return_value = (
                        True,
                        "Token stored securely in system credential manager. Masked token: ****inux",
                    )
                    mock_instance.test_connection.return_value = (
                        True,
                        "Connected as linuxuser to linuxuser/linuxrepo",
                    )
                    mock_instance.setup_repository.return_value = (
                        True,
                        "Repository setup complete",
                    )
                    mock_sync_class.return_value = mock_instance

                    # Test secure setup
                    result = runner.invoke(
                        main,
                        [
                            "sync",
                            "setup",
                            "--token",
                            "test_token_linux",
                            "--repo",
                            "linuxuser/linuxrepo",
                        ],
                    )
                    assert result.exit_code == 0
                    assert "Token stored securely" in result.output
                    assert "Connected as linuxuser" in result.output

    def test_cross_platform_status_command(self, temp_roadmap):
        """Test sync status command across platforms."""
        platforms = [("Darwin", "macOS"), ("Windows", "Windows"), ("Linux", "Linux")]

        for platform_name, platform_display in platforms:
            with patch("platform.system", return_value=platform_name):
                runner = CliRunner()

                # Mock credential manager availability
                with patch("roadmap.cli.sync.SyncManager") as mock_sync_class:
                    mock_instance = Mock()
                    mock_instance.test_connection.return_value = (
                        False,
                        "GitHub client not configured",
                    )
                    mock_instance.get_token_info.return_value = {
                        "config_file": False,
                        "environment": False,
                        "credential_manager": False,
                        "credential_manager_available": True,
                        "active_source": None,
                        "masked_token": None,
                    }
                    mock_sync_class.return_value = mock_instance

                    result = runner.invoke(main, ["sync", "status"])
                    assert result.exit_code == 0
                    assert "GitHub Integration Status" in result.output
                    assert "Token Sources:" in result.output
                    assert "Credential Manager:" in result.output

    def test_cross_platform_environment_variable_priority(self, temp_roadmap):
        """Test that environment variables work across all platforms."""
        platforms = ["Darwin", "Windows", "Linux"]

        for platform_name in platforms:
            with patch("platform.system", return_value=platform_name):
                runner = CliRunner()

                # Set environment variable
                with patch.dict(
                    "os.environ", {"GITHUB_TOKEN": f"env_token_{platform_name.lower()}"}
                ):
                    # Mock sync manager operations
                    with patch("roadmap.cli.sync.SyncManager") as mock_sync_class:
                        mock_instance = Mock()
                        mock_instance.test_connection.return_value = (
                            True,
                            f"Connected using env token on {platform_name}",
                        )
                        mock_instance.setup_repository.return_value = (
                            True,
                            "Repository setup complete",
                        )
                        mock_sync_class.return_value = mock_instance

                        # Test setup with just repo (should use env var for token)
                        result = runner.invoke(
                            main,
                            [
                                "sync",
                                "setup",
                                "--repo",
                                f"user/repo-{platform_name.lower()}",
                            ],
                        )
                        assert result.exit_code == 0
                        assert (
                            f"Connected using env token on {platform_name}"
                            in result.output
                        )

    def test_cross_platform_insecure_flag_behavior(self, temp_roadmap):
        """Test --insecure flag behavior across platforms."""
        platforms = ["Darwin", "Windows", "Linux"]

        for platform_name in platforms:
            with patch("platform.system", return_value=platform_name):
                runner = CliRunner()

                # Mock sync manager operations
                with patch("roadmap.cli.sync.SyncManager") as mock_sync_class:
                    mock_instance = Mock()
                    mock_instance.test_connection.return_value = (
                        True,
                        f"Connected on {platform_name}",
                    )
                    mock_instance.setup_repository.return_value = (
                        True,
                        "Repository setup complete",
                    )
                    mock_sync_class.return_value = mock_instance

                    # Test insecure flag
                    result = runner.invoke(
                        main,
                        [
                            "sync",
                            "setup",
                            "--token",
                            f"test_token_{platform_name.lower()}",
                            "--repo",
                            "user/repo",
                            "--insecure",
                        ],
                    )
                    assert result.exit_code == 0
                    assert (
                        "WARNING: Storing token in config file is NOT RECOMMENDED!"
                        in result.output
                    )
                    assert (
                        "Consider using environment variable instead" in result.output
                    )

    def test_cross_platform_credential_manager_unavailable(self, temp_roadmap):
        """Test behavior when credential manager is unavailable on each platform."""
        test_cases = [
            ("Darwin", "macOS keychain unavailable"),
            ("Windows", "Windows Credential Manager unavailable"),
            ("Linux", "Linux Secret Service unavailable"),
        ]

        for platform_name, error_context in test_cases:
            with patch("platform.system", return_value=platform_name):
                runner = CliRunner()

                # Mock credential manager unavailable
                with patch("roadmap.cli.sync.SyncManager") as mock_sync_class:
                    mock_instance = Mock()
                    mock_instance.store_token_secure.return_value = (
                        False,
                        "Secure credential storage not available on this system",
                    )
                    mock_sync_class.return_value = mock_instance

                    # Test setup should fail gracefully
                    result = runner.invoke(
                        main,
                        [
                            "sync",
                            "setup",
                            "--token",
                            "test_token",
                            "--repo",
                            "user/repo",
                        ],
                    )
                    assert result.exit_code == 0  # Should not crash
                    assert "Alternative: Set environment variable" in result.output

    def test_cross_platform_delete_token_command(self, temp_roadmap):
        """Test delete-token command across platforms."""
        platforms = [
            ("Darwin", "Keychain"),
            ("Windows", "Credential Manager"),
            ("Linux", "Secret Service"),
        ]

        for platform_name, storage_type in platforms:
            with patch("platform.system", return_value=platform_name):
                runner = CliRunner()

                # Mock sync manager operations
                with patch("roadmap.cli.sync.SyncManager") as mock_sync_class:
                    mock_instance = Mock()
                    mock_instance.delete_token_secure.return_value = (
                        True,
                        f"Token deleted from {storage_type}",
                    )
                    mock_sync_class.return_value = mock_instance

                    result = runner.invoke(main, ["sync", "delete-token"])
                    assert result.exit_code == 0
                    assert f"Token deleted from {storage_type}" in result.output


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
                    from roadmap.credentials import CredentialManager

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
                from roadmap.credentials import CredentialManager

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
                from roadmap.credentials import CredentialManager

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
        from roadmap.credentials import CredentialManager, CredentialManagerError

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
                        result = cm.store_token("test_token")
                        # May return False or raise CredentialManagerError
                    except CredentialManagerError as e:
                        # Should be a controlled exception
                        assert isinstance(e, CredentialManagerError)
                    except Exception as e:
                        # Other controlled exceptions are also acceptable
                        assert isinstance(e, (FileNotFoundError, ImportError))


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
                        from roadmap.credentials import CredentialManager

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

        for platform_system, distro in docker_platforms:
            with patch("platform.system", return_value=platform_system.title()):
                # Mock limited Docker environment
                limited_env = {"PATH": "/usr/local/bin:/usr/bin:/bin"}

                with patch.dict("os.environ", limited_env, clear=True):
                    from roadmap.credentials import CredentialManager

                    cm = CredentialManager()

                    # Should handle limited environment gracefully
                    available = cm.is_available()
                    # May or may not be available, but shouldn't crash
                    assert isinstance(available, bool)

    def test_minimal_system_compatibility(self):
        """Test compatibility on minimal systems."""
        from roadmap.credentials import CredentialManager

        minimal_scenarios = [
            ("Darwin", "macOS without developer tools"),
            ("Windows", "Windows without PowerShell"),
            ("Linux", "Alpine Linux minimal"),
            ("Linux", "BusyBox environment"),
        ]

        for platform_name, scenario in minimal_scenarios:
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
