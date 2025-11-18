# Roadmap Architecture Decision Document

**Date:** November 18, 2025
**Status:** Approved for v1.0 Refactoring
**Version:** 1.0

## Executive Summary

This document outlines the architectural decisions made for the Roadmap v1.0 codebase refactoring. The goal is to improve code quality, maintainability, and scalability while shipping a lean, focused v1.0 release.

---

## Architectural Decisions

### 1. Architecture Philosophy: Layered Architecture ✅

**Decision:** Implement a **strict layered architecture** with clear separation of concerns.

**Structure:**
```
roadmap/
├── presentation/     (CLI layer - user interface)
├── application/      (Use cases & orchestration)
├── domain/          (Business logic & models)
└── infrastructure/  (External systems: DB, GitHub, Git)
```

**Rationale:**
- Clear separation of concerns makes code easier to test and maintain
- Each layer has a single responsibility
- Dependencies flow downward only (presentation → application → domain → infrastructure)
- Easy to swap implementations (e.g., replace CLI with REST API)
- Scales well as the codebase grows

**Benefits:**
- ✅ Test each layer independently
- ✅ Familiar pattern to Python developers
- ✅ Clear dependency direction
- ✅ Easy to reason about the codebase

---

### 2. CLI Organization: Feature-Based Hierarchy (Option B) ✅

**Decision:** Organize CLI commands by **feature/domain** with one command per file.

**Structure:**
```
roadmap/presentation/cli/
├── __init__.py                  (command registration)
├── issues/
│   ├── __init__.py
│   ├── create.py               (issue creation command)
│   ├── list.py                 (issue listing command)
│   ├── update.py               (issue update command)
│   └── close.py                (issue closing command)
├── milestones/
│   ├── __init__.py
│   ├── create.py
│   ├── list.py
│   └── update.py
├── projects/
│   ├── __init__.py
│   ├── create.py
│   └── list.py
├── progress/
│   ├── __init__.py
│   └── show.py
├── data/
│   ├── __init__.py
│   └── export.py
└── git/
    ├── __init__.py
    └── hooks.py
```

**Rationale:**
- Each command in its own focused file (~100-200 lines)
- Mirrors backend feature structure
- Scales to large CLIs without monolithic files
- Easy to locate and test individual commands
- Clear ownership by feature team

**Benefits:**
- ✅ No more 1196-line CLI files
- ✅ Easy to add new commands
- ✅ Clear feature boundaries
- ✅ Testable in isolation

---

### 3. Shared vs Domain-Specific Code: Centralized Utilities (Option A) ✅

**Decision:** All validation, formatting, and utility code lives in **`shared/`** directory.

**Structure:**
```
roadmap/shared/
├── __init__.py
├── validation.py        (all validators: issue, milestone, project)
├── formatters.py        (output formatting)
├── errors.py            (exception definitions)
├── constants.py         (app constants & enums)
├── logging.py           (logging configuration)
└── utils.py             (misc utilities)
```

**Rationale:**
- Single source of truth for common logic
- Easy to refactor global behavior
- DRY principle - no duplication
- Clear dependency direction (everything can use shared)
- Easier to enforce consistent patterns

**Benefits:**
- ✅ Consistency across features
- ✅ Easier to refactor
- ✅ Clear where common code lives
- ✅ Single point of control

**Trade-offs:**
- Shared folder might grow large over time (acceptable for v1.0)
- Post-v1.0 can consider per-domain validators if needed

---

### 4. External Integrations: Infrastructure Subsystem (Option C) ✅

**Decision:** All external system integrations live in **`infrastructure/`** directory.

**Structure:**
```
roadmap/infrastructure/
├── __init__.py
├── github.py            (GitHub API client)
├── git.py               (Git integration + hooks)
├── storage.py           (Database layer)
└── persistence.py       (State persistence)
```

**Rationale:**
- Clear boundary between "what we do" vs "how we interface with external systems"
- Organized without deep nesting
- Easy to mock for testing
- Easy to swap implementations (e.g., different database)
- Infrastructure is a concern orthogonal to business logic

**Benefits:**
- ✅ All external APIs in one place
- ✅ Easy to add new integrations
- ✅ Clear what's external vs internal
- ✅ Facilitates testing and mocking

---

### 5. Visualization & Large Modules: Full Package (Option B) ✅

**Decision:** Refactor `visualization.py` into a **full package** organized by visualization type.

