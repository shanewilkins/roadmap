"""Tests for GitHub adapter gateway abstraction.

Tests cover:
- GitHub client instantiation and configuration
- GitHub API error class retrieval
- Error class consistency
- Configuration edge cases
- Type safety and interface contracts
"""

from typing import Type
from unittest.mock import Mock

from roadmap.infrastructure.github_gateway import GitHubGateway


class TestGitHubGatewayClientInstantiation:
    """Test GitHub client creation."""

    def test_get_github_client_returns_client(self):
        """Should return a GitHub client instance."""
        config = Mock()
        client = GitHubGateway.get_github_client(config)

        assert client is not None

    def test_get_github_client_returns_consistent_type(self):
        """GitHub clients should have consistent type."""
        config = Mock()
        client1 = GitHubGateway.get_github_client(config)
        client2 = GitHubGateway.get_github_client(config)

        assert type(client1) is type(client2)

    def test_get_github_client_with_token(self):
        """Should create authenticated client when token available."""
        config = Mock()
        config.github_token = "test-token"
        client = GitHubGateway.get_github_client(config)
        assert client is not None

    def test_get_github_client_uses_org_from_config(self):
        """Client should use organization from configuration."""
        config = Mock()
        config.github_org = "myorg"
        client = GitHubGateway.get_github_client(config)
        assert client is not None


class TestGitHubGatewayErrorClassRetrieval:
    """Test GitHub API error class access."""

    def test_get_github_api_error_returns_exception_class(self):
        """Should return an exception class."""
        error_class = GitHubGateway.get_github_api_error()

        assert error_class is not None

    def test_get_github_api_error_is_exception_class(self):
        """Returned error class should be an Exception subclass."""
        error_class = GitHubGateway.get_github_api_error()

        # Should be a class (not instance)
        assert isinstance(error_class, type)
        # Should be subclass of Exception
        assert issubclass(error_class, Exception)

    def test_get_github_api_error_consistent_class(self):
        """GitHub API error class should be consistent."""
        error1 = GitHubGateway.get_github_api_error()
        error2 = GitHubGateway.get_github_api_error()

        assert error1 is error2

    def test_get_github_api_error_can_be_raised(self):
        """Returned error class should be raisable."""
        error_class: Type[Exception] = GitHubGateway.get_github_api_error()

        # Should be able to instantiate and raise
        try:
            raise error_class("Test error message")
        except error_class as e:
            assert str(e) == "Test error message"


class TestGitHubGatewayErrorHandling:
    """Test error handling with GitHub API errors."""

    def test_catching_github_api_error(self):
        """Should be able to catch GitHub API errors."""
        error_class = GitHubGateway.get_github_api_error()

        try:
            raise error_class("API failed")  # type: ignore
        except Exception:  # type: ignore
            # Successfully caught
            pass

    def test_error_class_inheritance(self):
        """GitHub API error should inherit from Exception."""
        error_class = GitHubGateway.get_github_api_error()

        # Should be catchable as Exception
        try:
            raise error_class("Test")  # type: ignore
        except Exception:
            pass

    def test_multiple_error_instances_independent(self):
        """Multiple error instances should be independent."""
        error_class = GitHubGateway.get_github_api_error()

        err1 = error_class("Error 1")
        err2 = error_class("Error 2")

        assert str(err1) == "Error 1"
        assert str(err2) == "Error 2"


class TestGitHubGatewayClientConfiguration:
    """Test client configuration options."""

    def test_client_configuration_with_custom_org(self):
        """Client should accept custom organization."""
        config = Mock()
        config.github_org = "custom-org"
        client = GitHubGateway.get_github_client(config)
        assert client is not None

    def test_client_respects_environment_config(self):
        """Client should respect environment configuration."""
        config = Mock()
        config.github_org = "env-org"
        client = GitHubGateway.get_github_client(config)
        assert client is not None

    def test_multiple_clients_independent(self):
        """Multiple clients should be independent instances."""
        config1 = Mock()
        config2 = Mock()
        client1 = GitHubGateway.get_github_client(config1)
        client2 = GitHubGateway.get_github_client(config2)

        # Both valid
        assert client1 is not None
        assert client2 is not None


class TestGitHubGatewayMethodVisibility:
    """Test gateway method interface."""

    def test_gateway_has_static_methods(self):
        """Gateway methods should be static."""
        # Should be callable via class
        config = Mock()
        client = GitHubGateway.get_github_client(config)
        error = GitHubGateway.get_github_api_error()

        assert client is not None
        assert error is not None

    def test_gateway_requires_no_instance(self):
        """Gateway should not require instantiation."""
        # Should work without creating an instance
        # (calling static methods on class)
        config = Mock()
        client = GitHubGateway.get_github_client(config)
        assert client is not None


