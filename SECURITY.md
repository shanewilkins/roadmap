# Security Policy

This document outlines the security policy for Roadmap CLI, including how to report vulnerabilities, our security process, and supported versions.

## Reporting Security Vulnerabilities

**Do not open public GitHub issues for security vulnerabilities.** This could allow malicious actors to exploit the vulnerability before a fix is available.

### Responsible Disclosure

If you discover a security vulnerability in Roadmap CLI, please report it responsibly:

1. **Email:** `security@roadmap-cli.dev`
   - Subject line: `SECURITY: [Brief Description]`
   - Include version number where vulnerability was discovered
   - Include detailed reproduction steps
   - Allow 90 days for fix development

2. **GitHub Security Advisory:** Use [GitHub's private vulnerability reporting](https://github.com/shanewilkins/roadmap/security/advisories/new)
   - Provides secure communication with maintainers
   - Embargoed disclosure timeline
   - CVE assignment coordination

3. **HackerOne (if applicable):** [roadmap-cli on HackerOne](https://hackerone.com/roadmap-cli)

### Disclosure Timeline

- **Day 0:** Vulnerability reported
- **Day 1:** Acknowledgment of receipt
- **Day 7:** Initial assessment and timeline
- **Day 30:** Target patch release date
- **Day 90:** Public disclosure if patch available
- **Day 90+:** Disclosure even if patch delayed (with justification)

**For critical vulnerabilities (CVSS 9.0+):** Coordinated disclosure may be expedited to 48 hours.

## Security Supported Versions

| Version | Python | Status | Security Updates Until |
|---------|--------|--------|------------------------|
| 0.4.x   | 3.10+ | ✅ Active | June 2026 |
| 0.3.x   | 3.9+ | ⚠️ Limited | December 2025 |
| < 0.3 | Any | ❌ Unsupported | N/A |

**Security Updates:** Only available for currently supported versions. We recommend keeping Roadmap CLI updated to the latest stable release.

## Known Security Practices

### Credential Security

- ✅ GitHub tokens stored in secure OS credential storage (Keyring/SecretService)
- ✅ Credentials never logged or printed
- ✅ Environment variable fallback with validation
- ✅ Token masking in error messages (`ghp_****...`)
- ✅ Automatic token refresh with atomic updates

### Input Validation

- ✅ All CLI inputs validated against injection attacks
- ✅ YAML/JSON parsing with strict mode enabled
- ✅ Special character escaping for git operations
- ✅ Path traversal prevention via absolute path validation
- ✅ URL scheme validation for remote repositories

### File System Security

- ✅ Secure file creation with `0o600` permissions
- ✅ Atomic write operations prevent corruption
- ✅ Symlink resolution validation
- ✅ Directory permission verification
- ✅ Temporary file cleanup on error

### Git Integration Security

- ✅ Git commands constructed as list (prevents shell injection)
- ✅ Remote URLs validated before operations
- ✅ Branch names validated with regex
- ✅ Commit messages sanitized
- ✅ Git hooks use absolute paths

### Data Privacy

- ✅ GitHub PAT tokens masked in logs
- ✅ Home paths sanitized in error messages
- ✅ Git config credentials never logged
- ✅ JSON responses filtered for sensitive fields
- ✅ Exception stack traces sanitized

## Dependency Management

### Vulnerability Scanning

Production installations use **0 known CVEs**:

```bash
# Verify production dependencies
pip install roadmap-cli
pip-audit  # Should show: No known vulnerabilities found

# Dev-only CVEs are NOT in production
pip install -e ".[dev]"
pip-audit --dev  # May show dev-only vulnerabilities
```

### Dependency Policy

- **Runtime Dependencies:** Carefully selected, regularly audited
- **Dev Dependencies:** Not included in production installations
- **Pinned Versions:** Specified in `pyproject.toml` for reproducibility
- **Security Patches:** Applied within 7 days of disclosure

### Automatic Dependency Updates

GitHub Dependabot is configured to:
- Create pull requests for dependency updates
- Run full test suite before merging
- Verify security audit (pip-audit) passes
- Auto-merge patch updates after CI passes

## Security Testing

### Static Analysis

- **Pyright:** Type checking and type safety
- **Ruff:** Linting with security rules enabled
- **Bandit:** Security-focused code analysis (when running dev tools)

### Dynamic Analysis

- **Unit Tests:** 87% code coverage with security-focused tests
- **Integration Tests:** Real-world scenario testing
- **Penetration Tests:** Simulated attack scenarios

### Continuous Monitoring

- **GitHub Security:** Dependency alerts enabled
- **pip-audit:** Production CVE verification
- **SAST Scanning:** Static Application Security Testing in CI/CD

## Security Hardening Checklist

For production deployments, implement these security measures:

### Access Control

- [ ] Run Roadmap CLI as unprivileged user (not root)
- [ ] Restrict file permissions to owner only (`chmod 700`)
- [ ] Use OS-level credential storage (Keyring/SecretService)
- [ ] Implement SSH key authentication for git operations

### Network Security

- [ ] Use HTTPS for all GitHub operations
- [ ] Verify SSL certificates (enabled by default)
- [ ] Restrict outbound network access via firewall
- [ ] Use VPN for corporate environments

### Data Security

- [ ] Encrypt sensitive data at rest (database, configs)
- [ ] Enable audit logging
- [ ] Implement log rotation (7+ day retention)
- [ ] Secure backup storage

### Deployment Security

- [ ] Use production installation (`poetry install --no-dev`)
- [ ] Verify 0 CVEs with `pip-audit`
- [ ] Deploy in container with read-only filesystem
- [ ] Implement health checks and monitoring
- [ ] Set resource limits (CPU, memory)

### Secrets Management

- [ ] Never hardcode credentials in configuration
- [ ] Use environment variables or secrets manager
- [ ] Rotate credentials regularly (quarterly minimum)
- [ ] Revoke compromised tokens immediately
- [ ] Monitor token usage and access patterns

## Security Architecture

### Threat Model

**Assets Protected:**
- GitHub access tokens
- Project roadmap data
- User credentials and secrets
- System resources

**Threat Actors:**
- Malicious local users
- Network-based attackers
- Dependency vulnerabilities
- Social engineering

**Attack Vectors:**
- Command injection via git operations
- Path traversal via file operations
- Credential theft or exposure
- XML External Entity (XXE) attacks
- Denial of Service (resource exhaustion)

### Defense-in-Depth

1. **Input Validation:** All user inputs validated
2. **Access Control:** Minimal required permissions
3. **Secure Defaults:** Security-first configuration
4. **Fail Secure:** Secure behavior on errors
5. **Monitoring:** Audit logging for security events

## Incident Response

### Security Incident Procedure

1. **Discovery:** Security vulnerability identified
2. **Notification:** Core team alerted immediately
3. **Assessment:** Severity, scope, and impact determined
4. **Remediation:** Patch developed and tested
5. **Release:** Security update released
6. **Communication:** Vulnerability disclosed responsibly
7. **Postmortem:** Root cause analysis performed

### Incident Communication

- Affected users notified via:
  - GitHub Security Advisory
  - Release notes
  - Email (if applicable)
  - Twitter/Blog post for critical issues

## Security Resources

### For Users

- **[Installation Guide](../INSTALLATION.md)** - Secure installation
- **[Production Environment Verification](./PRODUCTION_ENVIRONMENT_VERIFICATION.md)** - CVE status
- **[Deployment Guide](./DEPLOYMENT_GUIDE.md)** - Security hardening

### For Developers

- **[Security Tests](../tests/security/)** - Security test suite
- **[Contributing Guide](../CONTRIBUTING.md)** - Development security
- **[Security Architecture Docs](./SECURITY_ARCHITECTURE.md)** - Detailed threat model

### External Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [Python Security](https://python.readthedocs.io/en/stable/library/security_warnings.html)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

## Compliance

### Standards and Frameworks

- ✅ **OWASP Top 10:** Addressed in design
- ✅ **CWE Top 25:** Regular audits performed
- ✅ **NIST Cybersecurity:** Framework-aligned
- ✅ **PCI DSS (applicable):** No payment processing

### Audit Logs

All security-relevant events are logged:
- Authentication attempts
- Authorization failures
- Data access (sensitive files)
- Configuration changes
- Token refresh operations

## Contact

For security-related questions or concerns:

- **Security Email:** `security@roadmap-cli.dev`
- **GitHub Issues:** For non-security bugs only
- **Security Advisories:** [GitHub Repository Security](https://github.com/shanewilkins/roadmap/security)

---

**Last Updated:** December 2, 2025
**Policy Version:** 1.0
**Next Review:** June 2026