**Structure:**
```
roadmap/application/visualization/
├── __init__.py              (main export)
├── timeline.py              (timeline visualization: ~500 lines)
├── progress.py              (progress/burndown: ~600 lines)
├── burndown.py              (burndown analysis: ~300 lines)
├── renderers/
│   ├── __init__.py
│   ├── text.py              (ASCII rendering for CLI)
│   ├── json.py              (JSON output for APIs)
│   └── html.py              (HTML rendering - reserved for future)
└── formatters.py            (shared formatting utilities)
```

**Rationale:**
- Breaks 1487-line monolith into focused modules
- Clear structure for adding new chart types
- Renderer pattern enables multiple output formats
- Each file is ~300-600 lines (readable)
- Future-proof for HTML rendering, etc.

**Benefits:**
- ✅ Organized visualization logic
- ✅ Easy to add new chart types
- ✅ Testable components
- ✅ Supports multiple rendering backends

---

### 6. Testing Structure: Hybrid with Unit/Integration Split (Option C) ✅

**Decision:** Organize tests with **unit/integration split** but don't mirror source structure perfectly.

**Structure:**
```
tests/
├── unit/                        (isolated component tests)
│   ├── application/
│   │   ├── test_issue_service.py
│   │   ├── test_milestone_service.py
│   │   └── test_project_service.py
│   ├── domain/
│   │   ├── test_issue_model.py
│   │   ├── test_milestone_model.py
│   │   └── test_project_model.py
│   ├── shared/
│   │   ├── test_validation.py
│   │   ├── test_formatters.py
│   │   └── test_errors.py
│   └── infrastructure/
│       ├── test_github_client.py
│       └── test_storage.py
│
├── integration/                 (component interaction tests)
│   ├── test_cli_issues.py      (CLI + service + storage)
│   ├── test_cli_milestones.py
│   ├── test_github_sync.py     (service + GitHub API)
│   └── test_git_integration.py (service + Git)
│
├── fixtures/
│   ├── conftest.py              (shared fixtures)
│   ├── mock_data.py             (test data)
│   └── factories.py             (object factories)
│
└── pytest.ini
```

**Rationale:**
- Clear unit vs integration distinction
- Easier to run unit tests fast (development)
- Integration tests verify layer interaction
- Flexible organization - not rigid mirroring
- Scales as tests grow

**Benefits:**
- ✅ Fast feedback loop for unit tests
- ✅ Integration tests verify contracts
- ✅ Clear test organization
- ✅ Easy to categorize new tests

---

### 7. Future Expansion: v1.0 Focused (Option B) ✅

**Decision:** Design structure for **current v1.0 needs only**, no speculative future directories.

**Rationale:**
- Avoid over-engineering
- No empty directories waiting for features
- Can add `plugins/`, `reporting/`, etc. post-v1.0
- Current structure supports future extension without refactoring

**In Scope for v1.0:**
- Issues, Milestones, Projects
- GitHub integration
- Git integration
- CLI interface
- Basic visualization

**Out of Scope (post-v1.0):**
- Plugin system
- Advanced reporting
- Multiple integrations (Jira, Linear, etc.)
- REST API
- Web UI

**Benefits:**
- ✅ Ship faster
- ✅ No wasted structure
- ✅ Extensible when needed
- ✅ Clear v1.0 scope

---

### 8. Dev Velocity vs Purity: Pragmatic Approach (Option B) ✅

**Decision:** Prioritize **pragmatism and velocity** over strict architectural purity.

**Rules for v1.0:**
1. **File Size:** No file should exceed 400 lines (split if needed)
2. **Layer Purity:** Strict dependency direction (presentation → application → domain → infrastructure)
3. **Testability:** 80% test coverage minimum for critical paths
4. **Code Quality:** Follow PEP 8, type hints on public APIs
5. **Readability:** Code clarity over clever solutions

**When to Apply Exceptions:**
- Emergency bug fixes (allowed, document with TODO)
- Third-party integrations (allowed if tested)
- Temporary workarounds (allowed if <50 lines and documented)

**Post-v1.0:**
- Strict architectural refactoring
- Eliminate all technical debt
- Optimize for scalability

**Benefits:**
- ✅ Ship v1.0 faster
- ✅ Clear implementation path
- ✅ Flexibility when needed
- ✅ Tech debt acknowledged and plannable

---

## Dependency Direction (Enforced)

