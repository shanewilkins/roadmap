#!/bin/bash

# Roadmap CLI - PyPI Publication Script
# This script handles the complete publication process for PyPI

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Validate environment
print_status "Validating environment..."

if ! command_exists poetry; then
    print_error "Poetry not found. Please install Poetry first."
    exit 1
fi

if ! command_exists twine; then
    print_warning "Twine not found. Installing twine..."
    pip install twine
fi

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    print_error "pyproject.toml not found. Are you in the project root?"
    exit 1
fi

# Get current version
CURRENT_VERSION=$(poetry version -s)
print_status "Current version: $CURRENT_VERSION"

# Pre-publication checks
print_status "Running pre-publication checks..."

# 1. Validate package configuration
print_status "Validating package configuration..."
if ! poetry check; then
    print_error "Package configuration validation failed"
    exit 1
fi
print_success "Package configuration is valid"

# 2. Run tests
print_status "Running test suite..."
if ! poetry run pytest --cov=roadmap --cov-report=term-missing -q; then
    print_error "Tests failed"
    exit 1
fi
print_success "All tests passed"

# 3. Clean previous builds
print_status "Cleaning previous builds..."
rm -rf dist/
rm -rf build/
rm -rf *.egg-info/

# 4. Build package
print_status "Building package..."
if ! poetry build; then
    print_error "Package build failed"
    exit 1
fi
print_success "Package built successfully"

# 5. Validate built packages
print_status "Validating built packages..."
if ! twine check dist/*; then
    print_error "Package validation failed"
    exit 1
fi
print_success "Built packages are valid"

# Publication options
echo ""
echo "Publication options:"
echo "1. Test publication (TestPyPI)"
echo "2. Production publication (PyPI)"
echo "3. Both (TestPyPI first, then PyPI)"
echo "4. Exit"
echo ""

read -p "Choose an option (1-4): " choice

case $choice in
    1)
        print_status "Publishing to TestPyPI..."

        # Configure TestPyPI if not already configured
        poetry config repositories.test-pypi https://test.pypi.org/legacy/ 2>/dev/null || true

        # Publish to TestPyPI
        if poetry publish -r test-pypi; then
            print_success "Successfully published to TestPyPI"
            print_status "You can now test the installation with:"
            echo "pip install --index-url https://test.pypi.org/simple/ roadmap-cli==$CURRENT_VERSION"
        else
            print_error "TestPyPI publication failed"
            exit 1
        fi
        ;;

    2)
        print_status "Publishing to PyPI..."
        print_warning "This will publish to the PRODUCTION PyPI. Are you sure? (y/N)"
        read -p "" confirm

        if [[ $confirm =~ ^[Yy]$ ]]; then
            if poetry publish; then
                print_success "Successfully published to PyPI"
                print_status "Package is now available at: https://pypi.org/project/roadmap-cli/$CURRENT_VERSION/"
                print_status "Users can install with: pip install roadmap-cli"
            else
                print_error "PyPI publication failed"
                exit 1
            fi
        else
            print_status "Publication cancelled"
        fi
        ;;

    3)
        print_status "Publishing to TestPyPI first..."

        # Configure TestPyPI if not already configured
        poetry config repositories.test-pypi https://test.pypi.org/legacy/ 2>/dev/null || true

        # Publish to TestPyPI
        if poetry publish -r test-pypi; then
            print_success "Successfully published to TestPyPI"
            print_status "Testing installation from TestPyPI..."

            # Test installation
            if pip install --index-url https://test.pypi.org/simple/ roadmap-cli==$CURRENT_VERSION --force-reinstall; then
                print_success "Test installation successful"

                # Test basic functionality
                if roadmap --version; then
                    print_success "Basic functionality test passed"

                    print_warning "TestPyPI test successful. Proceed with PyPI publication? (y/N)"
                    read -p "" confirm

                    if [[ $confirm =~ ^[Yy]$ ]]; then
                        print_status "Publishing to PyPI..."
                        if poetry publish; then
                            print_success "Successfully published to PyPI"
                            print_status "Package is now available at: https://pypi.org/project/roadmap-cli/$CURRENT_VERSION/"
                        else
                            print_error "PyPI publication failed"
                            exit 1
                        fi
                    else
                        print_status "PyPI publication cancelled"
                    fi
                else
                    print_error "Basic functionality test failed"
                    exit 1
                fi
            else
                print_error "Test installation failed"
                exit 1
            fi
        else
            print_error "TestPyPI publication failed"
            exit 1
        fi
        ;;

    4)
        print_status "Publication cancelled"
        exit 0
        ;;

    *)
        print_error "Invalid option"
        exit 1
        ;;
esac

# Post-publication tasks
echo ""
print_success "Publication completed successfully!"
print_status "Post-publication tasks:"
echo "  • Update GitHub repository with release tag"
echo "  • Update documentation with new version"
echo "  • Announce the release"
echo "  • Monitor for issues and feedback"

# Suggest next steps
echo ""
print_status "Suggested next steps:"
echo "  1. Create GitHub release: git tag v$CURRENT_VERSION && git push origin v$CURRENT_VERSION"
echo "  2. Update documentation site"
echo "  3. Announce on social media/communities"
echo "  4. Monitor PyPI download statistics"

print_success "Publication script completed!"
