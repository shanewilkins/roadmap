from unittest.mock import patch

import pytest
from roadmap.cli import main

pytestmark = pytest.mark.skip(reason="CLI command integration tests - complex Click mocking")


def test_init_uses_cli_token_and_stores_it(cli_runner):
    runner = cli_runner
    with runner.isolated_filesystem():
        fake_token = "ghp_REALTOKEN"
        recorded = {}

        class DummyGitHubClient:
            def __init__(self, token):
                # record the token used to construct the client
                recorded["client_token"] = token

            def _make_request(self, *args, **kwargs):
                # Mock Response object with json() method
                class MockResponse:
                    def json(self):
                        return {"login": "mockuser"}

                return MockResponse()

            def set_repository(self, owner, repo):
                pass

            def test_repository_access(self):
                return {"full_name": "owner/repo", "permissions": {"admin": True}}

        class DummyCredManager:
            def __init__(self):
                recorded["cred_instance"] = self
                self._stored = None

            def get_token(self):
                return None

            def store_token(self, token):
                self._stored = token
                recorded["stored_token"] = token

        with (
            patch("roadmap.cli.core.GitHubClient", DummyGitHubClient),
            patch("roadmap.cli.core.CredentialManager", DummyCredManager),
        ):
            result = runner.invoke(
                main,
                [
                    "init",
                    "--non-interactive",
                    "--yes",
                    "--github-repo",
                    "owner/repo",
                    "--github-token",
                    fake_token,
                    "--project-name",
                    "Integration Test",
                ],
            )

            assert result.exit_code == 0, result.output
            # Ensure the GitHub client got constructed with the CLI token
            assert recorded.get("client_token") == fake_token
            # Ensure the credential manager stored the token
            assert recorded.get("stored_token") == fake_token
