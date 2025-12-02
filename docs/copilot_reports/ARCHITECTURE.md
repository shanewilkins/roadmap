# Git-SQLite Architecture Documentation

## Overview

This document outlines the architectural decisions for the roadmap CLI v1.0, which adopts a **git-only, stateful CLI architecture** with SQLite as a performance cache layer.

## Core Architecture Principles

### 1. Git as Single Source of Truth

- All roadmap data (issues, milestones, projects) stored as YAML files in `.roadmap/` directory
- Git repository history is the authoritative record
- SQLite database serves as a fast index/cache for queries and operations
- Database can be rebuilt from git files at any time

### 2. Stateful CLI with Database Backend

- SQLite provides fast queries, relationships, and complex operations
- In-memory caching for frequently accessed data
- Structured logging for all operations
- Environment-aware configuration management

### 3. Automatic Synchronization

- Git hooks automatically sync changes between git files and SQLite
- No manual sync commands required for day-to-day operations
- Incremental updates for performance on large repositories

## Git-SQLite Integration Strategy

### Data Flow Architecture

```text
[User CLI Command] → [Update YAML Files] → [Git Commit] → [Git Hook] → [Update SQLite]
                                                             ↓
[Display Results] ← [Query SQLite] ← [CLI Response] ← [Sync Complete]

```text

### File Structure

```text
.roadmap/
├── config.yaml              # Project configuration

├── issues/
│   ├── issue-abc123.md      # Individual issue files (YAML frontmatter + markdown)

│   └── issue-def456.md
├── milestones/
│   ├── milestone-v1.0.md    # Milestone definitions

│   └── milestone-v2.0.md
└── projects/
    └── main-project.md      # Project metadata

.roadmap.db                  # SQLite cache (gitignored)

.roadmap/logs/              # Application logs

```text

## Key Architectural Decisions

### 1. Conflict Resolution Strategy

**Decision**: Disable SQLite during git conflicts, rebuild after resolution

**Implementation**:
- Git hooks detect merge conflicts in `.roadmap/` files
- SQLite enters "conflict mode" (read-only operations only)
- CLI shows clear messaging about conflict state
- After conflict resolution + commit, automatic SQLite rebuild
- Users resolve conflicts in human-readable YAML files

**Rationale**:
- Prevents data corruption during conflicts
- Maintains data integrity
- Forces conflict resolution at the data level
- Simple to implement and debug

### 2. Performance Strategy

**Decision**: Incremental updates with full rebuild fallback

**Implementation**:
- Track file modification times and content hashes
- Only parse/update changed files during sync operations
- Full rebuild when hashes missing or database corrupted
- Lazy loading for complex queries and relationships

**Performance Targets**:
- Sub-second response for typical operations
- Support for 1000+ issues without performance degradation
- Incremental syncs complete in <2 seconds
- Full rebuilds complete in <30 seconds for large repositories

**Rationale**:
- Scales to enterprise-size projects
- Fast day-to-day operations
- Safety net of full rebuild capability
- Balances performance with reliability

### 3. Data Migration Strategy

**Decision**: Auto-rebuild on first CLI command

**Implementation**:
- SQLite database not committed to git (in .gitignore)
- First CLI command checks for database existence/currency
- Auto-rebuild from `.roadmap/` files if missing or stale
- Progress indicators for rebuild operations
- Cache rebuild metadata for future validation

**User Experience Flow**:

```bash
$ git clone roadmap-project && cd roadmap-project
$ roadmap list issues
🔄 Building database index from git files... ████████████ 100%
📊 Found 23 issues, 5 milestones, 2 projects
[normal command output]

```text

**Rationale**:
- Zero setup friction for new team members
- Self-healing system (auto-recovery from corruption)
- Works with any git workflow
- Clear user feedback and progress indication

### 4. Offline/Online Mode Strategy

**Decision**: Require git repository, graceful degradation for hooks

**Implementation**:
- Hard requirement: CLI only operates within git repositories
- Git hooks are optional (manual sync mode available)
- Graceful fallback when hooks fail (warning + continue)
- Manual sync command: `roadmap sync`

**Error Handling Examples**:

```bash

# Outside git repository

$ roadmap list issues
❌ Error: roadmap requires a git repository
   Run 'git init' or 'cd' to a git repository

# Git hooks disabled/broken

$ roadmap issue update 123 --status done
✅ Updated issue 123
⚠️  Warning: Git hooks not installed. Run 'roadmap git setup' for auto-sync
   Manual sync available: roadmap sync

```text

**Rationale**:
- Aligns with git-only architecture principle
- Clear guidance for users in error states
- Flexible deployment for different team configurations
- Maintains data integrity guarantees

## Database Schema Design

### Core Tables

```sql
-- Projects: Top-level containers
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT  -- JSON for extensibility
);

-- Milestones: Project phases/releases
CREATE TABLE milestones (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    due_date DATE,
    progress_percentage REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
);

-- Issues: Individual work items
CREATE TABLE issues (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    milestone_id TEXT,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    priority TEXT NOT NULL DEFAULT 'medium',
    issue_type TEXT NOT NULL DEFAULT 'task',
    assignee TEXT,
    estimate_hours REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    due_date DATE,
    metadata TEXT,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    FOREIGN KEY (milestone_id) REFERENCES milestones (id) ON DELETE SET NULL
);

```text

