# Roadmap CLI Installation and Setup Guide

Complete guide for installing and configuring the Roadmap CLI tool for various environments and use cases.

## 🚀 Quick Installation

### Option 1: Install from PyPI (Recommended)

```bash
# Install the latest stable version
pip install roadmap-cli

# Verify installation
roadmap --version
```

### Option 2: Install from Source

```bash
# Clone the repository
git clone https://github.com/yourusername/roadmap.git
cd roadmap

# Install with Poetry (recommended for development)
poetry install
poetry shell

# Or install with pip
pip install -e .
```

### Option 3: Install with pipx (Isolated Environment)

```bash
# Install pipx if not already installed
pip install --user pipx
pipx ensurepath

# Install roadmap-cli in isolated environment
pipx install roadmap-cli

# Verify installation
roadmap --version
```

## 📋 System Requirements

### Minimum Requirements

- **Python**: 3.12+ (recommended), 3.8+ (minimum)
- **Operating System**: macOS, Linux, Windows
- **Memory**: 256MB RAM
- **Storage**: 50MB free space

### Recommended Requirements

- **Python**: 3.12+ for best performance
- **Memory**: 1GB RAM for large projects (1000+ issues)
- **Storage**: 500MB for backups and caching
- **Network**: Stable internet for GitHub sync

### Python Version Compatibility

| Python Version | Support Status | Notes |
|----------------|----------------|-------|
| 3.12+ | ✅ Recommended | Latest features, best performance |
| 3.11 | ✅ Fully Supported | Excellent performance |
| 3.10 | ✅ Fully Supported | Good performance |
| 3.9 | ✅ Supported | Basic features work |
| 3.8 | ⚠️ Minimum | Limited features |
| < 3.8 | ❌ Not Supported | Please upgrade Python |

## 🔧 Initial Setup

### 1. Basic Project Initialization

```bash
# Navigate to your project directory
cd /path/to/your/project

# Initialize a new roadmap
roadmap init

# Verify initialization
roadmap status
```

**Expected Output:**
```
🗺️  Initializing new roadmap...
✅ Roadmap initialized successfully!

Created the following structure:
  .roadmap/
  ├── issues/
  ├── milestones/
  ├── templates/
  └── config.yaml

Try: roadmap issue create 'My first issue'
```

### 2. Configuration File Setup

The initialization creates a `config.yaml` file that you can customize:

```yaml
# .roadmap/config.yaml
project:
  name: "My Project"
  description: "Project roadmap and issue tracking"
  version: "1.0.0"

github:
  # Will be configured during sync setup
  repository: null
  token: null

settings:
  default_priority: "medium"
  default_assignee: null
  auto_backup: true
  validation_strict: true

performance:
  sync_workers: 8
  batch_size: 50
  cache_ttl: 300  # 5 minutes
```

## 🔐 GitHub Integration Setup

### 1. Generate GitHub Token

**Step-by-step GitHub token creation:**

1. **Go to GitHub Settings**
   - Visit: https://github.com/settings/tokens
   - Click "Generate new token" → "Generate new token (classic)"

2. **Configure Token Permissions**
   ```
   ✅ repo (for private repositories)
   ✅ public_repo (for public repositories)
   ✅ write:issues (to create and update issues)
   ✅ read:org (to access organization repositories)
   ```

3. **Set Token Expiration**
   - Choose appropriate expiration (30-90 days recommended)
   - Set up calendar reminder for renewal

