# Roadmap CLI Troubleshooting Guide

Comprehensive troubleshooting guide for common issues, error messages, and solutions when using the Roadmap CLI tool.

## 🚨 Quick Diagnosis

### Health Check Commands

Run these commands to quickly identify issues:

```bash

# 1. Check basic functionality

roadmap --version
roadmap status

# 2. Validate your roadmap files

roadmap bulk validate .roadmap/

# 3. Test GitHub connectivity (if configured)

roadmap sync test

# 4. Generate comprehensive health report

roadmap bulk health-report .roadmap/

```text

## 📁 YAML Validation Errors

### Common YAML Syntax Issues

#### 1. Invalid YAML Syntax

**Error Message:**

```text
❌ .roadmap/issues/broken-issue.yaml - Invalid YAML syntax at line 5

```text

**Common Causes and Solutions:**

```yaml

# ❌ Wrong: Inconsistent indentation

---
title: "Fix authentication bug"
priority: high
  status: todo    # Incorrect indentation

# ✅ Correct: Consistent indentation

---
title: "Fix authentication bug"
priority: high
status: todo

```text

```yaml

# ❌ Wrong: Missing quotes for special characters

title: Fix: Authentication & Authorization

# ✅ Correct: Quoted strings with special characters

title: "Fix: Authentication & Authorization"

```text

```yaml

# ❌ Wrong: Unescaped colons in strings

description: Time: 2 hours

# ✅ Correct: Quoted strings with colons

description: "Time: 2 hours"

```text

**Solution Steps:**

```bash

# 1. Identify the problematic file

roadmap bulk validate .roadmap/ | grep ERROR

# 2. Check specific file

cat .roadmap/issues/broken-issue.yaml

# 3. Restore from backup if needed

ls .roadmap/.backups/
cp .roadmap/.backups/issues_latest/broken-issue.yaml .roadmap/issues/

# 4. Validate fix

roadmap bulk validate .roadmap/

```text

#### 2. Schema Validation Errors

**Error Message:**

```text
❌ Issue validation failed: priority must be one of [critical, high, medium, low]

```text

**Common Invalid Values:**

```yaml

# ❌ Wrong: Invalid priority values

priority: urgent     # Should be: critical, high, medium, low

priority: super-high # Should be: critical, high, medium, low

# ❌ Wrong: Invalid status values

status: complete     # Should be: todo, in-progress, review, done

status: working      # Should be: todo, in-progress, review, done

# ❌ Wrong: Invalid date format

due_date: 12/31/2024 # Should be: 2024-12-31

created: yesterday   # Should be: 2024-10-10T10:30:00Z

```text

**Solutions:**

```bash

# Check valid enum values

roadmap issue create --help  # Shows valid options

# Fix common priority issues

roadmap bulk update-field .roadmap/ \
  --field priority \
  --old-value "urgent" \
  --new-value "critical"

# Fix common status issues

roadmap bulk update-field .roadmap/ \
  --field status \
  --old-value "complete" \
  --new-value "done"

```text

#### 3. Missing Required Fields

**Error Message:**

```text
❌ Issue validation failed: field 'title' is required

```text

**Solution:**

```bash

# Find issues with missing fields

roadmap bulk validate .roadmap/ --detailed

# Example fix for missing title

roadmap issue update "issue-id" --title "Descriptive title"

```text

### Recovery from Corrupted Files

#### Automatic Recovery

```bash

# 1. Identify corruption

roadmap bulk validate .roadmap/
❌ Multiple validation errors found

# 2. Check available backups

ls .roadmap/.backups/ -la
drwxr-xr-x  issues_20241010_143022/
drwxr-xr-x  issues_20241010_120515/
drwxr-xr-x  milestones_20241010_143022/

# 3. Restore from most recent backup

cp .roadmap/.backups/issues_20241010_143022/*.yaml .roadmap/issues/

# 4. Verify restoration

roadmap bulk validate .roadmap/
✅ All files validated successfully

```text

#### Manual Recovery

```bash

# If backups are unavailable, recreate from GitHub

roadmap sync pull --high-performance --force-overwrite

# Or recreate specific issues

roadmap issue create "Recreated issue" \
  --priority high \
  --status todo \
  --milestone "v1.0"

```text

## 🔄 GitHub Sync Issues

### Authentication Problems

#### 1. Invalid or Expired Token

**Error Messages:**

```text
❌ GitHub authentication failed: Bad credentials
❌ Token has expired
❌ API rate limit exceeded

```text

**Solutions:**

```bash

# 1. Generate new token

# Visit: https://github.com/settings/tokens

# Generate new token with repo permissions

# 2. Update token

roadmap sync delete-token
roadmap sync setup --token "new-token" --repo "user/repo"

# 3. Test new token

roadmap sync test

```text

