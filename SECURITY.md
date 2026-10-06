# Security Policy

## Supported Versions

This project is currently in beta.
Security fixes are prioritized for the latest release line.

## Reporting a Vulnerability

Please do not report security vulnerabilities in public issues.
Use one of the private channels below.

- Email: shane.wilkins@gmail.com
- GitHub private advisories: https://github.com/shanewilkins/roadmap/security/advisories/new

Include as much detail as possible.

- Affected version.
- Reproduction steps.
- Impact and expected behavior.
- Any proposed mitigations.

## Response Process

- We will acknowledge receipt as quickly as possible.
- We will investigate and validate the report.
- We will coordinate remediation and release timing.
- We will publish an advisory when appropriate.

## Security Practices

This repository uses static analysis and security checks in CI.
Current static security checks include Bandit.
Type and lint checks also run as part of the quality gate.
The required quality job also runs pinned `pip-audit` against a hashed export
of the locked runtime and development dependencies. Known vulnerabilities or
audit collection failures fail the job. Dependabot provides ongoing alerts
between CI runs. See CONTRIBUTING.md for the local audit command.

For detailed implementation notes and operational guidance, see
docs/architecture/adr/0002-git-owned-synchronization.md.
