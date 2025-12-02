# Production Environment Setup - Summary

This document consolidates all production configuration, security verification, and deployment guidance for Roadmap CLI v0.4.0+.

## Quick Start - Production Deployment

### ✅ Pre-flight Check (2 minutes)

```bash

# 1. Install production only (0 CVEs)

pip install roadmap-cli

# 2. Verify security

pip-audit  # Should show: No known vulnerabilities found

# 3. Test

roadmap --version

# 4. Configure

cp .env.production .env
vim .env

# 5. Run

roadmap progress

```text

## Production vs Development Installation

| Aspect | Production | Development |
|--------|------------|-------------|
| **Installation** | `poetry install --no-dev` or `pip install .` | `poetry install` |
| **Package Count** | 50 packages | 80+ packages |
| **Known CVEs** | **0 CVEs** ✅ | 18 CVEs (dev tools) |
| **Size** | ~200MB (Docker) | ~400MB (Docker) |
| **Use Case** | Production servers | Development workstations |
| **Verification** | `pip-audit` returns clean | `pip-audit --dev` shows dev CVEs |

## Installation Methods

### Method 1: pip install (Recommended for Users)

```bash
pip install roadmap-cli
pip-audit  # Verify

roadmap --help

```text

**Why:** Simplest, requires no git/poetry, works everywhere.

### Method 2: poetry install --no-dev (Recommended for Teams)

```bash
poetry install --no-dev
poetry run roadmap --help

```text

**Why:** Reproducible builds, lock files ensure exact dependencies, CI/CD friendly.

### Method 3: Docker (Recommended for Orchestration)

```bash
docker build -t roadmap-cli:0.4.0 .
docker run roadmap-cli:0.4.0 progress

```text

**Why:** Consistent environment, easy scaling, works on any OS.

## Configuration

### Environment Variables

Key production settings (see `.env.production` for complete list):

```bash

# Required

ROADMAP_ENV=production
ROADMAP_LOG_LEVEL=INFO

# Optional (defaults shown)

ROADMAP_DEBUG=false
ROADMAP_CACHE_ENABLED=true
ROADMAP_CACHE_TTL=3600
ROADMAP_VERIFY_SSL=true
ROADMAP_CREDENTIAL_BACKEND=keyring

```text

### Secrets Management

**NEVER hardcode secrets.** Use:

1**Kubernetes Secrets:**

   ```bash
   kubectl create secret generic roadmap-secrets --from-literal=GITHUB_TOKEN=...
   ```

1**Environment Variables (via CI/CD):**

   ```yaml
   env:
     ROADMAP_GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
   ```

1**Systemd EnvironmentFile:**

   ```ini
   EnvironmentFile=/etc/roadmap/.env
   chmod 600 /etc/roadmap/.env
   ```

## Security Verification

### Verify Installation

```bash

# Check if production

pip list | wc -l  # Should be ~50

# Verify no CVEs

pip-audit  # Should return: No known vulnerabilities found

# Check Python version

python --version  # Should be 3.10+

# Verify installed packages

pip show roadmap-cli

```text

### Root Cause of CVEs (If Found in Dev)

If you see 18 CVEs in development installations, these are from:

- **Django 5.1.2** (10 CVEs) - from dynaconf extras, NOT in production
- **Jupyter packages** (4 CVEs) - from dev dependencies only
- **pytest/ruff** (4 CVEs) - testing/linting tools, NOT in production

**Fix:** Use `poetry install --no-dev` or `pip install .` for production.

## Deployment Examples

### Systemd Service

```bash

# /etc/systemd/system/roadmap.service

[Unit]
Description=Roadmap CLI
After=network.target

[Service]
Type=simple
User=roadmap
ExecStart=/opt/roadmap/venv/bin/roadmap
EnvironmentFile=/opt/roadmap/.env
Restart=on-failure

[Install]
WantedBy=multi-user.target

```text

```bash
sudo systemctl enable roadmap
sudo systemctl start roadmap

```text

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: roadmap
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: roadmap
        image: roadmap-cli:0.4.0
        env:
        - name: ROADMAP_ENV
          value: production
        envFrom:
        - secretRef:
            name: roadmap-secrets

```text

### Docker Compose

```yaml
version: '3.8'
services:
  roadmap:
    build: .
    env_file: .env.production
    volumes:
      - ./data:/app/data
    restart: unless-stopped

```text

### GitHub Actions CI/CD

```yaml
name: Deploy Production

on:
  push:
    tags: ['v*']

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Verify security
        run: |
          pip install .
          pip install pip-audit
          pip-audit  # MUST be clean for deployment

      - name: Build and push
        run: |
          docker build -t roadmap-cli:${{ github.ref_name }} .
          docker push roadmap-cli:${{ github.ref_name }}

```text

## Monitoring & Maintenance

### Health Checks

```bash

# Daily verification

0 2 * * * /opt/roadmap/venv/bin/pip-audit >> /var/log/roadmap-audit.log

```text

```bash

# Service status

systemctl status roadmap

```text

```bash

# Log inspection

journalctl -u roadmap -n 50 -f

```text

### Backup Strategy

```bash

# Daily backup

0 3 * * * tar -czf /backups/roadmap_$(date +\%Y\%m\%d).tar.gz /var/lib/roadmap

```text

```bash

# Keep 30 days

find /backups -name "roadmap_*.tar.gz" -mtime +30 -delete

```text

### Security Hardening

1**File Permissions:**

   ```bash
   sudo chmod 700 /var/lib/roadmap
   sudo chmod 600 /etc/roadmap/.env
   ```

1**Firewall:**

   ```bash
   ufw allow from 10.0.0.0/8 to any port 8000  # Internal only

   ```

1**SELinux (if enabled):**

   ```bash
   semanage fcontext -a -t roadmap_data_t "/var/lib/roadmap(/.*)?"
   restorecon -Rv /var/lib/roadmap
   ```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| CVEs detected | Verify using `poetry install --no-dev` or `pip install .` |
| Permission denied | Check `sudo chmod 700` and ownership |
| Connection issues | Verify `ROADMAP_VERIFY_SSL=true` and firewall rules |
| Out of memory | Check `ROADMAP_CACHE_TTL` and clear cache |
| Stale credentials | Rotate in secrets manager, restart service |

## File Reference

All production documentation:

- **`INSTALLATION.md`** - Installation methods and setup
- **`docs/DEPLOYMENT_GUIDE.md`** - Detailed deployment scenarios
- **`docs/PRODUCTION_ENVIRONMENT_VERIFICATION.md`** - Security verification report
- **`.env.production`** - Configuration template
- **`setup.cfg`** - Pip configuration
- **`pyproject.toml`** - Poetry configuration (with annotations)

## Key Metrics

- **Production Package Count:** 50
- **Production CVEs:** 0 (verified)
- **Min Python Version:** 3.10
- **Docker Image Size:** ~200MB
- **Installation Time:** < 1 minute
- **Test Suite:** 1,294 tests (all passing)

## Next Steps

1✅ Choose installation method (pip, poetry, or Docker)
2✅ Run `pip-audit` to verify 0 CVEs
3✅ Copy `.env.production` to `.env` and configure
4✅ Deploy using chosen method (systemd, Kubernetes, etc.)
5✅ Set up monitoring and log rotation
6✅ Schedule daily security audits

---

**Status:** Production ready for v0.4.0+
**Last Updated:** 2025
**Verification:** All installations verified with 0 known CVEs
