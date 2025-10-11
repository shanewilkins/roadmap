# Secure Credential Management

The roadmap CLI now includes comprehensive security improvements for handling GitHub authentication tokens.

## 🔒 Security Features Implemented

### 1. **Multi-Platform Credential Storage**
- **macOS**: Keychain Services integration
- **Windows**: Windows Credential Manager
- **Linux**: Secret Service API (GNOME Keyring, KDE Wallet)
- **Fallback**: Environment variables for unsupported systems

### 2. **Token Source Priority**

The system follows a secure priority order for token resolution:

1. **Environment Variable** (`GITHUB_TOKEN`) - Highest priority, recommended for CI/CD
2. **System Credential Manager** - Secure storage, default for interactive use
3. **Configuration File** - Legacy fallback (strongly discouraged, requires `--insecure` flag)

### 3. **Enhanced CLI Commands**

#### Secure Setup (Recommended)

```bash
# Store token securely in system credential manager (default behavior)
roadmap sync setup --token ghp_xxx --repo owner/repo

# Environment variable method (recommended for CI/CD)
export GITHUB_TOKEN="ghp_xxx"
roadmap sync setup --repo owner/repo
```

#### Legacy Setup (Discouraged)

```bash
# Store in config file (requires explicit --insecure flag with warnings)
roadmap sync setup --token ghp_xxx --repo owner/repo --insecure
```

#### Status and Information
```bash
# View comprehensive credential status
roadmap sync status

# Shows:
# - Connection status
# - Available credential sources
# - Active token source
# - Masked token display
# - Repository configuration
```

#### Token Management
```bash
# Delete stored token from credential manager
roadmap sync delete-token

# Test authentication
roadmap sync test
```

## 🛡️ Security Improvements

### **Before (Security Issues)**
❌ Plain text token storage in config files  
❌ Risk of accidentally committing tokens to git  
❌ No token masking in output  
❌ Single storage method  

### **After (Secure Implementation)**
✅ Encrypted storage in OS credential managers  
✅ Environment variable priority  
✅ Token masking in all output  
✅ Multiple secure storage options  
✅ Clear security warnings for legacy methods  
✅ Comprehensive credential status reporting  

## 📖 Usage Examples

### Initial Setup with Secure Storage
```bash
# Initialize roadmap
roadmap init

# Setup GitHub integration with secure token storage
roadmap sync setup --token ghp_your_token_here --repo username/repository --secure
```

### Check Credential Status
```bash
roadmap sync status
```

**Output:**
```
GitHub Integration Status
──────────────────────────────
✅ Connection: Connected as username to username/repository

Token Sources:
  ✅ Credential Manager: Available
  ❌ Environment Variable (GITHUB_TOKEN): Not set
  ❌ Config File: Not stored

Active Source: Credential Manager
Token: ****here

Repository: username/repository
```

### Environment Variable Method (Recommended for CI/CD)
```bash
# Set environment variable
export GITHUB_TOKEN="ghp_your_token_here"

# Setup repository only
roadmap sync setup --repo username/repository

# Status will show environment variable as active source
roadmap sync status
```

## 🔧 Technical Implementation

### Cross-Platform Support
- **macOS**: Uses `security` command-line tool for Keychain access
- **Windows**: Uses `keyring` library with Windows Credential Manager
- **Linux**: Uses `keyring` library with Secret Service API
- **Fallback**: Graceful degradation to environment variables

### Error Handling
- Silent fallback when credential managers are unavailable
- Non-blocking credential retrieval
- Clear error messages for setup issues
- Comprehensive validation and testing

### Token Security
- Tokens are masked in all CLI output (`****abcd`)
- No token logging or debugging output
- Secure credential manager APIs only
- Optional keyring dependency for enhanced security

## 📦 **Installation**

```bash
# Standard installation (includes secure credential management)
pip install roadmap
```

**Note**: The `keyring` library is now included by default, providing secure credential storage on all platforms.

## 🔍 Migration Guide

### Existing Users
If you have tokens stored in config files, the system will continue to work but will show security warnings:

```bash
roadmap sync status
```
```
⚠️ Token stored in config file. Consider using --secure flag for better security.
```

### Recommended Migration
1. Note your current repository configuration
2. Delete token from config file or use new secure storage:
   ```bash
   roadmap sync setup --token your_token --repo owner/repo --secure
   ```
3. Verify secure storage:
   ```bash
   roadmap sync status
   ```

## 🧪 Testing

The credential management system includes comprehensive tests:
- 32 credential manager tests
- Cross-platform compatibility tests
- Error handling and fallback tests
- Integration tests with CLI commands
- Security validation tests

```bash
poetry run pytest tests/test_credentials.py -v
```

## 🔐 Security Best Practices

1. **Use Environment Variables for CI/CD**: Set `GITHUB_TOKEN` in your CI environment
2. **Enable Secure Storage for Development**: Use `--secure` flag for local development
3. **Regular Token Rotation**: Periodically rotate your GitHub tokens
4. **Scope Limitations**: Use minimal token scopes (`repo` or `public_repo`)
5. **Monitor Token Usage**: Check GitHub's token usage monitoring

## 📋 Requirements

- **GitHub Token Scopes**: `repo` (private repos) or `public_repo` (public repos)
- **Optional Dependencies**: `keyring` library for enhanced Windows/Linux support
- **System Requirements**: 
  - macOS: Built-in Keychain Services
  - Windows: Windows Credential Manager
  - Linux: GNOME Keyring or KDE Wallet

## 🐛 Troubleshooting

### Credential Manager Not Available
```bash
roadmap sync status
```
If credential manager shows as unavailable:
- **Linux**: Install `gnome-keyring` or `kde-wallet`
- **Windows**: Install with `pip install roadmap[secure]`
- **Fallback**: Use environment variables

### Token Not Found
```bash
roadmap sync delete-token  # Clear any stored tokens
export GITHUB_TOKEN="your_token"  # Set environment variable
roadmap sync test  # Verify connection
```

This secure credential management system ensures that your GitHub tokens are stored and handled securely across all supported platforms while maintaining backward compatibility with existing workflows.