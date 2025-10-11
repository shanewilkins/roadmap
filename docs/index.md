# Roadmap CLI

A powerful, modern command-line tool for creating and managing project roadmaps with GitHub integration, team collaboration, and advanced analytics.

## ✨ Key Features

- **🗺️ Comprehensive Roadmap Management** - Create, track, and manage project roadmaps with issues and milestones
- **🔄 GitHub Integration** - Seamless synchronization with GitHub repositories and issues
- **👥 Team Collaboration** - Multi-user support with role-based permissions and handoff workflows
- **📊 Advanced Analytics** - Data-driven insights with pandas-powered analytics and export capabilities
- **⚡ High Performance** - Optimized for large projects with bulk operations and concurrent processing
- **🔒 Enterprise Security** - Secure credential management and data validation
- **📈 Data Export** - Export to CSV, Excel, and JSON for reporting and analysis

## 🚀 Quick Start

### Installation

```bash
pip install roadmap-cli
```

### Basic Usage

```bash
# Initialize a new roadmap
roadmap init

# Create your first issue
roadmap issue create "Setup project structure" --priority high --type feature

# Create a milestone
roadmap milestone create "v1.0 Release" --due-date 2025-12-31

# View project status
roadmap status

# Export data for analysis
roadmap export issues --format excel
```

## 📖 Documentation Structure

### Getting Started
- **[Installation Guide](INSTALLATION.md)** - Complete setup instructions
- **[Quick Start](quickstart.md)** - Get up and running in minutes
- **[User Workflows](USER_WORKFLOWS.md)** - Step-by-step workflows

### User Guide
- **[Core Concepts](user-guide/concepts.md)** - Understanding roadmaps, issues, and milestones
- **[Issue Management](user-guide/issues.md)** - Creating and managing issues
- **[Milestone Planning](user-guide/milestones.md)** - Project milestone management
- **[Team Collaboration](user-guide/team.md)** - Multi-user workflows and permissions
- **[Data Export](user-guide/export.md)** - Export and analytics features
- **[GitHub Integration](user-guide/github.md)** - Sync with GitHub repositories

### Reference
- **[CLI Reference](CLI_REFERENCE.md)** - Complete command documentation
- **[API Reference](api/index.md)** - Python API documentation
- **[Configuration](configuration.md)** - Configuration options and settings

### Advanced Topics
- **[Performance Optimization](PERFORMANCE_OPTIMIZATION.md)** - Scaling and optimization
- **[Security Guide](SECURITY.md)** - Security best practices
- **[Architecture](architecture.md)** - Technical architecture overview

## 💡 Key Concepts

### Issues
Issues are the fundamental units of work in your roadmap. Each issue represents a task, feature, bug fix, or any work item that needs to be tracked.

```bash
# Create an issue
roadmap issue create "Implement user authentication" \\
  --priority critical \\
  --type feature \\
  --milestone "v1.0" \\
  --assignee john \\
  --estimate 8

# List issues with filtering
roadmap issue list --status in-progress --assignee john
```

### Milestones
Milestones represent significant project checkpoints or releases. They help organize issues into deliverable chunks.

```bash
# Create a milestone
roadmap milestone create "Beta Release" \\
  --due-date 2025-06-01 \\
  --description "Initial beta version with core features"

# Assign issues to milestone
roadmap issue update ISSUE_ID --milestone "Beta Release"
```

### Team Collaboration
Roadmap CLI supports multi-user workflows with assignment tracking, handoffs, and team analytics.

```bash
# Assign an issue
roadmap issue update ISSUE_ID --assignee alice

# Hand off to another team member
roadmap handoff ISSUE_ID bob --context "Needs frontend integration"

# View team workload
roadmap team workload
```

### Data Export and Analytics
Export your roadmap data for reporting, analysis, and stakeholder communication.

```bash
# Export issues to Excel
roadmap export issues --format excel --milestone "v1.0"

# Generate analytics dashboard
roadmap analytics --period month --export --format excel

# Export with filtering
roadmap export issues --format csv --status done --priority critical
```

## 🏗️ Architecture

Roadmap CLI is built with modern Python practices and enterprise-grade features:

- **📝 YAML-based Persistence** - Human-readable storage with validation and backup
- **🔧 Pydantic Models** - Type-safe data structures with rich validation
- **⚡ High-Performance Sync** - Optimized GitHub API integration
- **🛡️ Secure Credentials** - System keyring integration for token storage
- **📊 Pandas Integration** - Advanced data manipulation and analytics
- **🔒 File Locking** - Safe concurrent access and conflict prevention

## 🤝 Contributing

We welcome contributions! See our [Contributing Guide](contributing.md) for details on:

- Setting up the development environment
- Code style and testing requirements
- Submitting pull requests
- Reporting issues

## 📄 License

Roadmap CLI is released under the MIT License. See [LICENSE](license.md) for details.

## 🆘 Support

- **Documentation**: [https://roadmap-cli.readthedocs.io/](https://roadmap-cli.readthedocs.io/)
- **Issues**: [GitHub Issues](https://github.com/roadmap-cli/roadmap/issues)
- **Discussions**: [GitHub Discussions](https://github.com/roadmap-cli/roadmap/discussions)
- **Email**: support@roadmap-cli.com

---

*Built with ❤️ for project managers, developers, and teams who value organized, data-driven project planning.*