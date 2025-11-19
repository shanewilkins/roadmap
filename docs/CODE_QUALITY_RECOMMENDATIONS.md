# Code Quality & Stability Recommendations

**Date**: November 19, 2025
**Current State Analysis & Improvement Path**

---

## 📊 Current State Assessment

### Test Coverage: **45.7%** ⚠️

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Overall Coverage | 45.7% | 80%+ | ⚠️ **Needs Improvement** |
| Covered Lines | 4,321 | ~7,500 | ⚠️ **54% gap** |
| Missing Lines | 5,126 | <2,000 | ⚠️ **High** |
| Tests Passing | 757/757 (100%) | 100% | ✅ **Excellent** |

**Key Issues:**
- **CLI layer**: 0% coverage (8 modules completely untested)
- **Presentation layer**: Low coverage (~11%)
- **Infrastructure**: Moderate coverage
- **Domain/Application**: Good coverage

---

### Error Handling: **70% Generic** ⚠️

| Pattern | Count | % of Total | Quality |
|---------|-------|------------|---------|
| Try blocks | 346 | - | ✅ Good |
| Total except clauses | 370 | 100% | - |
| **Bare except:** | **1** | **0.3%** | ⚠️ **Fix immediately** |
| **Generic `except Exception`** | **259** | **70%** | ⚠️ **Too high** |
| **Specific exceptions** | **66** | **18%** | ✅ **Preferred** |

**Problems:**
- 70% using generic `Exception` catching (hard to debug)
- Only 18% using specific exception types
- 1 bare `except:` block (catches everything, including KeyboardInterrupt!)

---

### Logging: **Limited Usage** ⚠️

| Metric | Current | Assessment |
|--------|---------|------------|
| Files using logging | 11/90 (12%) | ⚠️ **Too low** |
| DEBUG statements | 7 | ⚠️ **Very low** |
| INFO statements | 30 | ⚠️ **Low** |
| WARNING statements | 20 | ⚠️ **Low** |
| ERROR statements | 26 | ⚠️ **Low** |
| CRITICAL statements | 0 | ℹ️ **Expected** |

**Issues:**
- Only 12% of files use logging
- Very few DEBUG statements (makes troubleshooting hard)
- No structured logging (harder to parse/analyze)
- Missing correlation IDs or context

---

### Code Documentation: **Mixed** ⚠️

| Metric | Value | Status |
|--------|-------|--------|
| Total docstrings | 1,088 | ✅ Good |
| Python files | 90 | - |
| Functions | 184 | - |
| Classes | 79 | - |
| Type annotations | Good | ✅ Most functions typed |
| TODO/FIXME markers | 0 | ✅ **Excellent!** |

**Observations:**
- Good docstring coverage overall
- Strong type hint usage
- No lingering TODOs (clean!)
- Could improve inline comments for complex logic

---

## 🎯 Improvement Path

### Phase 1: Critical Fixes (1-2 days) 🔥

**Priority 1: Fix Bare Exception**
```python
# Find and fix:
grep -rn "except:" roadmap --include="*.py"

# Replace with specific exception or at minimum:
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise
```

**Priority 2: Add Logging to CLI Layer**
```python
# Every CLI command should log:
logger.info(f"User executed: roadmap {command} {args}")
logger.debug(f"Command context: {context}")
logger.error(f"Command failed: {error}")
```

**Priority 3: Coverage for Critical Paths**
- Test all CLI entry points (currently 0%)
- Test error handling paths
- Test data persistence operations

---

### Phase 2: Foundation Improvements (1 week)

#### 1. Structured Logging Framework

**Goal**: Consistent, parseable logging across all modules

```python
# Create: roadmap/shared/structured_logger.py
import logging
import json
from datetime import datetime
from typing import Any, Dict

class StructuredLogger:
    """Structured logging with context and correlation IDs."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.context: Dict[str, Any] = {}

    def with_context(self, **kwargs) -> 'StructuredLogger':
        """Add context to all log messages."""
        new_logger = StructuredLogger(self.logger.name)
        new_logger.context = {**self.context, **kwargs}
        return new_logger

    def _format_message(self, msg: str, **kwargs) -> str:
        """Format message with context."""
        data = {
            'timestamp': datetime.utcnow().isoformat(),
            'message': msg,
            'context': {**self.context, **kwargs}
        }
        return json.dumps(data)

    def info(self, msg: str, **kwargs):
        self.logger.info(self._format_message(msg, **kwargs))

    # ... debug, warning, error, critical methods
```

**Rollout:**
1. Create structured logger module
2. Update 2-3 modules per day
3. Add correlation IDs for request tracking
4. Configure log rotation and retention

---

#### 2. Exception Hierarchy

**Goal**: Specific, informative exceptions

