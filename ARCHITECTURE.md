# Architecture & Dependency Rules

**Established**: Phase 1 Refactoring, December 16, 2025

## Layered Architecture

```
┌─────────────────────────────────────────────────┐
│         CLI/Adapters (Click, Formatters)        │
│              (User Interface Layer)              │
└────────────────────┬────────────────────────────┘
                     │ depends on
                     ▼
┌─────────────────────────────────────────────────┐
│           Core Services & Orchestration          │
│         (Business Logic Coordination)            │
└────────────────────┬────────────────────────────┘
                     │ depends on
                     ▼
┌─────────────────────────────────────────────────┐
│      Domain Layer (Abstract Interfaces)          │
│        (IssueRepository, ProjectRepository)      │
└────────────────────┬────────────────────────────┘
                     │ implemented by
                     ▼
┌─────────────────────────────────────────────────┐
│  Infrastructure (Database, Git, Persistence)    │
│            (Implementation Details)              │
└─────────────────────────────────────────────────┘
```

## Dependency Rules

### ✅ ALLOWED Dependencies
- **Adapters → Core Services**: CLI commands call service layer
- **Adapters → Domain Models**: Adapters work with domain entities
- **Core Services → Domain Abstractions**: Services depend on interfaces
- **Infrastructure → Domain Abstractions**: Infrastructure implements interfaces
- **Adapters → Infrastructure**: Direct for UI-specific operations (file display, etc.)

### ❌ PROHIBITED Dependencies
- **Core → Infrastructure**: Services MUST NOT import from infrastructure directly
- **Domain → Infrastructure/Core**: Domain is pure, no framework dependencies
- **Infrastructure → Adapters**: Infrastructure doesn't depend on UI layer
- **Domain → Adapters**: Domain doesn't depend on UI

## Implementation Locations

| Layer | Location | Purpose |
|-------|----------|---------|
| **Domain** | `roadmap/domain/` | Abstract interfaces, business models, value objects |
| **Core** | `roadmap/core/services/` | Business logic orchestration |
| **Adapters** | `roadmap/adapters/` | CLI, formatters, presenters (UI layer) |
| **Infrastructure** | `roadmap/infrastructure/` | Persistence, external integrations |
| **Common** | `roadmap/common/` | Utilities, shared logic (no layer dependencies) |

## Repository Pattern

### Abstract Interfaces (domain layer)
Located in `roadmap/domain/repositories/`:
- `IssueRepository` - Issue persistence contract
- `ProjectRepository` - Project persistence contract
- `MilestoneRepository` - Milestone persistence contract

Services depend ONLY on these interfaces, never on concrete implementations.

### Concrete Implementations (infrastructure layer)
Located in `roadmap/infrastructure/`:
- File-based repositories
- Database repositories
- Git integration repositories

### Usage Pattern
```python
# ✅ CORRECT - Core service depends on abstract interface
class IssueService:
    def __init__(self, repository: IssueRepository):
        self.repository = repository  # Injected abstraction

# ❌ WRONG - Direct import of infrastructure
class IssueService:
    def __init__(self):
        from infrastructure.issue_repository import IssueRepositoryImpl
        self.repository = IssueRepositoryImpl()  # Tightly coupled
```

## Dependency Injection

Services receive dependencies through constructor injection:

```python
# Service receives what it needs
service = IssueService(
    repository=issue_repository,
    state_manager=state_manager,
    coordinator=coordinator
)
```

Benefits:
- Testable: Easy to inject mocks
- Flexible: Can swap implementations
- Decoupled: Services don't know about infrastructure
- Clear: Dependencies visible in constructor

## Forbidden Patterns (Anti-patterns)

### 1. Service Locator Pattern
```python
# ❌ WRONG
class IssueService:
    def get_repository(self):
        from infrastructure.issue_repository import repo
        return repo  # Service discovers dependency at runtime
```

### 2. Direct Infrastructure Import
```python
# ❌ WRONG
from roadmap.infrastructure.issue_operations import IssueOperations

class IssueService:
    def __init__(self):
        self.ops = IssueOperations()  # Tightly coupled
```

### 3. Circular Dependencies
```python
# ❌ WRONG
# infrastructure/repo.py imports from core/service.py
# core/service.py imports from infrastructure/repo.py
# This creates unresolvable circular dependency
```

## Common Imports by Layer

### In Core Services
```python
# ✅ ALLOWED
from domain.models import Issue, Project
from domain.repositories import IssueRepository
from common.logging import get_logger
from shared.constants import STATUS_ACTIVE

# ❌ NOT ALLOWED
from infrastructure.issue_operations import IssueOperations
from adapters.persistence import StorageManager
```

### In Adapters/CLI
```python
# ✅ ALLOWED
from core.services import IssueService
from domain.models import Issue
from adapters.formatters import format_issue
from common.output_formatter import print_table

# ❌ NOT ALLOWED (generally)
from infrastructure.database import Database
# Exception: Direct infrastructure for UI operations is OK
from infrastructure.logging import setup_logger
```

### In Infrastructure
```python
# ✅ ALLOWED
from domain.models import Issue
from domain.repositories import IssueRepository
from common.logging import get_logger

# ❌ NOT ALLOWED
from adapters.cli import click_command
from core.services import IssueService
```

## Migration Path

For existing violations:
1. Create abstract interface in `domain/repositories/`
2. Keep existing implementation in `infrastructure/`
3. Gradually inject abstract interface into services
4. Remove direct imports of infrastructure classes
5. Update tests to inject mock implementations

## Testing Strategy

### Unit Testing Services
```python
# Inject mock repository
mock_repo = MagicMock(spec=IssueRepository)
service = IssueService(repository=mock_repo)
# Test service logic in isolation
```

### Integration Testing
```python
# Use real infrastructure implementations
repo = IssueRepositoryImpl()
service = IssueService(repository=repo)
# Test full flow with real storage
```

## Files Modified for Phase 1

- Created `roadmap/domain/repositories/__init__.py`
- Created `roadmap/domain/repositories/issue_repository.py`
- Created `roadmap/domain/repositories/project_repository.py`
- Created `roadmap/domain/repositories/milestone_repository.py`
- Created `ARCHITECTURE.md` (this file)

## Next Steps (Phase 2+)

1. Update services to accept repositories via constructor
2. Create concrete implementations in infrastructure
3. Update tests to inject mock repositories
4. Remove direct infrastructure imports from services
5. Add dependency container/factory for initialization