### Sync Tracking Tables

```sql
-- File synchronization state
CREATE TABLE file_sync_state (
    file_path TEXT PRIMARY KEY,
    content_hash TEXT NOT NULL,
    file_size INTEGER,
    last_modified TIMESTAMP,
    last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Git synchronization metadata
CREATE TABLE sync_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Example keys: last_commit_hash, last_sync_time, git_conflicts_detected

```text

## Implementation Phases

### Phase 1: Infrastructure Foundation ✅ COMPLETE

- Added core dependencies (structlog, GitPython, dynaconf, etc.)
- Created logging infrastructure
- Built SQLite state management foundation
- Implemented git hooks framework
- Added configuration management

### Phase 2A: Git-SQLite Sync Foundation

- **Priority 1: Basic sync infrastructure**
- Add YAML parsing to database.py
- Implement file hash tracking system
- Create incremental sync logic
- Add git conflict detection
- Test basic git hook → SQLite synchronization flow

### Phase 2B: Auto-rebuild & CLI Integration

- **Priority 2: User experience enhancement**
- Implement auto-rebuild on first CLI command
- Add progress indicators for rebuild operations
- Modify CLI commands to write YAML + auto-commit
- Create manual sync command
- Handle edge cases (corrupted DB, missing files)

### Phase 2C: Legacy Sync Elimination

- **Priority 3: Remove old architecture**
- Delete sync.py, performance_sync.py, cli/sync.py (~3000+ lines)
- Remove sync-related tests (~300 tests)
- Update CLI commands to use new SQLite backend
- Migrate existing .roadmap/ data format if needed
- Update documentation and examples

### Phase 2D: Production Polish

- **Priority 4: Performance and reliability**
- Optimize performance for large repositories (1000+ issues)
- Add advanced caching strategies
- Improve error messages and user guidance
- Add git hook health monitoring
- Comprehensive testing and documentation updates

## New CLI Commands

### Git Integration Commands

```bash
roadmap sync                 # Manual rebuild SQLite from git files

roadmap git status          # Show sync status, detect conflicts

roadmap git setup           # Install/reinstall git hooks

roadmap git check           # Validate git-SQLite consistency

roadmap git hooks           # Manage hook installation/removal

```text

### Enhanced Core Commands

```bash

# Generic update patterns

roadmap issue update ID --status STATUS --assignee USER --priority PRIORITY
roadmap milestone update ID --status STATUS --due-date DATE --progress PERCENT
roadmap project update ID --status STATUS --description TEXT

# Unified management

roadmap milestone assign MILESTONE_ID ISSUE_ID
roadmap project assign PROJECT_ID MILESTONE_ID

```text

## Configuration Settings

### Git Integration Settings

```toml
[git]
auto_sync = true              # Enable automatic git hooks

hooks_enabled = true          # Install git hooks on setup

default_branch = "main"       # Primary branch for operations

conflict_resolution = "manual"  # How to handle merge conflicts

[sync]
incremental_updates = true    # Use file hash tracking

full_rebuild_threshold = 100  # Files changed before full rebuild

progress_indicators = true    # Show progress during operations

```text

### Performance Settings

```toml
[performance]
cache_enabled = true          # Enable SQLite result caching

cache_size = "100MB"         # Maximum cache size

cache_ttl = 3600             # Cache time-to-live (seconds)

lazy_loading = true          # Load relationships on-demand

batch_size = 50              # Batch size for bulk operations

```text

## Error Handling & Recovery

### Conflict Detection

- Monitor `.roadmap/` directory for git conflict markers
- Disable write operations during conflicts
- Provide clear user guidance for conflict resolution
- Auto-recovery after conflict resolution

### Database Corruption Recovery

- Detect SQLite corruption on startup
- Automatic fallback to full rebuild from git
- Backup strategies for critical data
- User notification and progress tracking

### Git Hook Failures

- Graceful degradation when hooks fail
- Clear warnings about manual sync requirements
- Health checks for hook installation
- Recovery procedures and troubleshooting guides

## Testing Strategy

### Integration Testing

- Git repository setup and teardown
- File system operations with real git repositories
- Hook installation and execution testing
- Conflict simulation and resolution

### Performance Testing

- Large repository simulation (1000+ issues)
- Incremental sync performance benchmarks
- Memory usage profiling
- Concurrent operation testing

### Error Condition Testing

- Database corruption scenarios
- Git conflict handling
- Network/filesystem failures
- Invalid YAML parsing

## Security Considerations

### File System Security

- Secure file permissions for .roadmap.db
- Validation of file paths to prevent directory traversal
- Sanitization of YAML content
- Git hook script validation

### Data Integrity

- Transaction-based database operations
- Checksums for file integrity validation
- Atomic git operations
- Rollback capabilities for failed operations

---

**Last Updated**: November 17, 2025
**Version**: 1.0
**Status**: Implementation Phase 2A
