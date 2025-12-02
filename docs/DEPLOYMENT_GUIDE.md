# Deployment Guide

This guide covers deploying Roadmap CLI in production environments with security best practices.

## Overview

Roadmap CLI production deployments use one of three methods:

1. **pip install** (recommended for most users)
2. **poetry install --no-dev** (recommended for reproducible builds)
3. **Docker** (recommended for containerized deployments)

All methods result in **0 known CVEs** when properly configured.

## Pre-Deployment Checklist

Before deploying to production:

- [ ] Run `pip-audit` to verify no CVEs: `PIPAPI_PYTHON_LOCATION=$(which python) pip-audit`
- [ ] Verify Python version: `python --version` (3.10+)
- [ ] Check system dependencies available (git, etc.)
- [ ] Copy `.env.production` to `.env` and configure settings
- [ ] Test CLI locally: `roadmap --help`
- [ ] Review SECURITY.md for security considerations
- [ ] Set up log rotation (if using file logging)

## Method 1: pip install (Simplest)

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install production package
pip install roadmap-cli

# Verify installation
roadmap --version
```

### Verification

```bash
# Verify no CVEs
pip-audit

# Verify dependencies
pip list | grep -E "roadmap|click|pydantic|pyyaml|requests|aiohttp|pandas"
```

### Deployment

```bash
# Copy configuration
cp .env.production .env
vim .env  # Edit as needed

# Run application
roadmap --help
```

## Method 2: poetry install --no-dev (Reproducible)

### Installation

```bash
# Install poetry (if not already installed)
pip install poetry

# Clone/download repository
git clone https://github.com/shanewilkins/roadmap.git
cd roadmap

# Install production dependencies
poetry install --no-dev

# Verify installation
poetry run roadmap --version
```

### Verification

```bash
# Verify no CVEs
pip-audit

# Verify reproducibility
poetry lock --no-update  # Ensures lock file is committed
poetry install --no-dev --no-root  # Reproduces exact environment
```

### Deployment

```bash
# Copy configuration
cp .env.production .env
vim .env  # Edit as needed

# Run application via poetry
poetry run roadmap --help

# Or activate venv
source $(poetry env info --path)/bin/activate
roadmap --help
```

## Method 3: Docker (Containerized)

### Dockerfile (Production)

```dockerfile
FROM python:3.12-slim

LABEL maintainer="Roadmap CLI"
LABEL description="Enterprise project management tool"

# Set working directory
WORKDIR /app

# Copy files
COPY pyproject.toml setup.cfg README.md LICENSE.md ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Create non-root user
RUN useradd -m -u 1000 roadmap && \
    chown -R roadmap:roadmap /app

USER roadmap

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD roadmap --help > /dev/null || exit 1

# Entry point
ENTRYPOINT ["roadmap"]
CMD ["--help"]
```

### Build & Run

```bash
# Build image
docker build -t roadmap-cli:0.4.0 .

# Run container
docker run --rm -v $(pwd)/config:/app/config \
  -e ROADMAP_CONFIG_PATH=/app/config \
  roadmap-cli:0.4.0 list

# Run with environment file
docker run --rm --env-file .env.production \
  roadmap-cli:0.4.0 progress
```

### Docker Compose

```yaml
version: '3.8'

services:
  roadmap:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: roadmap-cli
    env_file: .env.production
    volumes:
      - ./data:/app/data
      - ./config:/app/config
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "roadmap", "--help"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 5s
```

### Verify Docker Build

```bash
# Check image size (should be ~200MB)
docker images roadmap-cli

# Verify no CVEs in container
docker run --rm roadmap-cli:0.4.0 python -m pip list

# Run security audit in container
docker run --rm roadmap-cli:0.4.0 pip-audit
```

## Configuration

### Environment Variables

Key production environment variables (see `.env.production` for full list):

```bash
# Application
ROADMAP_ENV=production
ROADMAP_DEBUG=false
ROADMAP_LOG_LEVEL=INFO

# Credentials (use secrets manager in production!)
ROADMAP_GITHUB_TOKEN=
ROADMAP_GIT_USER_EMAIL=
ROADMAP_GIT_USER_NAME=

# Storage
ROADMAP_DATA_PATH=/var/lib/roadmap
ROADMAP_CACHE_ENABLED=true
ROADMAP_CACHE_TTL=3600

# Security
ROADMAP_CREDENTIAL_BACKEND=keyring
ROADMAP_VERIFY_SSL=true
```

### Secrets Management

**DO NOT hardcode secrets!** Use one of:

1. **Environment variables** (via secrets manager)
   ```bash
   # Kubernetes
   kubectl create secret generic roadmap-secrets \
     --from-literal=ROADMAP_GITHUB_TOKEN=...

   # Docker Swarm
   docker secret create roadmap_github_token -
   ```

2. **Systemd secrets**
   ```bash
   # /etc/systemd/system/roadmap.service.d/override.conf
   [Service]
   Environment="ROADMAP_GITHUB_TOKEN=..."
   EnvironmentFile=/etc/roadmap/.env
   ```

3. **HashiCorp Vault**
   ```bash
   # Load secrets from Vault
   export ROADMAP_GITHUB_TOKEN=$(vault kv get -field=token secret/roadmap/github)
   ```

## Deployment Scenarios

### Linux Systemd Service

```bash
# Create service file: /etc/systemd/system/roadmap.service
[Unit]
Description=Roadmap CLI
After=network.target

[Service]
Type=simple
User=roadmap
WorkingDirectory=/home/roadmap
ExecStart=/home/roadmap/venv/bin/roadmap
EnvironmentFile=/home/roadmap/.env
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable roadmap
sudo systemctl start roadmap

# Check status
sudo systemctl status roadmap
sudo journalctl -u roadmap -f
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: roadmap
  labels:
    app: roadmap
