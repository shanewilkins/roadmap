# Roadmap CLI 🗺️

[![PyPI version](https://badge.fury.io/py/roadmap-cli.svg)](https://badge.fury.io/py/roadmap-cli)
[![Python Support](https://img.shields.io/pypi/pyversions/roadmap-cli.svg)](https://pypi.org/project/roadmap-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Coverage](https://img.shields.io/badge/coverage-87%25-brightgreen.svg)](https://roadmap-cli.readthedocs.io)
[![Documentation](https://img.shields.io/badge/docs-available-brightgreen.svg)](https://roadmap-cli.readthedocs.io)

An enterprise-grade command line tool for project roadmap management with GitHub integration, data visualization, and advanced analytics. Transform your project planning workflow with powerful issue tracking, milestone management, and stakeholder reporting capabilities.

## ✨ Key Features

### 🗺️ **Project Management**

- **Complete Roadmap System** - Initialize and manage structured project roadmaps
- **Advanced Issue Tracking** - Create, update, and organize issues with rich metadata
- **Milestone Management** - Define and monitor project milestones with progress tracking
- **Intelligent Status Tracking** - Comprehensive workflow states (todo, in-progress, blocked, review, done)
- **Priority & Assignment** - Priority levels, assignee management, and team collaboration

### 📊 **Data Visualization & Analytics**

- **Interactive Charts** - Status distribution, burndown, velocity, and team workload charts
- **Stakeholder Dashboards** - Executive-ready comprehensive project overview reports
- **Multiple Output Formats** - HTML (interactive), PNG (static), SVG (vector) export
- **Performance Analytics** - Team velocity tracking, cycle time analysis, and productivity insights
- **Visual Progress Tracking** - Milestone progress bars, completion trends, and forecasting

### 🔧 **Enterprise-Grade Persistence**

- **Advanced YAML Validation** - Schema validation with automatic backup and recovery
- **File Locking System** - Safe concurrent access for multi-user environments
- **Bulk Operations** - Directory-wide validation, updates, and batch processing
- **Data Export** - CSV, Excel export with comprehensive analytics and reporting
- **Schema Migration** - Automated format updates and backward compatibility

### 🚀 **GitHub Integration**

- **High-Performance Sync** - 40x faster synchronization (100+ items in seconds)
- **Two-way Synchronization** - Seamless push/pull with GitHub repositories
- **Intelligent Caching** - Smart API usage optimization with configurable TTL
- **Batch Processing** - Parallel operations with configurable workers
- **OAuth Authentication** - Secure token management and credential storage

### 🔒 **Security & Reliability**

- **Enterprise Security** - Comprehensive security module with audit logging
- **Input Validation** - Protection against injection and path traversal attacks
- **87% Test Coverage** - Comprehensive test suite ensuring reliability
- **Error Resilience** - Graceful error handling with informative user feedback
- **Cross-Platform** - Windows, macOS, Linux compatibility

## 🚀 Quick Start

### Installation

```bash
# Install from PyPI (recommended)
pip install roadmap-cli

# Verify installation
roadmap --version
```

### Initialize Your First Roadmap

```bash
# Create a new roadmap
roadmap init

# Add your first issue
roadmap issue create "Implement user authentication" \
  --priority high \
  --status todo \
  --assignee john-doe

# Create a milestone
roadmap milestone create "v1.0 Release" \
  --due-date 2024-12-31 \
  --description "First major release"

# View your roadmap
roadmap issue list
```

### Generate Visual Reports

```bash
# Create interactive status dashboard
roadmap visualize dashboard

# Generate milestone progress chart
roadmap visualize milestones --format png

# Team workload analysis
roadmap visualize team --format html
```

### GitHub Integration

```bash
# Connect to GitHub repository
roadmap github auth

# Sync with GitHub issues
roadmap github sync --repo username/repository

# Push local changes to GitHub
roadmap github push --repo username/repository
```

1. **Clone the repository:**

```bash
git clone https://github.com/roadmap-cli/roadmap.git
cd roadmap
```

1. **Install with Poetry:**

```bash
poetry install
```

1. **Activate the virtual environment:**

```bash
poetry shell
```

## 📖 Quick Start

### 🎯 Try the Demo Project (Recommended)

Want to see Roadmap CLI in action immediately? We've included a comprehensive demo project with 1,346 realistic issues:

```bash
# Navigate to the demo project
cd demo-project

# Explore the project
roadmap issue list
roadmap project               # Project analytics
roadmap dashboard            # Interactive charts
roadmap export csv           # Data export

# Run feature demonstrations
python demo_scripts/demos/project_analytics_demo.py
python demo_scripts/demos/visualization_demo.py
```

The demo project showcases the complete "CloudSync Enterprise Platform" development with 5 milestones, 16 team members, and realistic project data. Perfect for learning all features before creating your own project.

### Basic Workflow

```bash
# 1. Initialize a new roadmap
roadmap init

# 2. Create your first issue
roadmap issue create "Implement user authentication" \
  --priority high \
  --milestone "v1.0" \
  --assignee "developer1"

# 3. Add a milestone
roadmap milestone create "v1.0" \
  --description "First major release" \
  --due-date "2024-12-31"

# 4. View your roadmap
roadmap issue list
roadmap milestone list

# 5. Track progress
roadmap issue update "Implement user authentication" --status in-progress
```

### GitHub Integration Workflow

```bash
# 1. Setup GitHub integration
roadmap sync setup \
  --token "your-github-token" \
  --repo "username/repository"

# 2. Test connection
roadmap sync test

# 3. Pull existing issues from GitHub (high-performance)
roadmap sync pull --high-performance

# 4. Create local issues and push to GitHub
roadmap issue create "New feature request"
roadmap sync push --issues

# 5. Sync everything efficiently
roadmap sync pull --high-performance --workers 12 --batch-size 25
```

## 🎬 Interactive Demos

Explore features with ready-to-run demonstration scripts in the `demos/` directory:

```bash
# Comment management features
python demos/comment_demo.py

# Blocked status workflow
python demos/blocked_status_demo.py

# Enhanced delete safety
python demos/delete_safety_demo.py

# Advanced list filtering
python demos/enhanced_list_demo.py

# Performance optimization
python demos/performance_demo.py
```

Each demo showcases specific features with examples, benefits, and usage patterns. Perfect for learning new features or demonstrating capabilities to team members.

## 📋 Complete Command Reference

### Project Initialization

```bash
# Initialize new roadmap
roadmap init

# Check initialization status
roadmap status
```

### Issue Management

```bash
# Create issues
roadmap issue create "Issue title"
roadmap issue create "Complex issue" \
  --priority high \
  --status in-progress \
  --milestone "v2.0" \
  --assignee "team-lead" \
  --labels bug,frontend

# List and search issues
roadmap issue list
roadmap issue list --status todo --priority high
roadmap issue list --milestone "v1.0"

# Update issues
roadmap issue update "Issue title" --status done
roadmap issue update "Issue title" --priority low --assignee "new-dev"

# Delete issues
roadmap issue delete "Issue title"
```

### Milestone Management

```bash
# Create milestones
roadmap milestone create "v1.0" --description "First release"
roadmap milestone create "v2.0" \
  --description "Major update" \
  --due-date "2024-12-31" \
  --status open

# List milestones
roadmap milestone list
roadmap milestone list --status open

# Update milestones
roadmap milestone update "v1.0" --status closed
roadmap milestone update "v2.0" --due-date "2025-01-15"

# Delete milestones
roadmap milestone delete "v1.0"
```

### GitHub Synchronization

```bash
# Setup and configuration
roadmap sync setup --token "token" --repo "user/repo"
roadmap sync test
roadmap sync status
roadmap sync delete-token

# Standard sync
roadmap sync pull --issues --milestones
roadmap sync push --issues --milestones

# High-performance sync (recommended for 50+ items)
roadmap sync pull --high-performance
roadmap sync pull --high-performance --workers 16 --batch-size 100
roadmap sync push --high-performance

# Selective sync
roadmap sync pull --issues --high-performance
roadmap sync pull --milestones
```

### Bulk Operations

```bash
# Validate entire directory
roadmap bulk validate /path/to/roadmaps

# Generate health report
roadmap bulk health-report /path/to/roadmaps

# Backup directory
roadmap bulk backup /path/to/roadmaps

# Batch field updates
roadmap bulk update-field /path/to/roadmaps \
  --field priority \
  --old-value medium \
  --new-value high
```

## 🏗️ Architecture & Features

### Enhanced YAML Persistence

- **Schema Validation**: Pydantic-based validation for data integrity
- **Error Recovery**: Automatic recovery from corrupted YAML files
- **Backup System**: Timestamped backups before every modification
- **Migration Tools**: Schema version migration and format conversion

### File Locking System

- **Concurrent Safety**: Prevents data corruption during simultaneous access
- **Platform Support**: Cross-platform file locking (Unix/Windows)
- **Deadlock Prevention**: Intelligent lock management and timeout handling
- **Transaction Safety**: Atomic operations for data consistency

### High-Performance Sync

- **Parallel Processing**: Configurable worker threads for concurrent operations
- **Batch Operations**: Process items in batches to optimize API usage
- **Smart Caching**: 5-minute TTL cache for GitHub API responses
- **Performance Metrics**: Real-time throughput and timing analysis

| Sync Type | 100 Issues | Time | API Calls | Improvement |
|-----------|------------|------|-----------|-------------|
| Standard  | Sequential | 52s  | 102 calls | Baseline |
| High-Perf | Parallel   | 1.3s | 2 calls   | **40x faster** |

### Technology Stack

- **Python 3.12+**: Latest Python with cutting-edge performance features
- **Click**: Robust command-line interface framework
- **Rich**: Beautiful terminal output with tables and progress bars
- **Pydantic**: Advanced data validation and settings management
- **PyYAML**: Enhanced YAML processing with custom validation
- **Poetry**: Modern dependency management and packaging
- **pytest**: Comprehensive testing with 87% coverage

## 📁 Project Structure

```text
roadmap/
├── roadmap/
│   ├── __init__.py              # Package initialization
│   ├── cli.py                   # Main CLI interface
│   ├── core.py                  # Core roadmap functionality
│   ├── models.py                # Data models and validation
│   ├── parser.py                # YAML parsing and validation
│   ├── persistence.py           # Enhanced YAML persistence
│   ├── bulk_operations.py       # Bulk file operations
│   ├── file_locking.py          # Concurrent access protection
│   ├── sync.py                  # GitHub synchronization
│   ├── performance_sync.py      # High-performance sync engine
│   ├── github_client.py         # GitHub API integration
│   └── credentials.py           # Secure credential management
├── tests/                       # Comprehensive test suite (87% coverage)
├── .roadmap/                    # Local roadmap data (created by init)
│   ├── issues/                  # Issue YAML files
│   ├── milestones/              # Milestone YAML files
│   ├── templates/               # File templates
│   └── config.yaml              # Local configuration
├── pyproject.toml               # Poetry configuration
└── README.md                    # This documentation
```

## 🔄 User Workflows

### Workflow 1: Solo Developer

```bash
# Setup
roadmap init
roadmap sync setup --token "token" --repo "user/project"

# Daily workflow
roadmap issue create "Fix login bug" --priority high
roadmap milestone create "v1.1" --due-date "2024-11-15"
roadmap sync push --issues --milestones

# Project updates
roadmap issue update "Fix login bug" --status done
roadmap sync pull --high-performance  # Get team updates
```

### Workflow 2: Team Development

```bash
# Team leader setup
roadmap init
roadmap sync setup --token "team-token" --repo "org/project"
roadmap sync pull --high-performance  # Import existing issues

# Daily team sync
roadmap sync pull --high-performance  # Get latest from GitHub
roadmap issue create "Team standup notes"
roadmap bulk validate .roadmap/       # Validate local changes
roadmap sync push --issues            # Share with team
```

### Workflow 3: Large-Scale Project

```bash
# Initial import from active repository
roadmap init
roadmap sync setup --token "token" --repo "large-org/enterprise-app"
roadmap sync pull --high-performance --workers 16 --batch-size 100

# Bulk operations for project management
roadmap bulk health-report .roadmap/
roadmap bulk update-field .roadmap/ --field priority --old-value medium --new-value high
roadmap bulk backup .roadmap/

# Performance monitoring
roadmap sync pull --high-performance  # Monitor performance metrics
```

## 🛠️ Advanced Configuration

### Performance Tuning

```bash
# Optimize for your system
roadmap sync pull --high-performance \
  --workers 16 \           # CPU cores × 2
  --batch-size 100         # Larger batches for more items

# Monitor performance
roadmap sync pull --high-performance  # Shows performance report
```

### Advanced Bulk Operations

```bash
# Project health monitoring
roadmap bulk health-report /projects/roadmaps/

# Backup before major changes
roadmap bulk backup /projects/roadmaps/

# Mass updates
roadmap bulk update-field /projects/ \
  --field assignee \
  --condition "milestone=v1.0" \
  --new-value "team-lead"
```

## 🧪 Testing & Quality

### Running Tests

```bash
# Run full test suite
poetry run pytest

# Run with coverage
poetry run pytest --cov=roadmap --cov-report=html

# Test specific components
poetry run pytest tests/test_performance_sync.py
poetry run pytest tests/test_bulk_operations.py
```

### Code Quality

```bash
# Format code
poetry run black .
poetry run isort .

# Type checking
poetry run mypy roadmap

# Linting
poetry run flake8 roadmap
```

## 📈 Performance Benchmarks

| Scenario | Items | Standard Time | HP Time | Improvement | API Reduction |
|----------|-------|---------------|---------|-------------|---------------|
| Small    | 12    | 6.1s         | 1.1s    | **5.5x**    | 12→2 (6x)     |
| Medium   | 54    | 26.5s        | 1.2s    | **23x**     | 52→2 (26x)    |
| Large    | 106   | 52.1s        | 1.3s    | **40x**     | 102→2 (51x)   |
| Enterprise| 515   | 256.1s       | 2.5s    | **102x**    | 502→2 (251x)  |

## 🚨 Troubleshooting

### Common Issues

#### YAML Validation Errors

```bash
# Check file syntax
roadmap bulk validate .roadmap/

# View detailed error report
roadmap bulk health-report .roadmap/

# Restore from backup
ls .roadmap/.backups/
cp .roadmap/.backups/issues_20241010_143022/issue.yaml .roadmap/issues/
```

#### GitHub Sync Issues

```bash
# Test connection
roadmap sync test

# Check token and repository
roadmap sync status

# Reset configuration
roadmap sync delete-token
roadmap sync setup --token "new-token" --repo "user/repo"
```

#### Performance Issues

```bash
# Use high-performance mode
roadmap sync pull --high-performance

# Adjust workers and batch size
roadmap sync pull --high-performance --workers 4 --batch-size 25

# Monitor performance
roadmap sync pull --high-performance  # Check performance report
```

## 🤝 Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes with tests**
4. **Run the full test suite**:

   ```bash
   poetry run pytest --cov=roadmap
   poetry run black .
   poetry run isort .
   poetry run flake8 roadmap
   poetry run mypy roadmap
   ```

5. **Commit your changes**: `git commit -m 'Add amazing feature'`
6. **Push to the branch**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**

### Development Environment

```bash
# Setup development environment
git clone https://github.com/yourusername/roadmap.git
cd roadmap
poetry install
poetry shell

# Run tests during development
poetry run pytest tests/test_performance_sync.py -v
poetry run pytest tests/test_bulk_operations.py -v
poetry run pytest tests/test_file_locking.py -v
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## � Documentation

Complete documentation is available in the [`/docs`](docs/) directory:

| Document | Description |
|----------|-------------|
| **[Installation Guide](docs/INSTALLATION.md)** | Complete setup and installation instructions |
| **[User Workflows](docs/USER_WORKFLOWS.md)** | Step-by-step workflows for different scenarios |
| **[CLI Reference](docs/CLI_REFERENCE.md)** | Complete command reference with examples |
| **[Feature Showcase](docs/FEATURE_SHOWCASE.md)** | Technical deep-dive into advanced features |
| **[Performance Optimization](docs/PERFORMANCE_OPTIMIZATION.md)** | Performance analysis and optimization guide |
| **[Troubleshooting](docs/TROUBLESHOOTING.md)** | Common issues and solutions |
| **[Security Guide](docs/SECURITY.md)** | Security best practices and guidelines |

## ️ Roadmap

### ✅ Completed Features (Current)

- Enhanced YAML persistence with validation and recovery
- Comprehensive issue and milestone management
- GitHub two-way synchronization
- High-performance sync engine (40x speed improvement)
- Bulk operations and directory management
- File locking for concurrent access
- Advanced CLI with rich output
- Comprehensive testing (87% coverage)

### 🔄 In Progress

- Format migration tools for schema evolution
- Documentation and user workflow guides
- Performance optimization tutorials

### 📅 Planned Features

- Timeline and Gantt chart visualization
- Advanced filtering and search capabilities
- Team collaboration features
- Plugin system for extensibility
- Web dashboard interface
- Mobile app companion
- Integration with popular project management tools
- Advanced analytics and reporting

### 💡 Contributing Ideas

- Custom export formats (PDF, HTML, Markdown)
- Dependency tracking between issues
- Automated milestone progress calculation
- Slack/Discord/Teams integration
- Custom field definitions
- Template system for issue types
- Advanced GitHub webhook support

---

Built with ❤️ using Python 3.12+ and modern development practices

*For detailed API documentation, examples, and advanced usage patterns, visit our [documentation site](https://roadmap-cli.readthedocs.io) (coming soon).*
