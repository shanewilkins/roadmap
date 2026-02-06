# GitHub Token Setup for Roadmap CLI

The roadmap CLI uses GitHub's API for syncing issues with GitHub repositories. A Personal Access Token is required for authentication.

## Steps to Create a Personal Access Token (Classic)

1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Give it a name like "roadmap-cli-dev"
4. Set expiration (90 days recommended for testing)
5. Select required scopes:
   - ✅ `repo` (full control of private/public repositories) - **REQUIRED**
   - ✅ `workflow` (optional, for GitHub Actions workflows)
6. Click "Generate token"
7. **Copy the token immediately** (you won't see it again!)

## Setting the Token in Your Environment

### Option 1: Add to Your Shell Profile (Permanent)

Add to `~/.zshrc`, `~/.bashrc`, or `~/.bash_profile`:

```bash
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

Then reload your shell:
```bash
source ~/.zshrc
```

### Option 2: Set for Current Session Only (Temporary)

```bash
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

## Verify Setup

```bash
echo $GITHUB_TOKEN
# Should show: ghp_xxxxx... (first 7 chars visible)
```

## Token Scopes Reference

- **`repo`** - Full control of public and private repositories
  - Use this for private repositories or when full access needed
  - **RECOMMENDED** for roadmap CLI
  
- **`public_repo`** - Access to public repositories only
  - Use this if you only sync with public GitHub repositories
  - More restrictive, better for public use

## Troubleshooting

### "GitHub token not configured" Error

**Problem**: You see `GitHub token not configured` when running sync

**Solution**: 
1. Verify token is set: `echo $GITHUB_TOKEN`
2. If empty, export it: `export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"`
3. Try sync again: `roadmap sync github`

### "401 Unauthorized" Error

**Problem**: You see `401 Unauthorized` when syncing

**Causes**:
- Token has expired
- Token was revoked
- Token doesn't have required scopes

**Solution**:
1. Go to https://github.com/settings/tokens
2. Check token expiration and scopes
3. Create a new token if needed
4. Update `GITHUB_TOKEN` environment variable

### "403 Forbidden" Error  

**Problem**: You see `403 Forbidden` when syncing

**Causes**:
- Token doesn't have permission for the repository
- Repository is private and token scope is `public_repo`

**Solution**:
1. Verify token has `repo` scope (not just `public_repo`)
2. Verify token has access to the repository
3. Create new token if needed with correct scopes

## Security Best Practices

1. **Never commit tokens to git** - Add to `.gitignore` if storing in config files
2. **Use environment variables** - Most secure for CI/CD and development
3. **Rotate tokens regularly** - Expire tokens after 30-90 days
4. **Use minimal scopes** - Only select scopes you actually need
5. **Revoke old tokens** - https://github.com/settings/tokens

## For CI/CD Environments

In GitHub Actions or other CI systems, use repository secrets:

1. Go to `Settings → Secrets and variables → Actions`
2. Click "New repository secret"
3. Name: `GITHUB_TOKEN` (or custom name)
4. Value: Paste your personal access token
5. Use in workflow:
   ```yaml
   env:
     GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
   ```

For other CI systems (GitLab, Jenkins, etc), follow their documentation for storing secrets securely.
