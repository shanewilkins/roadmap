# Homebrew formula for Roadmap CLI
#
# Installation:
#   brew install --formula scripts/roadmap.rb
#
# Or add to a custom tap and install normally:
#   brew tap roadmap-cli/roadmap
#   brew install roadmap

class Roadmap < Formula
  desc "Enterprise-grade CLI tool for project roadmap management with GitHub integration"
  homepage "https://github.com/shanewilkins/roadmap"
  url "https://files.pythonhosted.org/packages/source/r/roadmap/roadmap-1.0.0.tar.gz"
  sha256 "PLACEHOLDER"  # Replace with actual SHA256 from PyPI release
  license "MIT"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  def post_install
    # Ensure the CLI is available
    bin.install_symlink libexec/"bin/roadmap"
  end

  test do
    system bin/"roadmap", "--version"
  end
end
