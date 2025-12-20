================================================================================
Architecture Overview
================================================================================

Roadmap CLI is a Python command-line tool for managing project roadmaps with milestones and issues.

System Architecture
===================

Roadmap CLI follows a layered, modular architecture:

.. code-block:: text

    ┌─────────────────────────────────────────────────┐
    │         Command Line Interface (Click)          │
    │     project, milestone, issue, git, init        │
    └──────────────────┬──────────────────────────────┘
                       │
    ┌──────────────────┴──────────────────────────────┐
    │         Presentation Layer                      │
    │     Validators, Formatters, Output Handlers     │
    └──────────────────┬──────────────────────────────┘
                       │
    ┌──────────────────┴──────────────────────────────┐
    │         Application Services                    │
    │     Command Handlers, Business Logic            │
    └──────────────────┬──────────────────────────────┘
                       │
    ┌──────────────────┴──────────────────────────────┐
    │         Domain Layer                            │
    │     Projects, Milestones, Issues, Models        │
    └──────────────────┬──────────────────────────────┘
                       │
    ┌──────────────────┴──────────────────────────────┐
    │         Infrastructure Layer                    │
    │  File I/O, GitHub API, Git Operations, Logging  │
    └─────────────────────────────────────────────────┘

Core Components
===============

**CLI Layer** (roadmap/adapters/cli/)
    - Entry point for all commands
    - Click framework for command parsing
    - Input validation and error handling
    - Command routing to services

**Presentation Layer** (roadmap/adapters/cli/presentation/)
    - Table formatters (projects, milestones, issues)
    - Kanban board visualization
    - JSON/CSV export formatters
    - Output styling and formatting

**Domain Models** (roadmap/core/domain/, roadmap/domain/)
    - Project - Container for milestones
    - Milestone - Time-based deliverable
    - Issue - Discrete unit of work
    - Team - Multiple project collaborators
    - Data value objects (Priority, Status, etc.)

**Services Layer** (roadmap/core/services/, roadmap/infrastructure/)
    - Project operations (create, update, list, archive)
    - Milestone operations (create, close, sync)
    - Issue operations (create, start, block, done)
    - GitHub synchronization
    - Data validation and consistency

**Persistence** (roadmap/adapters/persistence/)
    - JSON-based file storage
    - SQLite database support
    - File synchronization utilities
    - Data repositories

**GitHub Integration** (roadmap/adapters/github/, roadmap/infrastructure/github/)
    - Milestone ↔ GitHub releases sync
    - Issue ↔ GitHub issues sync
    - PR linking and tracking
    - Token management

**Shared Utilities** (roadmap/shared/)
    - Text formatting and display
    - Error handling and logging
    - Security and input validation
    - Observability and instrumentation

Data Model Hierarchy
====================

Roadmap uses a hierarchical three-level model:

.. code-block:: text

    Project
    ├── Metadata (name, owner, created, updated)
    ├── Status (open, archived)
    ├── Milestones
    │   ├── Name
    │   ├── Target date
    │   ├── Status (open, closed, overdue)
    │   └── Issues
    │       ├── Title
    │       ├── Description
    │       ├── Status (open, in-progress, done, blocked)
    │       ├── Priority (low, medium, high, critical)
    │       ├── Assignee
    │       ├── Labels
    │       └── Dependencies (blocked by, blocks)
    └── GitHub Integration
        ├── Organization
        ├── Repository
        └── Sync status

Key Design Decisions
====================

**Hierarchical Organization**
    - Projects contain milestones contain issues
    - Intuitive mental model matching product development
    - Supports filtering and aggregation across levels

**Local-First Storage**
    - Data stored locally in ~/.roadmap/ by default
    - Git-friendly JSON format
    - Can be version controlled by user
    - GitHub sync is optional, bidirectional

**Separation of Concerns**
    - CLI layer handles user interaction
    - Domain layer defines data structures
    - Services layer contains business logic
    - Persistence layer handles storage
    - Each layer has clear, testable boundaries

**Click Framework**
    - Decorator-based command definition
    - Built-in help and completion
    - Extensible command hierarchy
    - Consistent UX across all commands

**Status-Based Workflows**
    - Issues track status: open → in-progress → done
    - Milestones track status: open → closed (or overdue)
    - Projects can be archived (soft delete)
    - Status changes recorded with timestamps

**Type Safety**
    - Python dataclasses for model definition
    - Type annotations throughout codebase
    - Validation at boundaries (CLI input, file I/O)
    - Pydantic models for complex validation

Technology Stack
=================

**Core**
    - Python 3.10+
    - Click framework for CLI
    - dataclasses for models
    - Pydantic for validation

**Persistence**
    - JSON for configuration and data
    - SQLite for structured data queries
    - YAML for config files

**GitHub Integration**
    - PyGithub library
    - GitHub REST API v3

**Testing**
    - pytest for unit and integration tests
    - pytest-cov for coverage reporting
    - Factory fixtures for test data

**Observability**
    - OpenTelemetry for instrumentation
    - Jaeger for distributed tracing
    - Structured logging

**Development**
    - Poetry for package management
    - Pre-commit hooks for quality checks
    - Sphinx for documentation
    - Mkdocs for user guides

Command Structure
=================

Roadmap commands follow a pattern: ``roadmap <resource> <action> <name>``

.. code-block:: text

    roadmap project create "My Project"
    roadmap project list
    roadmap project kanban "My Project"

    roadmap milestone create "v1.0" --project "My Project" --date "2025-03-31"
    roadmap milestone close "v1.0"

    roadmap issue create "Add feature X" --milestone "v1.0"
    roadmap issue start "Add feature X"
    roadmap issue done "Add feature X"

Configuration System
====================

Configuration via multiple sources (priority order):

1. Command-line flags (highest priority)
2. Environment variables
3. Config file (~/.roadmap/config.yaml)
4. Defaults (lowest priority)

Key settings:

.. code-block:: yaml

    data_dir: ~/.roadmap/data/
    github:
        enabled: true
        token: ${GITHUB_TOKEN}
        org: my-org
    logging:
        level: INFO
        format: json

Extensibility Points
====================

1. **Custom formatters** - Add new output formats
2. **Custom repositories** - Change storage backend
3. **GitHub integration plugins** - Extend sync capabilities
4. **Command hooks** - Pre/post command execution
5. **Validators** - Custom business logic validation

Performance Characteristics
============================

- **Load time**: < 100ms for typical projects
- **List operations**: O(n) where n = number of items
- **Create operations**: O(1) amortized
- **GitHub sync**: Configurable, runs asynchronously
- **Memory footprint**: < 50MB for 10,000 items

See Also
========

- :doc:`design-decisions` - Design decisions and rationale
- :doc:`performance` - Performance profiling and optimization
- :doc:`../developer/development` - Contributing and development guide
