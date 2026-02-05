---
id: c2b21158
title: Implement performance optimization strategy with hybrid storage and caching
headline: ''
priority: medium
status: todo
issue_type: other
milestone: backlog
labels:
- synced:from-github
remote_ids: {}
created: '2026-02-05T15:17:48.036759+00:00'
updated: '2026-02-05T15:17:48.036760+00:00'
assignee: null
estimated_hours: null
due_date: null
depends_on: []
blocks: []
actual_start_date: null
actual_end_date: null
progress_percentage: null
handoff_notes: null
previous_assignee: null
handoff_date: null
git_branches: []
git_commits: []
completed_date: null
comments: []
github_issue: null
---

# Implement performance optimization strategy with hybrid storage and caching

## Description

The current file-based storage system works well for small datasets but has scalability limitations as the number of issues, milestones, and roadmaps grows. We need to implement a hybrid storage approach that maintains the git-friendly file format while adding performance optimizations through SQLite indexing and intelligent caching.

## Current Performance Analysis

### File-Store Limitations
- **List operations**: O(n) file reads for every query
- **Search operations**: Full-text grep across all files
- **Relationship queries**: Expensive traversal for dependencies/milestones
- **Memory usage**: Grows linearly with dataset size
- **Concurrent access**: Risk of file corruption

### Scale Breaking Points
- **~100-500 issues**: Noticeable delays but acceptable
- **~1,000-5,000 issues**: Slow operations, user frustration
- **~10,000+ issues**: Likely unusable without optimization

### Current Bottlenecks
```bash
# These operations become expensive at scale:
roadmap issue list --status in-progress    # Scans all files
roadmap issue list --assignee shane        # Full file reads
roadmap milestone status v090              # Relationship traversal
```

## Proposed Hybrid Architecture

### Core Design Principles
1. **Files remain source of truth** - Maintains git integration
2. **SQLite for fast queries** - Indexed metadata for performance
3. **Lazy loading content** - Only load full issue when needed
4. **Automatic sync** - Keep file and database in sync
5. **Graceful degradation** - Falls back to file-only if DB issues

### Architecture Overview
```python
# Hybrid storage layer
class HybridStorage:
    def __init__(self):
        self.file_store = FileStore()           # Current implementation
        self.index_db = SQLiteIndex()           # New performance layer
        self.cache = InMemoryCache()            # Fast access cache

    def list_issues(self, filters):
        # Fast: Query SQLite index
        return self.index_db.query(filters)

    def get_issue(self, issue_id):
        # Full content: Always from file
        return self.file_store.load(issue_id)

    def update_issue(self, issue_id, data):
        # Write to file, sync to index
        self.file_store.save(issue_id, data)
        self.index_db.update_from_file(issue_id)
```

## Implementation Plan

### Phase 1: SQLite Index Layer (2.5h)

#### Database Schema
```sql
CREATE TABLE issues (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    priority TEXT NOT NULL,
    assignee TEXT,
    milestone TEXT,
    estimated_hours REAL,
    progress_percentage INTEGER,
    created_date TEXT,
    updated_date TEXT,
    file_path TEXT NOT NULL,
    file_mtime INTEGER NOT NULL
);

CREATE INDEX idx_issues_status ON issues(status);
CREATE INDEX idx_issues_assignee ON issues(assignee);
CREATE INDEX idx_issues_milestone ON issues(milestone);
CREATE INDEX idx_issues_priority ON issues(priority);

CREATE TABLE milestones (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    due_date TEXT,
    file_path TEXT NOT NULL,
    file_mtime INTEGER NOT NULL
);

CREATE TABLE roadmaps (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    owner TEXT,
    priority TEXT,
    file_path TEXT NOT NULL,
    file_mtime INTEGER NOT NULL
);
```

#### Index Management
```python
class SQLiteIndex:
    def __init__(self, db_path='.roadmap/index.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.init_schema()

    def sync_from_files(self):
        """Full rebuild from all files"""
        for file_path in glob('.roadmap/issues/*.md'):
            self.update_from_file(file_path)

    def update_from_file(self, file_path):
        """Update single file in index"""
        metadata = parse_yaml_header(file_path)
        mtime = os.path.getmtime(file_path)

        self.conn.execute("""
            INSERT OR REPLACE INTO issues
            (id, title, status, priority, assignee, milestone,
             estimated_hours, progress_percentage, created_date,
             updated_date, file_path, file_mtime)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (metadata['id'], metadata['title'], ...))

    def is_stale(self, file_path):
        """Check if index needs update"""
        current_mtime = os.path.getmtime(file_path)
        db_mtime = self.get_file_mtime(file_path)
        return current_mtime > db_mtime
```

### Phase 2: Intelligent Caching (1.5h)

#### Memory Cache Layer
```python
class InMemoryCache:
    def __init__(self, max_size=1000):
        self.metadata_cache = LRUCache(max_size)
        self.content_cache = LRUCache(max_size // 4)  # Smaller for full content

    @lru_cache(maxsize=1000)
    def get_issue_metadata(self, issue_id, file_mtime):
        """Cache metadata keyed by file modification time"""
        return self.load_metadata_from_file(issue_id)

    def invalidate_issue(self, issue_id):
        """Clear cache when file changes"""
        # Clear all cached versions of this issue
```