4. **Copy Token**
   - Copy the generated token immediately
   - Store securely (you won't see it again)

### 2. Configure GitHub Integration

```bash
# Basic setup
roadmap sync setup \
  --token "your-github-token" \
  --repo "username/repository-name"

# Enterprise GitHub setup
roadmap sync setup \
  --token "enterprise-token" \
  --repo "org/project" \
  --github-url "https://github.enterprise.com"

# Test the connection
roadmap sync test
```

**Expected Output:**
```
🔍 Testing GitHub connection...
✅ Successfully connected to GitHub
✅ Repository access confirmed: username/repository
✅ Issue creation permissions verified
✅ Milestone access permissions verified
🎉 GitHub integration is working correctly!
```

### 3. Environment Variables (Alternative)

For CI/CD or automated environments:

```bash
# Set environment variables
export ROADMAP_GITHUB_TOKEN="your-token"
export ROADMAP_GITHUB_REPO="username/repository"
export ROADMAP_GITHUB_URL="https://api.github.com"  # Optional

# Test without explicit setup
roadmap sync test
```

## 🏢 Enterprise Environment Setup

### 1. Enterprise GitHub Integration

```bash
# Setup for GitHub Enterprise Server
roadmap sync setup \
  --token "enterprise-token" \
  --repo "organization/project" \
  --github-url "https://github.company.com"

# Test enterprise connection
roadmap sync test --verbose
```

### 2. Proxy Configuration

For environments behind corporate proxies:

```bash
# Set proxy environment variables
export HTTP_PROXY="http://proxy.company.com:8080"
export HTTPS_PROXY="http://proxy.company.com:8080"
export NO_PROXY="localhost,127.0.0.1,.company.com"

# Test connection through proxy
roadmap sync test
```

### 3. SSL Certificate Handling

```bash
# For environments with custom CA certificates
export REQUESTS_CA_BUNDLE="/path/to/company-ca-bundle.pem"

# For development/testing only (not recommended)
roadmap sync setup \
  --token "token" \
  --repo "org/repo" \
  --insecure  # Skips SSL verification
```

## 👥 Team Setup

### 1. Shared Repository Configuration

For teams sharing a single roadmap:

```bash
# Team lead initial setup
roadmap init
roadmap sync setup --token "team-token" --repo "team/project"

# Import existing GitHub issues
roadmap sync pull --high-performance

# Create shared backup
roadmap bulk backup .roadmap/ --destination ./shared-backups/
```

### 2. Individual Developer Setup

For team members joining an existing project:

```bash
# Clone project repository
git clone https://github.com/team/project.git
cd project

# Setup roadmap CLI
roadmap sync setup --token "personal-token" --repo "team/project"

# Sync latest data
roadmap sync pull --high-performance

# Verify setup
roadmap status
```

### 3. CI/CD Integration

**GitHub Actions Example:**

```yaml
# .github/workflows/roadmap-sync.yml
name: Roadmap Sync
on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
  workflow_dispatch:

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install Roadmap CLI
        run: pip install roadmap-cli

      - name: Setup GitHub integration
        env:
          GITHUB_TOKEN: ${{ secrets.ROADMAP_GITHUB_TOKEN }}
        run: |
          roadmap sync setup \
            --token "$GITHUB_TOKEN" \
            --repo "${{ github.repository }}"

      - name: Sync roadmap
        run: roadmap sync pull --high-performance

      - name: Validate roadmap
        run: roadmap bulk validate .roadmap/

      - name: Commit changes
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add .roadmap/
          git diff --staged --quiet || git commit -m "Auto-sync roadmap"
          git push
```

## 🔧 Development Environment Setup

### 1. Poetry Setup (Recommended for Development)

```bash
# Install Poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Clone and setup development environment
git clone https://github.com/yourusername/roadmap.git
cd roadmap

# Install dependencies
poetry install

# Activate virtual environment
poetry shell

# Run in development mode
poetry run roadmap --help
```

### 2. Development Configuration

```bash
# Enable verbose logging
export ROADMAP_LOG_LEVEL=DEBUG

# Use development configuration
export ROADMAP_CONFIG_PATH=./dev-config.yaml

# Enable development features
export ROADMAP_DEV_MODE=true
```

### 3. Testing Setup

```bash
# Run tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=roadmap --cov-report=html

# Run performance tests
poetry run pytest tests/test_performance_sync.py -v

# Run integration tests
poetry run pytest tests/test_integration.py -v
```

## 🐳 Docker Setup

### 1. Using Pre-built Docker Image

```bash
# Pull the official image
docker pull roadmap-cli:latest

# Run with mounted volume
docker run -v $(pwd):/workspace roadmap-cli:latest init

# Run with environment variables
docker run \
  -e ROADMAP_GITHUB_TOKEN="your-token" \
  -e ROADMAP_GITHUB_REPO="user/repo" \
  -v $(pwd):/workspace \
  roadmap-cli:latest sync pull
```

### 2. Building Custom Docker Image

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install roadmap CLI
RUN pip install roadmap-cli

# Set working directory for roadmap files
WORKDIR /workspace

# Default command
CMD ["roadmap", "--help"]
```

```bash
# Build and run
docker build -t my-roadmap-cli .
docker run -v $(pwd):/workspace my-roadmap-cli init
```

## 🔍 Troubleshooting Installation

### Common Issues and Solutions

#### 1. Python Version Issues

```bash
# Check Python version
python --version
python3 --version

# If using old Python version
# Option 1: Use pyenv to install Python 3.12
curl https://pyenv.run | bash
pyenv install 3.12.0
pyenv global 3.12.0

# Option 2: Use conda
conda create -n roadmap python=3.12
conda activate roadmap
pip install roadmap-cli
```

#### 2. Permission Issues

```bash
# If getting permission errors
# Option 1: Install with --user flag
pip install --user roadmap-cli

# Option 2: Use virtual environment
python -m venv roadmap-env
source roadmap-env/bin/activate  # On Windows: roadmap-env\Scripts\activate
pip install roadmap-cli
```

#### 3. Network/Proxy Issues

```bash
# Configure pip for proxy
pip install --proxy http://proxy.company.com:8080 roadmap-cli

# Or set environment variables
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080
pip install roadmap-cli
```

#### 4. GitHub Connection Issues

```bash
# Test GitHub connectivity
curl -H "Authorization: token your-token" https://api.github.com/user

# Check repository access
curl -H "Authorization: token your-token" \
     https://api.github.com/repos/username/repository

# Verify token permissions
roadmap sync test --verbose
```

### Performance Optimization

#### 1. Large Repository Setup

For repositories with 1000+ issues:

```bash
# Optimize performance settings
roadmap sync pull --high-performance \
  --workers 16 \           # Increase workers
  --batch-size 200         # Larger batches

# Enable caching
export ROADMAP_CACHE_TTL=600  # 10 minutes

# Use SSD storage for .roadmap directory
```

#### 2. Memory Optimization

For memory-constrained environments:

```bash
# Reduce memory usage
roadmap sync pull --high-performance \
  --workers 2 \            # Fewer workers
  --batch-size 10          # Smaller batches

# Process in chunks
roadmap sync pull --issues    # Issues only first
roadmap sync pull --milestones  # Then milestones
```

## 🎯 Best Practices

### 1. Security Best Practices

```bash
# Use environment variables for tokens
echo 'export ROADMAP_GITHUB_TOKEN="your-token"' >> ~/.bashrc
source ~/.bashrc

# Set restrictive permissions on config files
chmod 600 .roadmap/config.yaml

# Regularly rotate GitHub tokens
roadmap sync delete-token
roadmap sync setup --token "new-token" --repo "user/repo"
```

### 2. Backup Best Practices

```bash
# Set up automated backups
# Add to crontab (crontab -e):
0 6 * * * cd /path/to/project && roadmap bulk backup .roadmap/

# Configure backup retention
find .roadmap/.backups -type d -mtime +30 -exec rm -rf {} \;
```

### 3. Team Collaboration Best Practices

```bash
# Establish team conventions
roadmap issue create "Team: Use consistent labeling" \
  --labels team,process,documentation

# Set up shared configuration
cat > .roadmap/team-config.yaml << EOF
teams:
  backend:
    default_labels: [backend, api]
    members: [alice, bob]
  frontend:
    default_labels: [frontend, ui]
    members: [charlie, diana]
EOF
```

## 📚 Next Steps

After successful installation and setup:

1. **Read the User Workflows Guide**: [USER_WORKFLOWS.md](USER_WORKFLOWS.md)
2. **Explore CLI Commands**: [CLI_REFERENCE.md](CLI_REFERENCE.md)
3. **Review Feature Showcase**: [FEATURE_SHOWCASE.md](FEATURE_SHOWCASE.md)
4. **Check Performance Guide**: [PERFORMANCE_OPTIMIZATION.md](PERFORMANCE_OPTIMIZATION.md)

## 🆘 Getting Help

- **Documentation**: Check the complete documentation suite
- **GitHub Issues**: Report bugs and request features
- **Community**: Join discussions and get help from other users
- **Support**: Contact maintainers for enterprise support

---

**Quick Start Summary:**
```bash
# 1. Install
pip install roadmap-cli

# 2. Initialize
roadmap init

# 3. Setup GitHub (optional)
roadmap sync setup --token "your-token" --repo "user/repo"

# 4. Start using
roadmap issue create "My first issue"
roadmap milestone create "v1.0"
roadmap sync pull --high-performance
```