spec:
  replicas: 1
  selector:
    matchLabels:
      app: roadmap
  template:
    metadata:
      labels:
        app: roadmap
    spec:
      containers:
      - name: roadmap
        image: roadmap-cli:0.4.0
        imagePullPolicy: IfNotPresent
        command: ["roadmap", "progress"]
        env:
        - name: ROADMAP_ENV
          value: "production"
        - name: ROADMAP_LOG_LEVEL
          value: "INFO"
        envFrom:
        - secretRef:
            name: roadmap-secrets
        volumeMounts:
        - name: data
          mountPath: /app/data
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          exec:
            command: ["roadmap", "--help"]
          initialDelaySeconds: 10
          periodSeconds: 30
      volumes:
      - name: data
        emptyDir: {}
```

### AWS Lambda

```python
# lambda_function.py
import json
import subprocess
from roadmap.cli import main

def lambda_handler(event, context):
    """Run roadmap CLI command from Lambda"""

    command = event.get('command', ['list'])

    try:
        # Execute roadmap command
        result = subprocess.run(
            ['roadmap'] + command,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        return {
            'statusCode': 200,
            'body': json.dumps({
                'stdout': result.stdout,
                'returncode': result.returncode
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```

## Monitoring & Logging

### Log Rotation (Systemd)

```bash
# /etc/logrotate.d/roadmap
/var/log/roadmap/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 roadmap roadmap
    sharedscripts
    postrotate
        systemctl reload roadmap > /dev/null 2>&1 || true
    endscript
}
```

### Prometheus Metrics

```python
# In roadmap code
from prometheus_client import Counter, Histogram, start_http_server

commands_total = Counter('roadmap_commands_total', 'Total commands', ['command'])
command_duration = Histogram('roadmap_command_duration_seconds', 'Command duration')

@command_duration.time()
def execute_command(cmd):
    commands_total.labels(command=cmd).inc()
    # Execute command
```

### CloudWatch Logs (AWS)

```bash
# /etc/awslogs/config/roadmap.conf
[/var/log/roadmap/app.log]
log_group_name = /aws/roadmap/application
log_stream_name = {instance_id}
datetime_format = %Y-%m-%d %H:%M:%S
file = /var/log/roadmap/app.log
initial_interval = 5
log_retention_in_days = 30
```

## Backup & Recovery

### Data Backup

```bash
# Daily backup script: /usr/local/bin/roadmap-backup.sh
#!/bin/bash

BACKUP_DIR="/backups/roadmap"
DATA_DIR="/var/lib/roadmap"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Backup data
tar -czf "$BACKUP_DIR/roadmap_$DATE.tar.gz" \
  --exclude="*.log" \
  "$DATA_DIR"

# Keep only 30 days of backups
find "$BACKUP_DIR" -name "roadmap_*.tar.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR/roadmap_$DATE.tar.gz"
```

### Recovery

```bash
# Restore from backup
tar -xzf /backups/roadmap/roadmap_20240101_120000.tar.gz -C /

# Verify
roadmap list
```

## Security Hardening

### Firewall Rules

```bash
# If exposing HTTP/API interface
ufw allow 8000/tcp  # API port
ufw deny from 0.0.0.0/0 to any port 8000  # Default deny
ufw allow from 10.0.0.0/8 to any port 8000  # Allow internal network
```

### SELinux Policy

```bash
# Create custom policy
semanage fcontext -a -t roadmap_data_t "/var/lib/roadmap(/.*)?"
restorecon -Rv /var/lib/roadmap

semanage port -a -t roadmap_port_t -p tcp 8000
```

### File Permissions

```bash
# Secure data directory
sudo mkdir -p /var/lib/roadmap
sudo chown roadmap:roadmap /var/lib/roadmap
sudo chmod 700 /var/lib/roadmap

# Secure configuration
sudo chmod 600 /etc/roadmap/.env
sudo chmod 600 /etc/roadmap/.env.production
```

## Troubleshooting

### Check CVE Status

```bash
# Verify production installation has 0 CVEs
pip-audit --desc

# If CVEs found, check dev vs production
pip-audit --dev --desc  # Might show dev-only CVEs
```

### Performance Tuning

```bash
# Monitor resource usage
ps aux | grep roadmap
top -p $(pgrep -f roadmap)

# Check cache effectiveness
roadmap metrics cache-hit-rate

# Adjust thread pool
export ROADMAP_MAX_WORKERS=8
roadmap process --parallel
```

### Debug Mode

```bash
# Enable debug logging
export ROADMAP_DEBUG=true
export ROADMAP_LOG_LEVEL=DEBUG
roadmap --verbose list
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy to Production

on:
  release:
    types: [published]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install and verify
        run: |
          pip install --upgrade pip
          pip install .
          pip-audit  # Verify 0 CVEs

      - name: Build Docker image
        run: docker build -t roadmap-cli:${{ github.ref_name }} .

      - name: Push to registry
        run: |
          echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USER }} --password-stdin
          docker push roadmap-cli:${{ github.ref_name }}

      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/roadmap \
            roadmap=roadmap-cli:${{ github.ref_name }}
```

---

## Key Takeaways

1. **Always use production installation modes** (`--no-dev`, `pip install .`)
2. **Verify 0 CVEs** before deployment with `pip-audit`
3. **Use secrets management**, never hardcode credentials
4. **Monitor logs and metrics** in production
5. **Perform regular backups** of critical data
6. **Keep Python updated** to latest patch version (3.12.x)

For more information, see:
- `INSTALLATION.md` - Installation methods
- `PRODUCTION_ENVIRONMENT_VERIFICATION.md` - Security verification details
- `docs/SECURITY.md` - Security policy and reporting
