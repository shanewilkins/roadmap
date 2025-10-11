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
```

## 📁 YAML Validation Errors

### Common YAML Syntax Issues

#### 1. Invalid YAML Syntax

**Error Message:**
```
❌ .roadmap/issues/broken-issue.yaml - Invalid YAML syntax at line 5
```

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
```

```yaml
# ❌ Wrong: Missing quotes for special characters
title: Fix: Authentication & Authorization

# ✅ Correct: Quoted strings with special characters
title: "Fix: Authentication & Authorization"
```

```yaml
# ❌ Wrong: Unescaped colons in strings
description: Time: 2 hours

# ✅ Correct: Quoted strings with colons
description: "Time: 2 hours"
```

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
```

#### 2. Schema Validation Errors

**Error Message:**
```
❌ Issue validation failed: priority must be one of [critical, high, medium, low]
```

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
```

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
```

#### 3. Missing Required Fields

**Error Message:**
```
❌ Issue validation failed: field 'title' is required
```

**Solution:**
```bash
# Find issues with missing fields
roadmap bulk validate .roadmap/ --detailed

# Example fix for missing title
roadmap issue update "issue-id" --title "Descriptive title"
```

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
```

#### Manual Recovery

```bash
# If backups are unavailable, recreate from GitHub
roadmap sync pull --high-performance --force-overwrite

# Or recreate specific issues
roadmap issue create "Recreated issue" \
  --priority high \
  --status todo \
  --milestone "v1.0"
```

## 🔄 GitHub Sync Issues

### Authentication Problems

#### 1. Invalid or Expired Token

**Error Messages:**
```
❌ GitHub authentication failed: Bad credentials
❌ Token has expired
❌ API rate limit exceeded
```

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
```

#### 2. Insufficient Permissions

**Error Message:**
```
❌ GitHub API error: Not Found (repository may be private or you lack permissions)
```

**Required Token Permissions:**
```
✅ repo (for private repositories)
✅ public_repo (for public repositories)  
✅ write:issues (to create and update issues)
✅ read:org (for organization repositories)
```

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
```

#### 3. Repository Not Found

**Error Message:**
```
❌ Repository 'username/repo' not found or not accessible
```

**Solutions:**
```bash
# 1. Verify repository exists
curl https://api.github.com/repos/username/repository

# 2. Check repository name format
roadmap sync setup --token "token" --repo "correct-username/correct-repo"

# 3. For organization repositories
roadmap sync setup --token "token" --repo "organization/repository"
```

### Network and Connectivity Issues

#### 1. Proxy Configuration

**Error Message:**
```
❌ Connection failed: Unable to reach GitHub API
```

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
```

#### 2. SSL Certificate Issues

**Error Messages:**
```
❌ SSL certificate verification failed
❌ CERTIFICATE_VERIFY_FAILED
```

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
```

#### 3. Rate Limiting

**Error Message:**
```
❌ GitHub API rate limit exceeded (5000 requests/hour)
```

**Solutions:**
```bash
# 1. Check current rate limit status
curl -H "Authorization: token your-token" \
     https://api.github.com/rate_limit

# 2. Use high-performance sync to reduce API calls
roadmap sync pull --high-performance  # Uses only 2 API calls vs 100+

# 3. Wait for rate limit reset or use different token
roadmap sync status  # Shows rate limit info
```

### Sync Data Conflicts

#### 1. Merge Conflicts

**Error Message:**
```
⚠️  Conflict detected: Local issue modified, GitHub issue also changed
```

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
```

#### 2. Duplicate Issues

**Error Message:**
```
⚠️  Duplicate issue detected: "Fix login bug" exists both locally and on GitHub
```

**Solutions:**
```bash
# 1. List duplicates
roadmap sync status --duplicates

# 2. Merge duplicates
roadmap issue delete "local-duplicate-title"
roadmap sync pull  # Pull GitHub version

# 3. Or keep local and update GitHub
roadmap sync push --force-update
```

## 🔒 File Locking Issues

### Lock Acquisition Problems

#### 1. Stale Locks

**Error Message:**
```
❌ Unable to acquire lock: file.yaml is locked by process 12345 (not found)
```

**Solutions:**
```bash
# 1. Check active locks
roadmap debug locks list

