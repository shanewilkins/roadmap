# Homebrew formula for Roadmap CLI
#
# Installation:
#   brew install roadmap-cli
#
# Or from this file:
#   brew install --formula scripts/roadmap-cli.rb

class RoadmapCli < Formula
  desc "CLI tool for project roadmap management with GitHub integration"
  homepage "https://github.com/shanewilkins/roadmap"
  url "https://files.pythonhosted.org/packages/source/r/roadmap_cli/roadmap_cli-1.0.0.tar.gz"
  sha256 "1526652af159fce98b68fb45aa9eb2f48f52fdc174e26afdfbec36f8091eeab3"
  license "MIT"

  depends_on "python@3.11"

  def install
    virtualenv_install_with_resources
  end

  test do
    system bin/"roadmap", "--version"
  end
end
