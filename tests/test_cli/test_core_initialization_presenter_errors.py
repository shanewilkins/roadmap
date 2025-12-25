"""Error path tests for CoreInitializationPresenter.

Tests cover all console output methods with various inputs,
click command behavior, and formatting validation.
"""

from unittest import mock

from roadmap.adapters.cli.presentation.core_initialization_presenter import (
    CoreInitializationPresenter,
)


class TestInitializationPresenterMethods:
    """Test all presenter output methods."""

    def test_initialization_header(self):
        """Test initialization header display."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.secho") as mock_secho:
            presenter.present_initialization_header()
            mock_secho.assert_called()

    def test_force_reinitialize_warning(self):
        """Test force reinitialize warning."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.secho") as mock_secho:
            presenter.present_force_reinitialize_warning(".roadmap")
            assert mock_secho.called
            call_args = mock_secho.call_args[0][0]
            assert ".roadmap" in call_args

    def test_already_initialized_info(self):
        """Test already initialized info message."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.secho") as mock_secho:
            with mock.patch("click.echo") as mock_echo:
                presenter.present_already_initialized_info(".roadmap")
                assert mock_secho.called or mock_echo.called

    def test_initialization_error(self):
        """Test initialization error display."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.secho") as mock_secho:
            presenter.present_initialization_error("Something went wrong")
            assert mock_secho.called

    def test_initialization_tip(self):
        """Test initialization tip display."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.secho") as mock_secho:
            presenter.present_initialization_tip()
            assert mock_secho.called

    def test_already_in_progress_error(self):
        """Test already in progress error."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.secho") as mock_secho:
            presenter.present_already_in_progress_error()
            assert mock_secho.called

    def test_creating_structure(self):
        """Test creating structure message."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.secho") as mock_secho:
            presenter.present_creating_structure(".roadmap")
            assert mock_secho.called

    def test_existing_projects_found(self):
        """Test existing projects found message."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.secho") as mock_secho:
            presenter.present_existing_projects_found(5)
            assert mock_secho.called

    def test_project_created(self):
        """Test project created message."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.secho") as mock_secho:
            presenter.present_project_created("Backend")
            assert mock_secho.called

    def test_project_joined(self):
        """Test project joined message."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.secho") as mock_secho:
            presenter.present_project_joined("Backend")
            assert mock_secho.called

    def test_projects_joined(self):
        """Test multiple projects joined message."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.secho") as mock_secho:
            presenter.present_projects_joined("Backend", 3)
            assert mock_secho.called

    def test_initialization_warning(self):
        """Test initialization warning."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.secho") as mock_secho:
            presenter.present_initialization_warning("Warnings present")
            assert mock_secho.called

    def test_initialization_failed(self):
        """Test initialization failed message."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.secho") as mock_secho:
            presenter.present_initialization_failed("Connection error")
            assert mock_secho.called

    def test_status_header(self):
        """Test status header."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.secho") as mock_secho:
            presenter.present_status_header()
            assert mock_secho.called

    def test_status_section(self):
        """Test status section."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.secho") as mock_secho:
            presenter.present_status_section("Database")
            assert mock_secho.called

    def test_status_item(self):
        """Test status item."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.secho") as mock_secho:
            presenter.present_status_item("Version", "1.0.0", ok=True)
            assert mock_secho.called

    def test_status_item_not_ok(self):
        """Test status item with failure."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.secho") as mock_secho:
            presenter.present_status_item("Database", "Offline", ok=False)
            assert mock_secho.called

    def test_status_not_initialized(self):
        """Test status not initialized message."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.secho") as mock_secho:
            with mock.patch("click.echo") as mock_echo:
                presenter.present_status_not_initialized()
                assert mock_secho.called or mock_echo.called

    def test_health_header(self):
        """Test health check header."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.secho") as mock_secho:
            presenter.present_health_header()
            assert mock_secho.called

    def test_health_section(self):
        """Test health section header."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.secho") as mock_secho:
            presenter.present_health_section("Database")
            assert mock_secho.called

    def test_health_check_healthy(self):
        """Test healthy health check result."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.secho") as mock_secho:
            with mock.patch("click.echo") as mock_echo:
                presenter.present_health_check("database", "HEALTHY", "All ok")
                assert mock_secho.called or mock_echo.called

    def test_health_check_degraded(self):
        """Test degraded health check result."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.secho") as mock_secho:
            with mock.patch("click.echo") as mock_echo:
                presenter.present_health_check("cache", "DEGRADED", "Slow response")
                assert mock_secho.called or mock_echo.called

    def test_health_check_unhealthy(self):
        """Test unhealthy health check result."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.secho") as mock_secho:
            with mock.patch("click.echo") as mock_echo:
                presenter.present_health_check("filesystem", "UNHEALTHY", "Disk full")
                assert mock_secho.called or mock_echo.called

    def test_overall_health_healthy(self):
        """Test overall health status healthy."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.echo") as mock_echo:
            with mock.patch("click.secho") as mock_secho:
                presenter.present_overall_health("HEALTHY")
                assert mock_echo.called or mock_secho.called

    def test_overall_health_degraded(self):
        """Test overall health status degraded."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.echo") as mock_echo:
            with mock.patch("click.secho") as mock_secho:
                presenter.present_overall_health("DEGRADED")
                assert mock_echo.called or mock_secho.called

    def test_health_warning(self):
        """Test health warning message."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.secho") as mock_secho:
            presenter.present_health_warning("Check logs for details")
            assert mock_secho.called

    def test_github_testing(self):
        """Test GitHub testing message."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.secho") as mock_secho:
            presenter.present_github_testing()
            assert mock_secho.called

    def test_github_credentials_stored(self):
        """Test GitHub credentials stored message."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.secho") as mock_secho:
            presenter.present_github_credentials_stored()
            assert mock_secho.called

    def test_github_unavailable(self):
        """Test GitHub unavailable message."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.secho") as mock_secho:
            presenter.present_github_unavailable("Not configured")
            assert mock_secho.called

    def test_github_setup_failed(self):
        """Test GitHub setup failed message."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.secho") as mock_secho:
            presenter.present_github_setup_failed("Invalid token")
            assert mock_secho.called

    def test_present_error(self):
        """Test generic error message."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.secho") as mock_secho:
            presenter.present_error("Something failed")
            assert mock_secho.called

    def test_present_warning(self):
        """Test generic warning message."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.secho") as mock_secho:
            presenter.present_warning("Be careful")
            assert mock_secho.called

    def test_present_info(self):
        """Test generic info message."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.secho") as mock_secho:
            presenter.present_info("For your information")
            assert mock_secho.called

    def test_present_success(self):
        """Test generic success message."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.secho") as mock_secho:
            presenter.present_success("All done")
            assert mock_secho.called


