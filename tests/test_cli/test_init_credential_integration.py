from click.testing import CliRunner
from pathlib import Path
from roadmap.cli import main
from unittest.mock import patch


def test_init_uses_cli_token_and_stores_it(cli_runner):
    runner = cli_runner
    with runner.isolated_filesystem():
        fake_token = 'ghp_REALTOKEN'
        recorded = {}

        class DummyGitHubClient:
            def __init__(self, token):
                # record the token used to construct the client
                recorded['client_token'] = token
            def _make_request(self, *args, **kwargs):
                return {'login': 'mockuser'}
            def get_repository_info(self, owner, repo):
                return {'full_name': f'{owner}/{repo}', 'permissions': {'admin': True}}

        class DummyCredManager:
            def __init__(self):
                recorded['cred_instance'] = self
                self._stored = None
            def get_github_token(self):
                return None
            def store_github_token(self, token):
                self._stored = token
                recorded['stored_token'] = token

        with patch('roadmap.cli.core.GitHubClient', DummyGitHubClient), patch('roadmap.cli.core.CredentialManager', DummyCredManager):
            result = runner.invoke(
                main,
                [
                    'init',
                    '--non-interactive',
                    '--yes',
                    '--github-repo',
                    'owner/repo',
                    '--github-token',
                    fake_token,
                    '--project-name',
                    'Integration Test',
                ],
            )

            assert result.exit_code == 0, result.output
            # Ensure the GitHub client got constructed with the CLI token
            assert recorded.get('client_token') == fake_token
            # Ensure the credential manager stored the token
            assert recorded.get('stored_token') == fake_token