#### 2. Insufficient Permissions

**Error Message:**

```text
❌ GitHub API error: Not Found (repository may be private or you lack permissions)

```text

**Required Token Permissions:**

```text
✅ repo (for private repositories)
✅ public_repo (for public repositories)
✅ write:issues (to create and update issues)
✅ read:org (for organization repositories)

```text

**Solution:**

```bash

# 1. Check current token permissions

curl -H "Authorization: token your-token" \
     https://api.github.com/user

# 2. Verify repository access

curl -H "Authorization: token your-token" \
     https://api.github.com/repos/username/repository

# 3. Recreate token with correct permissions

roadmap sync setup --token "token-with-permissions" --repo "user/repo"

```text

#### 3. Repository Not Found

**Error Message:**

```text
❌ Repository 'username/repo' not found or not accessible

```text

**Solutions:**

```bash

# 1. Verify repository exists

curl https://api.github.com/repos/username/repository

# 2. Check repository name format

roadmap sync setup --token "token" --repo "correct-username/correct-repo"

# 3. For organization repositories

roadmap sync setup --token "token" --repo "organization/repository"

```text

### Network and Connectivity Issues

#### 1. Proxy Configuration

**Error Message:**

```text
❌ Connection failed: Unable to reach GitHub API

```text

**Solutions:**

```bash

# 1. Configure proxy environment variables

export HTTP_PROXY="http://proxy.company.com:8080"
export HTTPS_PROXY="http://proxy.company.com:8080"
export NO_PROXY="localhost,127.0.0.1"

# 2. Test connectivity

roadmap sync test --verbose

# 3. For authentication-required proxies

export HTTP_PROXY="http://username:password@proxy.company.com:8080"

```text

#### 2. SSL Certificate Issues

**Error Messages:**

```text
❌ SSL certificate verification failed
❌ CERTIFICATE_VERIFY_FAILED

```text

**Solutions:**

```bash

# 1. For corporate environments with custom CA

export REQUESTS_CA_BUNDLE="/path/to/company-ca-bundle.pem"

# 2. For development only (not recommended for production)

roadmap sync setup --token "token" --repo "user/repo" --insecure

# 3. Update certificates

# On macOS:

brew install ca-certificates

# On Ubuntu:

sudo apt-get update && sudo apt-get install ca-certificates

```text

#### 3. Rate Limiting

**Error Message:**

```text
❌ GitHub API rate limit exceeded (5000 requests/hour)

```text

**Solutions:**

```bash

# 1. Check current rate limit status

curl -H "Authorization: token your-token" \
     https://api.github.com/rate_limit

# 2. Use high-performance sync to reduce API calls

roadmap sync pull --high-performance  # Uses only 2 API calls vs 100+

# 3. Wait for rate limit reset or use different token

roadmap sync status  # Shows rate limit info

```text

### Sync Data Conflicts

#### 1. GitHub Timestamp Race Condition

**Symptoms:**

```text
Local changes appear to sync to GitHub but then get overridden
Issues marked as "done" locally don't stay closed on GitHub after sync

```text

**Root Cause:**
When using `newer_wins` strategy, GitHub updates its `updated_at` timestamp after receiving your push, making it appear "newer" than your local changes during the same bidirectional sync operation.

**Solutions:**

```bash

# 1. Use local_wins strategy (recommended default)

roadmap sync bidirectional --strategy local_wins

# 2. Change default strategy in configuration

roadmap config set sync.default_strategy "local_wins"

# 3. For timestamp-based resolution with multiple collaborators

roadmap sync bidirectional --strategy newer_wins  # Understand race condition risk

```text

#### 2. Merge Conflicts

**Error Message:**

```text
⚠️  Conflict detected: Local issue modified, GitHub issue also changed

```text

**Resolution:**

```bash

# 1. Review conflicts

roadmap sync status --conflicts

# 2. Choose resolution strategy

roadmap sync pull --strategy local      # Keep local changes

roadmap sync pull --strategy remote     # Use GitHub version

roadmap sync pull --strategy interactive # Manually resolve each conflict

# 3. Manual conflict resolution

roadmap issue update "conflicted-issue" \
  --title "Manually merged title" \
  --priority high

```text

#### 2. Duplicate Issues

**Error Message:**

```text
⚠️  Duplicate issue detected: "Fix login bug" exists both locally and on GitHub

```text

**Solutions:**

```bash

# 1. List duplicates

roadmap sync status --duplicates

# 2. Merge duplicates

roadmap issue delete "local-duplicate-title"
roadmap sync pull  # Pull GitHub version

# 3. Or keep local and update GitHub

roadmap sync push --force-update

```text