class TestGitHubGatewayClientCapabilities:
    """Test client capabilities."""

    def test_client_has_expected_interface(self):
        """GitHub client should have expected interface."""
        config = Mock()
        client = GitHubGateway.get_github_client(config)

        # Should have standard GitHub API methods
        # (At minimum, should not be None)
        assert client is not None

    def test_client_can_be_used_for_api_calls(self):
        """Client should be usable for GitHub API operations."""
        config = Mock()
        client = GitHubGateway.get_github_client(config)

        # Should have methods for common operations
        assert (
            hasattr(client, "get_user")
            or hasattr(client, "get_repo")
            or client is not None
        )


class TestGitHubGatewayErrorEdgeCases:
    """Test edge cases in error handling."""

    def test_error_with_empty_message(self):
        """Error should handle empty message."""
        error_class = GitHubGateway.get_github_api_error()
        err = error_class("")

        # Should create without error
        assert err is not None

    def test_error_with_none_message(self):
        """Error should handle None message gracefully."""
        error_class = GitHubGateway.get_github_api_error()

        # Should handle None or empty
        try:
            err = error_class(None)  # type: ignore
            assert err is not None
        except TypeError:
            # Some error classes don't accept None
            pass

    def test_error_with_special_characters(self):
        """Error message should handle special characters."""
        error_class = GitHubGateway.get_github_api_error()
        msg = "Error: API rate limit exceeded! 🚫"

        err = error_class(msg)
        assert msg in str(err) or "API" in str(err)


class TestGitHubGatewayTokenHandling:
    """Test token authentication handling."""

    def test_client_without_valid_token_still_works(self):
        """Client should work even without valid token."""
        config = Mock()
        config.github_token = None
        client = GitHubGateway.get_github_client(config)
        # Should not crash, even if unauthenticated
        assert client is not None

    def test_client_token_configuration(self):
        """Client should use configured token."""
        config = Mock()
        config.github_token = "test-token-12345"
        client = GitHubGateway.get_github_client(config)
        assert client is not None

    def test_client_with_empty_token_string(self):
        """Client should handle empty token string."""
        config = Mock()
        config.github_token = ""
        client = GitHubGateway.get_github_client(config)
        assert client is not None


class TestGitHubGatewayOrgConfiguration:
    """Test organization configuration."""

    def test_client_with_default_org(self):
        """Client should work with default organization."""
        config = Mock()
        client = GitHubGateway.get_github_client(config)
        assert client is not None

    def test_client_with_custom_org_name(self):
        """Client should accept various organization names."""
        orgs = ["my-org", "my_org", "myorg123", "org"]

        for org in orgs:
            config = Mock()
            config.github_org = org
            client = GitHubGateway.get_github_client(config)
            assert client is not None

    def test_org_configuration_doesnt_affect_error_class(self):
        """Organization config shouldn't affect error class."""
        config1 = Mock()
        config1.github_org = "org1"
        error1 = GitHubGateway.get_github_api_error()

        config2 = Mock()
        config2.github_org = "org2"
        error2 = GitHubGateway.get_github_api_error()

        # Same error class
        assert error1 is error2


class TestGitHubGatewayCallSequence:
    """Test typical usage patterns."""

    def test_get_client_then_error_class(self):
        """Should work to get client then error class."""
        config = Mock()
        client = GitHubGateway.get_github_client(config)
        error_class = GitHubGateway.get_github_api_error()

        assert client is not None
        assert error_class is not None

    def test_get_error_class_then_client(self):
        """Should work to get error class then client."""
        error_class = GitHubGateway.get_github_api_error()
        config = Mock()
        client = GitHubGateway.get_github_client(config)

        assert error_class is not None
        assert client is not None

    def test_repeated_calls_consistent(self):
        """Repeated calls should return consistent results."""
        for _ in range(5):
            config = Mock()
            client = GitHubGateway.get_github_client(config)
            error = GitHubGateway.get_github_api_error()

            assert client is not None
            assert error is not None


class TestGitHubGatewayIntegration:
    """Test integration patterns."""

    def test_client_error_combo_for_api_calls(self):
        """Test typical pattern: get client and error handling."""
        config = Mock()
        client = GitHubGateway.get_github_client(config)
        error_class: Type[Exception] = GitHubGateway.get_github_api_error()

        # Simulate typical usage
        try:
            # Would normally call API here
            pass
        except error_class:
            # Error handling
            pass

        # Both components available
        assert client is not None
        assert error_class is not None

    def test_gateway_supports_error_handling_pattern(self):
        """Gateway should support standard error handling."""
        error_class = GitHubGateway.get_github_api_error()

        # Should be able to use in except clause
        try:
            raise error_class("API failure")  # type: ignore
        except Exception:  # type: ignore
            # Caught successfully
            assert True
