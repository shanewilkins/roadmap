# Init Enhancements

This document describes the enhanced `roadmap init` flow implemented in Phase 1-3.

Features
- Automatic project creation (main project document)
- Project name auto-detection from git or directory
- `--template` builtin templates plus `--template-path` for custom template files
- Interactive and non-interactive flows (`--non-interactive`, `--yes`)
- `--skip-github` and `--skip-project` to skip optional steps
- `--github-token` to configure GitHub integration non-interactively
- `--github-token` to configure GitHub integration non-interactively
	- You can also provide the token via environment variable for CI:
		- `export ROADMAP_GITHUB_TOKEN=...`
- Post-init validation checks for `config.yaml` and project files
- Init manifest (`.roadmap/.init_manifest.json`) to support targeted rollback on errors

Usage examples

```bash
# Interactive init with project detection
roadmap init

# Non-interactive init with custom template and token
roadmap init --non-interactive --yes --template-path ./my_project.md --github-token $GITHUB_TOKEN
```

Notes
- Credential storage uses the project's `CredentialManager` (wraps keyring/backends).
- The manifest is written to `.roadmap/.init_manifest.json` and used for rollback on failure.
- Consider running `roadmap init --dry-run` when testing templates.

More examples

```bash
# Non-interactive init with token from env
ROADMAP_GITHUB_TOKEN=$GITHUB_TOKEN roadmap init --non-interactive --yes --github-repo owner/repo --project-name "My Project"
```
