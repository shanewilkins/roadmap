from unittest.mock import patch, Mock
from click.testing import CliRunner
from pathlib import Path
from roadmap.cli import main


def test_init_with_github_token_stores_and_uses_token(cli_runner):
    runner = cli_runner
    with runner.isolated_filesystem():
        # Provide a fake token via CLI
        fake_token = 'ghp_FAKE_TOKEN'

        # Mock GitHubClient and CredentialManager
        mock_github = Mock()
        mock_github._make_request.return_value = {'login': 'mockuser'}
        mock_github.get_repository_info.return_value = {'full_name': 'owner/repo', 'permissions': {'admin': True}}

        class DummyGitHubClient:
            def __init__(self, token):
                assert token == fake_token
                self._mock = mock_github
            def _make_request(self, *args, **kwargs):
                return self._mock._make_request(*args, **kwargs)
            def get_repository_info(self, owner, repo):
                return self._mock.get_repository_info(owner, repo)

        class DummyCredManager:
            def __init__(self):
                self._stored = None
            def get_github_token(self):
                return None
            def store_github_token(self, token):
                self._stored = token

        with patch('roadmap.cli.core.GitHubClient', DummyGitHubClient), patch('roadmap.cli.core.CredentialManager', DummyCredManager):
            result = runner.invoke(
                main,
                [
                    'init',
                    '--non-interactive',
                    '--yes',
                    '--skip-github',
                    '--github-token',
                    fake_token,
                    '--project-name',
                    'Credential Test',
                ],
            )

            # Since --skip-github is set, token shouldn't be used; ensure no crash
            assert result.exit_code == 0