```python
# Create: roadmap/shared/exceptions.py
class RoadmapError(Exception):
    """Base exception for all roadmap errors."""
    pass

class ValidationError(RoadmapError):
    """Data validation failed."""
    pass

class PersistenceError(RoadmapError):
    """Database/file operations failed."""
    pass

class GitOperationError(RoadmapError):
    """Git operations failed."""
    pass

class GithubAPIError(RoadmapError):
    """GitHub API call failed."""
    pass

class IssueNotFoundError(RoadmapError):
    """Issue does not exist."""
    pass

# Usage example:
try:
    issue = get_issue(issue_id)
except FileNotFoundError as e:
    logger.error(f"Issue file not found: {issue_id}", exc_info=True)
    raise IssueNotFoundError(f"Issue {issue_id} does not exist") from e
```

**Benefits:**
- Easier debugging (know exactly what failed)
- Better error messages for users
- Can catch and handle specific errors
- Maintains error chain with `from e`

---

#### 3. CLI Test Coverage

**Goal**: Test all CLI commands end-to-end

```python
# Example: tests/unit/presentation/cli/test_issue_commands.py
class TestIssueCommands:
    """Test issue CLI commands."""

    def test_create_issue_success(self, cli_runner, temp_roadmap):
        """Test creating an issue via CLI."""
        result = cli_runner.invoke(
            cli, ['issue', 'create', 'Test Issue', '--priority', 'high']
        )
        assert result.exit_code == 0
        assert 'Created issue' in result.output

    def test_create_issue_invalid_priority(self, cli_runner):
        """Test error handling for invalid priority."""
        result = cli_runner.invoke(
            cli, ['issue', 'create', 'Test', '--priority', 'invalid']
        )
        assert result.exit_code != 0
        assert 'Invalid priority' in result.output
```

**Strategy:**
- Use Click's `CliRunner` for testing
- Test happy paths first (quick wins)
- Then test error paths
- Aim for 80% CLI coverage

---

### Phase 3: Advanced Quality (2-3 weeks)

#### 1. Monitoring & Observability

```python
# Add: roadmap/shared/metrics.py
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

@dataclass
class OperationMetric:
    """Track operation performance and success."""
    operation: str
    duration_ms: float
    success: bool
    error: str | None = None
    timestamp: datetime = datetime.utcnow()

class MetricsCollector:
    """Collect and report application metrics."""

    def __init__(self):
        self.metrics: List[OperationMetric] = []

    def record(self, metric: OperationMetric):
        """Record a metric."""
        self.metrics.append(metric)
        logger.debug(f"Metric recorded: {metric}")

    def get_stats(self) -> Dict[str, any]:
        """Get aggregated statistics."""
        return {
            'total_operations': len(self.metrics),
            'success_rate': sum(m.success for m in self.metrics) / len(self.metrics),
            'avg_duration_ms': sum(m.duration_ms for m in self.metrics) / len(self.metrics),
            'errors': [m for m in self.metrics if not m.success]
        }
```

---

#### 2. Health Checks

```python
# Add: roadmap/application/health.py
from typing import Dict, List
from enum import Enum

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

class HealthCheck:
    """Application health checks."""

    @staticmethod
    def check_database() -> tuple[HealthStatus, str]:
        """Check database connectivity."""
        try:
            # Check if .roadmap/state.db exists and is accessible
            db_path = Path(".roadmap/state.db")
            if not db_path.exists():
                return HealthStatus.DEGRADED, "Database not initialized"
            # Try to query
            # ...
            return HealthStatus.HEALTHY, "Database OK"
        except Exception as e:
            return HealthStatus.UNHEALTHY, f"Database error: {e}"

    @staticmethod
    def check_github() -> tuple[HealthStatus, str]:
        """Check GitHub API connectivity."""
        # Test API call
        pass

    @classmethod
    def run_all_checks(cls) -> Dict[str, tuple[HealthStatus, str]]:
        """Run all health checks."""
        return {
            'database': cls.check_database(),
            'github': cls.check_github(),
            # Add more checks
        }
```

**Add CLI command:**
```bash
roadmap health  # Shows health check results
```

---

#### 3. Error Recovery & Retry Logic

```python
# Add: roadmap/shared/retry.py
from functools import wraps
import time
from typing import Callable, Type

def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[Type[Exception], ...] = (Exception,)
):
    """Retry decorator with exponential backoff."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            current_delay = delay

            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        logger.error(
                            f"Failed after {max_attempts} attempts",
                            exc_info=True
                        )
                        raise

                    logger.warning(
                        f"Attempt {attempt} failed, retrying in {current_delay}s",
                        error=str(e)
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff

        return wrapper
    return decorator

# Usage:
@retry(max_attempts=3, exceptions=(GitHubAPIError, RequestException))
def sync_with_github():
    # ... API call that might fail
    pass
```

---

### Phase 4: Continuous Quality (Ongoing)

#### 1. Coverage Requirements