## 🔒 File Locking Issues

### Lock Acquisition Problems

#### 1. Stale Locks

**Error Message:**

```text
❌ Unable to acquire lock: file.yaml is locked by process 12345 (not found)

```text

**Solutions:**

```bash

# 1. Check active locks

roadmap debug locks list

# 2. Clear stale locks

roadmap debug locks clear --stale

# 3. Force clear specific lock (use carefully)

roadmap debug locks clear --file issue.yaml --force

```text

#### 2. Permission Issues

**Error Message:**

```text
❌ Permission denied: Cannot create lock file

```text

**Solutions:**

```bash

# 1. Check file permissions

ls -la .roadmap/issues/

# 2. Fix permissions

chmod 755 .roadmap/
chmod 644 .roadmap/issues/*.yaml

# 3. Check directory ownership

sudo chown -R $(whoami) .roadmap/

```text

#### 3. Concurrent Access Deadlocks

**Error Message:**

```text
❌ Deadlock detected: Circular lock dependency

```text

**Solutions:**

```bash

# 1. Clear all locks (safe - locks auto-recreate)

roadmap debug locks clear --all

# 2. Restart operations in sequence

roadmap issue update "issue1" --status done
roadmap issue update "issue2" --priority high

# 3. Use bulk operations to avoid conflicts

roadmap bulk update-field .roadmap/ \
  --field status \
  --old-value "todo" \
  --new-value "in-progress"

```text

## ⚡ Performance Issues

### Slow Sync Operations

#### 1. Large Repository Performance

**Symptoms:**

```text
🐌 Sync taking longer than 30 seconds for 100+ issues

```text

**Solutions:**

```bash

# 1. Enable high-performance mode

roadmap sync pull --high-performance

# 2. Optimize worker count for your system

roadmap sync pull --high-performance --workers $(nproc)

# 3. Adjust batch size

roadmap sync pull --high-performance --batch-size 200

# 4. Monitor performance

roadmap sync pull --high-performance  # Shows performance report

```text

#### 2. Memory Usage Issues

**Symptoms:**

```text
Process killed due to out of memory

```text

**Solutions:**

```bash

# 1. Reduce memory usage

roadmap sync pull --high-performance \
  --workers 2 \            # Fewer workers

  --batch-size 10          # Smaller batches

# 2. Process in chunks

roadmap sync pull --issues      # Issues first

roadmap sync pull --milestones  # Then milestones

# 3. Check available memory

free -h  # Linux

vm_stat  # macOS

```text

#### 3. Disk Space Issues

**Error Message:**

```text
❌ No space left on device

```text

**Solutions:**

```bash

# 1. Check disk usage

df -h
du -sh .roadmap/

# 2. Clean old backups

find .roadmap/.backups -type d -mtime +30 -exec rm -rf {} \;

# 3. Compress large files

roadmap bulk backup .roadmap/ --compress

```text

### Cache Issues

#### 1. Stale Cache Data

**Symptoms:**

```text
Sync shows outdated data despite recent GitHub changes

```text

**Solutions:**

```bash

# 1. Clear cache manually

roadmap cache clear

# 2. Force refresh

roadmap sync pull --no-cache

# 3. Adjust cache TTL

export ROADMAP_CACHE_TTL=60  # 1 minute instead of 5

```text

#### 2. Cache Corruption

**Error Message:**

```text
❌ Cache validation failed: corrupted cache file

```text

**Solutions:**

```bash

# 1. Clear corrupted cache

roadmap cache clear --force

# 2. Rebuild cache

roadmap sync pull --high-performance

# 3. Disable cache temporarily

roadmap sync pull --no-cache

```text

## 🔧 Installation and Environment Issues

### Python Environment Problems

#### 1. Version Compatibility

**Error Message:**

```text
❌ Python 3.7 is not supported. Please upgrade to Python 3.8+

```text

**Solutions:**

```bash

# 1. Check Python version

python --version
python3 --version

# 2. Install newer Python with pyenv

curl https://pyenv.run | bash
pyenv install 3.12.0
pyenv global 3.12.0

# 3. Use conda environment

conda create -n roadmap python=3.12
conda activate roadmap
pip install roadmap-cli

```text

#### 2. Dependency Conflicts

**Error Message:**

```text
❌ Package conflicts detected: pydantic requires different version

```text

**Solutions:**

```bash

# 1. Use virtual environment

python -m venv roadmap-env
source roadmap-env/bin/activate
pip install roadmap-cli

# 2. Use pipx for isolated installation

pipx install roadmap-cli

# 3. Force reinstall with dependencies

pip install --force-reinstall roadmap-cli

```text

