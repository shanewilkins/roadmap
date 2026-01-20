# Submitting roadmap-cli to Official Homebrew

This guide walks through submitting the `roadmap-cli` formula to [homebrew-core](https://github.com/Homebrew/homebrew-core).

## Prerequisites

1. GitHub account
2. Homebrew installed locally
3. Git set up with your GitHub credentials

## Step 1: Fork Homebrew-Core

Fork the [Homebrew/homebrew-core](https://github.com/Homebrew/homebrew-core) repository to your GitHub account.

## Step 2: Clone Your Fork

```bash
git clone https://github.com/YOUR_USERNAME/homebrew-core.git
cd homebrew-core
```

## Step 3: Create a Branch

```bash
git checkout -b add-roadmap-cli
```

## Step 4: Add the Formula

Copy the formula to the correct location:

```bash
cp ../roadmap/scripts/roadmap-cli.rb ./Formula/roadmap-cli.rb
```

Verify the formula location:
```bash
ls -la Formula/roadmap-cli.rb
```

## Step 5: Test Locally

```bash
# Test the formula
brew install --verbose --build-from-source ./Formula/roadmap-cli.rb

# Verify it works
roadmap --version

# Run Homebrew tests
brew test roadmap-cli

# Check for lint issues
brew audit --new-formula ./Formula/roadmap-cli.rb
```

## Step 6: Commit and Push

```bash
git add Formula/roadmap-cli.rb
git commit -m "Add roadmap-cli formula

- CLI tool for project roadmap management
- GitHub integration and data visualization
- Supports Python 3.11+"

git push origin add-roadmap-cli
```

## Step 7: Create Pull Request

1. Go to https://github.com/Homebrew/homebrew-core
2. Click "New Pull Request"
3. Select your fork and `add-roadmap-cli` branch
4. Title: "Add roadmap-cli formula"
5. Description:
   ```
   - Adds roadmap-cli formula for macOS installation
   - Package: https://pypi.org/project/roadmap-cli/
   - Version: 1.0.0
   - License: MIT
   - Supports Python 3.11+

   Closes #XXXXX (leave blank if no issue)
   ```

## Step 8: Respond to Review

Homebrew maintainers may request changes:

- Update the formula as needed
- Run tests locally again
- Push updates to the same branch
- The PR will auto-update

## Common Review Comments

**Formula class name:** Should match `snake_case` of the package name
- ✅ `RoadmapCli` (for `roadmap-cli`)

**URL:** Should point to stable PyPI releases
- ✅ `https://files.pythonhosted.org/packages/source/r/roadmap_cli/roadmap_cli-1.0.0.tar.gz`

**SHA256:** Must match actual release hash
- ✅ `1526652af159fce98b68fb45aa9eb2f48f52fdc174e26afdfbec36f8091eeab3`

**Dependencies:** Should use oldest supported version
- ✅ `depends_on "python@3.11"` (we support 3.10+, using 3.11 for stability)

**Test block:** Should verify core functionality
- ✅ `system bin/"roadmap", "--version"`

## After Approval

Once the PR is merged:

```bash
# Homebrew maintainers will update the formula for new releases
# Just push version updates and new SHA256 to your repository

# Users can install with:
brew install roadmap-cli

# Update with:
brew upgrade roadmap-cli
```

## Troubleshooting

**Formula lint failures:**
```bash
brew doctor
brew audit --new-formula ./Formula/roadmap-cli.rb --verbose
```

**Installation fails locally:**
```bash
brew install --verbose ./Formula/roadmap-cli.rb
# Check output for specific errors
```

**SHA256 mismatch:**
```bash
# Recalculate from the built package
python3 -c "import hashlib; print(hashlib.sha256(open('dist/roadmap_cli-1.0.0.tar.gz', 'rb').read()).hexdigest())"
```

**Python version issues:**
- Homebrew prefers long-term stable Python versions
- `python@3.11` is a good choice (released Oct 2022, EOL Oct 2027)

## Resources

- [Homebrew Formula Cookbook](https://docs.brew.sh/Formula-Cookbook)
- [Python Formula Guidelines](https://docs.brew.sh/Python-for-formula-authors)
- [Contributing to Homebrew](https://docs.brew.sh/How-To-Open-a-Homebrew-Pull-Request)

## Timeline

- **Submission:** Immediately after this guide
- **Initial Review:** 24-48 hours
- **Revisions:** 1-3 rounds (if needed)
- **Approval:** ~1 week (varies)
- **Public Availability:** Immediately after merge