**Add to CI/CD:**
```yaml
# .github/workflows/tests.yml
- name: Check Coverage
  run: |
    poetry run pytest --cov=roadmap --cov-fail-under=80
```

**Coverage goals by layer:**
- Domain: 95%+ (business logic is critical)
- Application: 90%+ (use cases must work)
- Infrastructure: 80%+ (external integrations)
- Presentation/CLI: 80%+ (user-facing)
- Shared: 90%+ (utilities used everywhere)

---

#### 2. Code Quality Metrics

**Add tools:**
```bash
# Install
poetry add --group dev radon complexity-report

# Run complexity analysis
radon cc roadmap -a -nb  # Cyclomatic complexity
radon mi roadmap -nb     # Maintainability index

# Fail builds on high complexity
radon cc roadmap --min B --max F
```

**Set standards:**
- Cyclomatic complexity: < 10 per function
- Maintainability index: > 65 (B grade or better)
- Max function length: 50 lines
- Max file length: 500 lines

---

#### 3. Automated Quality Gates

**pre-commit hooks:**
```yaml
# .pre-commit-config.yaml additions
  - repo: local
    hooks:
      - id: check-coverage
        name: Check test coverage
        entry: poetry run pytest --cov=roadmap --cov-fail-under=80 -q
        language: system
        pass_filenames: false

      - id: check-complexity
        name: Check code complexity
        entry: poetry run radon cc roadmap --min B
        language: system
        pass_filenames: false
```

---

## 📋 Implementation Checklist

### Week 1: Critical Fixes
- [ ] Fix bare exception block
- [ ] Add structured logger module
- [ ] Create exception hierarchy
- [ ] Add logging to top 5 CLI commands
- [ ] Write tests for CLI commands (reach 30% coverage)

### Week 2: Foundation
- [ ] Replace all generic `Exception` with specific types (50% goal)
- [ ] Add logging to all CLI commands
- [ ] Add logging to infrastructure layer
- [ ] CLI test coverage to 60%
- [ ] Add health check system

### Week 3: Quality Tools
- [ ] Add metrics collection
- [ ] Implement retry logic for GitHub API
- [ ] Add complexity checking to CI
- [ ] Coverage to 70%
- [ ] Documentation for error handling patterns

### Week 4: Polish & Automation
- [ ] Coverage to 80%
- [ ] All remaining `Exception` to specific types
- [ ] Automated quality gates in CI
- [ ] Monitoring dashboard (if needed)
- [ ] Team training on new patterns

---

## 🎯 Success Metrics

| Metric | Current | Target (1 Month) | Target (3 Months) |
|--------|---------|------------------|-------------------|
| Test Coverage | 45.7% | 80% | 90% |
| CLI Coverage | 0% | 80% | 90% |
| Specific Exceptions | 18% | 60% | 90% |
| Modules with Logging | 12% | 50% | 90% |
| Bare Excepts | 1 | 0 | 0 |
| Health Checks | 0 | 5 | 10 |
| Tests Passing | 100% | 100% | 100% |

---

## 💡 Quick Wins (Do These First!)

1. **Fix the bare except** (5 minutes)
   ```bash
   grep -rn "except:" roadmap --include="*.py"
   ```

2. **Add logging to CLI entry point** (30 minutes)
   ```python
   # In cli/__init__.py or main CLI file
   logger.info(f"Command executed: {ctx.invoked_subcommand}")
   ```

3. **Create exception hierarchy** (1 hour)
   - Define base exceptions
   - Update 2-3 modules to use them

4. **Test one CLI command** (2 hours)
   - Pick simplest command
   - Write happy path test
   - Write error path test

5. **Set up coverage in CI** (1 hour)
   - Add coverage check to workflow
   - Set initial threshold at 45% (current)
   - Increase by 5% each week

---

## 📚 Resources & Tools

### Recommended Tools
- **Coverage**: `pytest-cov` (already installed)
- **Complexity**: `radon`, `mccabe`
- **Logging**: `structlog` (structured logging)
- **Monitoring**: `prometheus_client` (if needed)
- **Error tracking**: `sentry-sdk` (optional)

### Documentation to Create
1. Error handling guidelines
2. Logging standards
3. Testing patterns
4. Troubleshooting guide

---

## 🚀 Expected Outcomes

**After 1 Month:**
- 80% test coverage
- Structured logging across all modules
- Specific exception types in use
- Health checks in place
- Easier debugging and maintenance

**After 3 Months:**
- 90% test coverage
- Comprehensive monitoring
- Near-zero generic exceptions
- Automated quality enforcement
- Strong foundation for scale

**Long-term Benefits:**
- Faster debugging (good logs + specific errors)
- Fewer production issues (high test coverage)
- Easier onboarding (clear patterns)
- Confident refactoring (tests protect you)
- Better user experience (clear error messages)

---

**Next Steps**: Start with the Quick Wins section, then proceed through Phase 1. This is an incremental approach that shows progress quickly while building toward comprehensive quality.