# 2. Clear stale locks
roadmap debug locks clear --stale

# 3. Force clear specific lock (use carefully)
roadmap debug locks clear --file issue.yaml --force
```

#### 2. Permission Issues

**Error Message:**
```
❌ Permission denied: Cannot create lock file
```

**Solutions:**
```bash
# 1. Check file permissions
ls -la .roadmap/issues/

# 2. Fix permissions
chmod 755 .roadmap/
chmod 644 .roadmap/issues/*.yaml

# 3. Check directory ownership
sudo chown -R $(whoami) .roadmap/
```

#### 3. Concurrent Access Deadlocks

**Error Message:**
```
❌ Deadlock detected: Circular lock dependency
```

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
```

## ⚡ Performance Issues

### Slow Sync Operations

#### 1. Large Repository Performance

**Symptoms:**
```
🐌 Sync taking longer than 30 seconds for 100+ issues
```

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
```

#### 2. Memory Usage Issues

**Symptoms:**
```
Process killed due to out of memory
```

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
```

#### 3. Disk Space Issues

**Error Message:**
```
❌ No space left on device
```

**Solutions:**
```bash
# 1. Check disk usage
df -h
du -sh .roadmap/

# 2. Clean old backups
find .roadmap/.backups -type d -mtime +30 -exec rm -rf {} \;

# 3. Compress large files
roadmap bulk backup .roadmap/ --compress
```

### Cache Issues

#### 1. Stale Cache Data

**Symptoms:**
```
Sync shows outdated data despite recent GitHub changes
```

**Solutions:**
```bash
# 1. Clear cache manually
roadmap cache clear

# 2. Force refresh
roadmap sync pull --no-cache

# 3. Adjust cache TTL
export ROADMAP_CACHE_TTL=60  # 1 minute instead of 5
```

#### 2. Cache Corruption

**Error Message:**
```
❌ Cache validation failed: corrupted cache file
```

**Solutions:**
```bash
# 1. Clear corrupted cache
roadmap cache clear --force

# 2. Rebuild cache
roadmap sync pull --high-performance

# 3. Disable cache temporarily
roadmap sync pull --no-cache
```

## 🔧 Installation and Environment Issues

### Python Environment Problems

#### 1. Version Compatibility

**Error Message:**
```
❌ Python 3.7 is not supported. Please upgrade to Python 3.8+
```

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
```

#### 2. Dependency Conflicts

**Error Message:**
```
❌ Package conflicts detected: pydantic requires different version
```

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
```

#### 3. Permission Issues

**Error Message:**
```
❌ Permission denied: Cannot install package
```

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
```

### Configuration Issues

#### 1. Config File Corruption

**Error Message:**
```
❌ Invalid configuration file: .roadmap/config.yaml
```

**Solutions:**
```bash
# 1. Validate config file
roadmap config validate

# 2. Restore default config
roadmap config reset

# 3. Recreate from template
roadmap init --force  # Overwrites existing config
```

#### 2. Environment Variable Conflicts

**Symptoms:**
```
Commands behave unexpectedly with custom environment variables
```

**Solutions:**
```bash
# 1. Check environment variables
env | grep ROADMAP

# 2. Clear conflicting variables
unset ROADMAP_GITHUB_TOKEN
unset ROADMAP_GITHUB_REPO

# 3. Use explicit configuration
roadmap --config /path/to/config.yaml sync pull
```

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
```

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
```

### Performance Profiling

```bash
# Profile sync operations
roadmap sync pull --profile

# Profile output location
cat .roadmap/.profiles/sync_20241010_154530.prof

# Analyze bottlenecks
roadmap debug analyze-profile .roadmap/.profiles/sync_20241010_154530.prof
```

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
```

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
```

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
```

---

**Quick troubleshooting checklist:**
- ✅ Run `roadmap bulk validate .roadmap/`
- ✅ Check `roadmap sync test` if using GitHub
- ✅ Review `roadmap bulk health-report .roadmap/`
- ✅ Enable debug mode: `roadmap --debug command`
- ✅ Check for recent backups in `.roadmap/.backups/`