#### 3. Permission Issues

**Error Message:**

```text
❌ Permission denied: Cannot install package

```text

**Solutions:**

```bash

# 1. Install for user only

pip install --user roadmap-cli

# 2. Use virtual environment

python -m venv roadmap-env
source roadmap-env/bin/activate
pip install roadmap-cli

# 3. Fix pip permissions (macOS)

sudo chown -R $(whoami) $(python -m site --user-base)

```text

### Configuration Issues

#### 1. Config File Corruption

**Error Message:**

```text
❌ Invalid configuration file: .roadmap/config.yaml

```text

**Solutions:**

```bash

# 1. Validate config file

roadmap config validate

# 2. Restore default config

roadmap config reset

# 3. Recreate from template

roadmap init --force  # Overwrites existing config

```text

#### 2. Environment Variable Conflicts

**Symptoms:**

```text
Commands behave unexpectedly with custom environment variables

```text

**Solutions:**

```bash

# 1. Check environment variables

env | grep ROADMAP

# 2. Clear conflicting variables

unset ROADMAP_GITHUB_TOKEN
unset ROADMAP_GITHUB_REPO

# 3. Use explicit configuration

roadmap --config /path/to/config.yaml sync pull

```text

## 🔍 Debugging and Diagnostics

### Debug Mode

```bash

# Enable verbose logging

export ROADMAP_LOG_LEVEL=DEBUG
roadmap --debug sync pull

# Save debug output

roadmap --debug sync pull > debug.log 2>&1

# Analyze debug output

grep ERROR debug.log
grep WARNING debug.log

```text

### System Information

```bash

# Collect system information for bug reports

roadmap debug system-info

# Output example:

System Information:
├── OS: macOS 14.0
├── Python: 3.12.0
├── Roadmap CLI: 2.0.0
├── Dependencies: pydantic 2.4.0, click 8.1.0
├── Config: .roadmap/config.yaml (valid)
└── GitHub: Connected (username/repo)

```text

### Performance Profiling

```bash

# Profile sync operations

roadmap sync pull --profile

# Profile output location

cat .roadmap/.profiles/sync_20241010_154530.prof

# Analyze bottlenecks

roadmap debug analyze-profile .roadmap/.profiles/sync_20241010_154530.prof

```text

## 📞 Getting Help

### Self-Help Resources

1. **Documentation**: Complete documentation suite
2. **Health Check**: `roadmap bulk health-report .roadmap/`
3. **Debug Info**: `roadmap debug system-info`
4. **Logs**: Enable debug mode for detailed output

### Community Support

1. **GitHub Issues**: Report bugs with debug information
2. **Discussions**: Ask questions and share solutions
3. **Discord/Slack**: Real-time community help
4. **Stack Overflow**: Tag questions with 'roadmap-cli'

### Bug Report Template

When reporting issues, include:

```bash

# 1. System information

roadmap debug system-info

# 2. Configuration (redacted)

cat .roadmap/config.yaml | sed 's/token:.*/token: [REDACTED]/'

# 3. Error reproduction

roadmap --debug command-that-fails > error.log 2>&1

# 4. Health report

roadmap bulk health-report .roadmap/

# 5. Environment

env | grep ROADMAP

```text

## ✅ Prevention Best Practices

### Regular Maintenance

```bash

# Daily health check

roadmap bulk validate .roadmap/

# Weekly backup

roadmap bulk backup .roadmap/

# Monthly cleanup

find .roadmap/.backups -mtime +30 -delete
roadmap cache clear

```text

### Monitoring Scripts

```bash
#!/bin/bash

# roadmap-health-check.sh

echo "🔍 Roadmap Health Check - $(date)"

# Check validation

if ! roadmap bulk validate .roadmap/ > /dev/null 2>&1; then
    echo "❌ Validation failed"
    roadmap bulk validate .roadmap/
    exit 1
fi

# Check GitHub connectivity

if ! roadmap sync test > /dev/null 2>&1; then
    echo "⚠️  GitHub connectivity issue"
    roadmap sync test
fi

# Check disk space

if [ $(df .roadmap/ | tail -1 | awk '{print $5}' | sed 's/%//') -gt 90 ]; then
    echo "⚠️  Disk space low"
fi

echo "✅ All systems healthy"

```text

---

**Quick troubleshooting checklist:**
- ✅ Run `roadmap bulk validate .roadmap/`
- ✅ Check `roadmap sync test` if using GitHub
- ✅ Review `roadmap bulk health-report .roadmap/`
- ✅ Enable debug mode: `roadmap --debug command`
- ✅ Check for recent backups in `.roadmap/.backups/`