```
presentation/cli/        (user interface)
         ↓
    application/         (use cases, services)
         ↓
      domain/            (business logic, models)
         ↓
  infrastructure/        (external systems)

shared/                  (can be used by any layer)
```

**Rule:** Only downward dependencies. No upward or circular dependencies.

---

## Layer Responsibilities

### Presentation Layer (`presentation/`)
- **Responsibility:** User interface (CLI)
- **Owns:** Command definitions, command handlers, user output
- **Depends on:** Application layer
- **Testable:** Via Click's CliRunner

### Application Layer (`application/`)
- **Responsibility:** Use cases and orchestration
- **Owns:** Services (IssueService, MilestoneService), visualization
- **Depends on:** Domain layer, Infrastructure layer
- **Testable:** With mocked infrastructure

### Domain Layer (`domain/`)
- **Responsibility:** Business logic and models
- **Owns:** Issue, Milestone, Project models and their logic
- **Depends on:** Nothing (pure business logic)
- **Testable:** Without mocks

### Infrastructure Layer (`infrastructure/`)
- **Responsibility:** External system communication
- **Owns:** GitHub client, Git integration, database
- **Depends on:** Nothing
- **Testable:** With mocked HTTP/Git calls

### Shared Layer (`shared/`)
- **Responsibility:** Common utilities and patterns
- **Owns:** Validation, formatting, errors, constants
- **Depends on:** Domain layer only
- **Testable:** In isolation

---

## File Size Guidelines

| Layer | Module Type | Ideal Size | Max Size |
|-------|-------------|-----------|----------|
| Presentation | Command handler | 100-150 lines | 200 lines |
| Presentation | Command group | 100 lines | 150 lines |
| Application | Service | 200-300 lines | 400 lines |
| Application | Visualization | 200-400 lines | 600 lines |
| Domain | Model | 100-200 lines | 300 lines |
| Infrastructure | Integration client | 300-500 lines | 800 lines |
| Shared | Validator | 100-200 lines | 300 lines |

**Action:** If a file exceeds max size, break it into smaller files within the same directory.

---

## Module Naming Conventions

| Layer | Convention | Example |
|-------|-----------|---------|
| Presentation | `{feature}_{action}.py` | `issue_create.py`, `milestone_list.py` |
| Application | `{feature}_service.py` | `issue_service.py`, `milestone_service.py` |
| Domain | `{entity}.py` | `issue.py`, `milestone.py`, `project.py` |
| Infrastructure | `{system}.py` | `github.py`, `git.py`, `storage.py` |
| Shared | `{utility}.py` | `validation.py`, `formatters.py`, `errors.py` |

---

## Import Guidelines

**Good (downward dependencies):**
```python
# In presentation/cli/issues/create.py
from application.services.issue_service import IssueService
from shared.validation import validate_issue_title
```

**Good (shared utilities):**
```python
# In application/services/issue_service.py
from shared.errors import ValidationError
from shared.validation import validate_issue_title
```

**BAD (circular dependencies):**
```python
# DON'T DO THIS
# In domain/issue.py
from application.services.issue_service import IssueService  # ❌ CIRCULAR
```

**BAD (upward dependencies):**
```python
# DON'T DO THIS
# In infrastructure/storage.py
from presentation.cli.issues.create import CreateIssueCommand  # ❌ WRONG DIRECTION
```

---

## Success Criteria

✅ All files ≤ 400 lines
✅ Clear layer separation with no circular dependencies
✅ All tests pass (712 unit + integration)
✅ CLI commands all functional
✅ 80% test coverage maintained
✅ No breaking changes to external API
✅ Clear, navigable directory structure
✅ Documentation updated

---

## Appendix: Decision Matrix

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 1 | Architecture | Layered | Clear concerns, testable, familiar |
| 2 | CLI Organization | Feature Hierarchy | Scalable, mirrors backend, ~150 lines per file |
| 3 | Shared Code | Centralized | DRY, consistency, single source of truth |
| 4 | Integrations | Infrastructure Subsystem | Clear boundary, easy mocking |
| 5 | Visualization | Full Package | Organized, renderer pattern, scalable |
| 6 | Tests | Unit/Integration Split | Fast feedback, clear categorization |
| 7 | Future | v1.0 Focused | Ship faster, extend later |
| 8 | Velocity | Pragmatic | Rules + exceptions, tech debt acceptable |

---

**Document Approved:** November 18, 2025
**Next Review:** Post-v1.0 release