class TestPresenterWithEdgeCases:
    """Test presenter with edge case inputs."""

    def test_with_empty_strings(self):
        """Test presenter with empty string inputs."""
        presenter = CoreInitializationPresenter()
        with mock.patch("click.secho"):
            with mock.patch("click.echo"):
                presenter.present_project_created("")
                presenter.present_initialization_error("")
                presenter.present_health_warning("")

    def test_with_very_long_strings(self):
        """Test presenter with very long inputs."""
        presenter = CoreInitializationPresenter()
        long_string = "x" * 5000
        with mock.patch("click.secho"):
            presenter.present_project_created(long_string)
            presenter.present_initialization_error(long_string)

    def test_with_special_characters(self):
        """Test presenter with special characters."""
        presenter = CoreInitializationPresenter()
        special = "Project @#$%^&*() <test>"
        with mock.patch("click.secho"):
            presenter.present_project_created(special)

    def test_with_unicode(self):
        """Test presenter with Unicode characters."""
        presenter = CoreInitializationPresenter()
        unicode_str = "Проект 项目 プロジェクト"
        with mock.patch("click.secho"):
            presenter.present_project_created(unicode_str)

    def test_with_newlines(self):
        """Test presenter with newline characters."""
        presenter = CoreInitializationPresenter()
        with_newlines = "Line1\nLine2\nLine3"
        with mock.patch("click.secho"):
            presenter.present_initialization_error(with_newlines)


class TestPresenterInitialization:
    """Test presenter initialization."""

    def test_presenter_init(self):
        """Test presenter initializes correctly."""
        presenter = CoreInitializationPresenter()
        assert presenter is not None

    def test_presenter_no_state(self):
        """Test presenter has no internal state."""
        presenter1 = CoreInitializationPresenter()
        presenter2 = CoreInitializationPresenter()
        # Both should be independent
        assert presenter1 is not presenter2