#### File System Watching
```python
class FileWatcher:
    def __init__(self, storage):
        self.storage = storage
        self.observer = Observer()

    def start_watching(self):
        """Watch .roadmap directory for changes"""
        handler = FileSystemEventHandler()
        handler.on_modified = self.on_file_changed
        self.observer.schedule(handler, '.roadmap', recursive=True)
        self.observer.start()

    def on_file_changed(self, event):
        """Update index when files change"""
        if event.src_path.endswith('.md'):
            self.storage.index_db.update_from_file(event.src_path)
            self.storage.cache.invalidate_file(event.src_path)
```

### Phase 3: Performance Optimizations (2h)

#### Lazy Loading Implementation
```python
class LazyIssue:
    def __init__(self, metadata, file_path):
        self._metadata = metadata
        self._file_path = file_path
        self._content = None

    @property
    def content(self):
        """Load full content only when accessed"""
        if self._content is None:
            self._content = load_full_issue(self._file_path)
        return self._content

    # Fast access to indexed fields
    @property
    def status(self):
        return self._metadata['status']

    @property
    def assignee(self):
        return self._metadata['assignee']
```

#### Batch Operations
```python
class BatchOperations:
    def bulk_update_status(self, issue_ids, new_status):
        """Update multiple issues efficiently"""
        with self.storage.index_db.transaction():
            for issue_id in issue_ids:
                # Update file
                self.storage.file_store.update_metadata(issue_id, {'status': new_status})
                # Update index
                self.storage.index_db.update_field(issue_id, 'status', new_status)

    def bulk_assign_milestone(self, issue_ids, milestone):
        """Assign multiple issues to milestone"""
        # Similar batch processing
```

## Acceptance Criteria

### Performance Improvements
- [ ] List operations complete in <200ms for datasets up to 1000 issues
- [ ] Search operations complete in <500ms across all content
- [ ] Memory usage remains constant regardless of dataset size
- [ ] CLI remains responsive during large operations

### Data Integrity
- [ ] File format remains unchanged (git-friendly)
- [ ] Index automatically rebuilds when inconsistencies detected
- [ ] Graceful fallback to file-only mode if database issues
- [ ] No data loss during index rebuilding or corruption

### Compatibility
- [ ] Existing CLI commands work unchanged
- [ ] File-based workflows (git, manual editing) continue working
- [ ] Database is optional - tool works without it
- [ ] Migration path for existing installations

### Developer Experience
- [ ] Index rebuilding is automatic and transparent
- [ ] Performance monitoring and metrics available
- [ ] Clear error messages for storage issues
- [ ] Debug tools for troubleshooting performance

## Technical Implementation Details

### Configuration Options
```bash
# Performance settings
roadmap config set storage.use_index true
roadmap config set storage.cache_size 1000
roadmap config set storage.auto_rebuild_index true
roadmap config set storage.watch_files true

# Performance monitoring
roadmap config set debug.log_query_times true
roadmap config set debug.profile_operations true
```

### Migration Strategy
```python
def migrate_to_hybrid_storage():
    """One-time migration for existing installations"""
    print("🔄 Migrating to hybrid storage...")

    # Create SQLite index
    index = SQLiteIndex()
    index.init_schema()

    # Rebuild from all existing files
    index.sync_from_files()

    # Update configuration
    config.set('storage.use_index', True)

    print("✅ Migration complete!")
```

### Performance Monitoring
```python
class PerformanceMonitor:
    def time_operation(self, operation_name):
        """Decorator to monitor operation performance"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start = time.time()
                result = func(*args, **kwargs)
                duration = time.time() - start

                if duration > 1.0:  # Log slow operations
                    logger.warning(f"Slow operation: {operation_name} took {duration:.2f}s")

                return result
            return wrapper
        return decorator
```

## Success Metrics

### Performance Targets
- **List operations**: <200ms for 1000 issues
- **Search operations**: <500ms full-text search
- **Memory usage**: <100MB regardless of dataset size
- **Startup time**: <1s even with large datasets

### Scalability Goals
- Support 10,000+ issues without performance degradation
- Linear scaling of storage space only
- Constant time for common operations
- Graceful handling of concurrent access

## Related Issues

- 1fb2b36c: Enhanced init command (should set up performance optimizations)
- 515a927c: Progress tracking (will benefit from fast queries)
- ea4606b6: CI/CD integration (needs efficient data access)

## Risk Mitigation

### Data Safety
- Always keep files as source of truth
- Index is rebuild-able from files
- Atomic operations prevent corruption
- Regular integrity checks

### Backwards Compatibility
- Index is optional enhancement
- Fallback to file-only mode
- No breaking changes to CLI
- Migration is reversible

### Performance Regression
- Monitoring and alerting for slow operations
- A/B testing of optimizations
- Rollback capability if issues arise
- Performance benchmarks in CI/CD

## Future Enhancements

### Advanced Optimizations
- Distributed storage for enterprise scale
- Read replicas for multi-user scenarios
- Advanced query optimization
- Compressed storage for large datasets

### Integration Opportunities
- External database support (PostgreSQL, etc.)
- Cloud storage backends
- Real-time collaboration features
- Advanced analytics and reporting

---
*Created by roadmap CLI*
Assignee: @shanewilkins

---
*Synced from GitHub: #11*
