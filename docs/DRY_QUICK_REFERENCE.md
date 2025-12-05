# DRY Violations Quick Reference

## 7 Major DRY Violation Clusters

### 🔴 LARGE VIOLATIONS (High Priority)

#### #1: File Enumeration Pattern (5 instances)
**Impact:** 200 LOC | **Effort:** 3-4 hrs
**Solution:** Create `FileEnumerationService`
**Locations:** IssueService, ProjectService, MilestoneService, Validators

#### #2: Validator Class Boilerplate (8 classes)
**Impact:** 400 LOC | **Effort:** 4-5 hrs
**Solution:** Create `BaseValidator` abstract class
**Locations:** infrastructure_validator_service.py, data_integrity_validator_service.py

#### #3: Exception Handling Boilerplate (15+ methods)
**Impact:** 150 LOC | **Effort:** 2-3 hrs
**Solution:** Create `@service_operation` decorator
**Locations:** All service classes

---

### 🟡 MEDIUM VIOLATIONS (Important)

#### #4: Parsing/Serialization Pattern (3 parsers)
**Impact:** 250 LOC | **Effort:** 3-4 hrs
**Solution:** Generic `PydanticYAMLParser`
**Locations:** IssueParser, MilestoneParser, ProjectParser

#### #5: Status Summary Calculations (4 instances)
**Impact:** 50 LOC | **Effort:** 1-2 hrs
**Solution:** `StatusSummary` utility class
**Locations:** HealthCheckService, Validators

#### #6: Test Fixture Duplication (3+ test files)
**Impact:** 100 LOC | **Effort:** 1-2 hrs
**Solution:** Shared `tests/conftest.py`
**Locations:** test_project_service.py, test_health_check_service.py, etc.

#### #7: Filtering Logic Duplication (3 instances)
**Impact:** 80 LOC | **Effort:** 1-2 hrs
**Solution:** `FilterBuilder` utility
**Locations:** IssueService list methods

---

### 🟢 SMALL VIOLATIONS (Nice to Have)

#### #8: String Formatting in Logging (5+ instances)
**Solution:** Logging utility class

#### #9: Path Construction Pattern (3 instances)
**Solution:** `RoadmapPaths` utility

#### #10: Similar get_X methods (3 instances)
**Solution:** Generic getter utility

---

## Implementation Priority Matrix

```
        High Impact
           ↑
        #2 #1 #4
    #3 #5
 #7 #6
        #10 #9 #8
           →
        Low Effort
```

**Recommended Start Order:**
1. **Phase 1 (Foundation - 4-5 hrs):**
   - BaseValidator (#2) → enables validation fixes
   - @service_operation (#3) → enables service fixes
   - FileEnumerationService (#1) → enables service refactoring
   - StatusSummary (#5) → utility

2. **Phase 2 (Validators - 4-5 hrs):**
   - Update all validators to use BaseValidator

3. **Phase 3 (Services - 5-6 hrs):**
   - Refactor services with FileEnumerationService
   - Apply @service_operation decorator
   - Use StatusSummary

4. **Phase 4 (Testing - 3-4 hrs):**
   - Shared test fixtures
   - New utility tests

---

## Code Examples by Violation

### #1: File Enumeration (BEFORE)
```python
def list_issues(self, milestone=None, status=None):
    issues = []
    for issue_file in self.issues_dir.rglob("*.md"):
        try:
            issue = IssueParser.parse_issue_file(issue_file)
            issue.file_path = str(issue_file)

            if milestone and issue.milestone != milestone:
                continue
            if status and issue.status != status:
                continue

            issues.append(issue)
        except Exception as e:
            logger.error("Failed to parse issue", error=str(e))
            continue

    issues.sort(key=lambda x: x.priority)
    return issues
```

### #1: File Enumeration (AFTER)
```python
def list_issues(self, milestone=None, status=None):
    issues = FileEnumerationService.enumerate_and_parse(
        self.issues_dir,
        IssueParser.parse_issue_file
    )
    return (FilterBuilder(issues)
        .where("milestone", milestone)
        .where("status", status)
        .apply())
```

---

### #2: Validator Classes (BEFORE)
```python
class RoadmapDirectoryValidator:
    @staticmethod
    def check_roadmap_directory() -> tuple[str, str]:
        try:
            roadmap_dir = Path(".roadmap")
            if not roadmap_dir.exists():
                return HealthStatus.DEGRADED, "..."
            # ... more logic ...
            return HealthStatus.HEALTHY, "..."
        except Exception as e:
            logger.error("...", error=str(e))
            return HealthStatus.UNHEALTHY, f"..."
```

### #2: Validator Classes (AFTER)
```python
class RoadmapDirectoryValidator(BaseValidator):
    @staticmethod
    def get_check_name() -> str:
        return "roadmap_directory"

    @staticmethod
    def perform_check() -> tuple[str, str]:
        roadmap_dir = Path(".roadmap")
        if not roadmap_dir.exists():
            return HealthStatus.DEGRADED, "..."
        # ... check logic only, no try/except ...
        return HealthStatus.HEALTHY, "..."
```

---

### #3: Exception Handling (BEFORE)
```python
class HealthCheckService:
    def run_all_checks(self):
        try:
            checks = HealthCheck.run_all_checks(self.core)
            logger.debug("health_checks_completed", count=len(checks))
            return checks
        except Exception as e:
            logger.error("health_checks_failed", error=str(e))
            return {}

    def get_overall_status(self, checks=None):
        try:
            if checks is None:
                checks = self.run_all_checks()
            status = HealthCheck.get_overall_status(checks)
            logger.debug("overall_status_calculated", status=status)
            return status
        except Exception as e:
            logger.error("overall_status_failed", error=str(e))
            return HealthStatus.UNHEALTHY
```

### #3: Exception Handling (AFTER)
```python
class HealthCheckService:
    @service_operation(default_return={})
    def run_all_checks(self):
        return HealthCheck.run_all_checks(self.core)

    @service_operation(default_return=HealthStatus.UNHEALTHY)
    def get_overall_status(self, checks=None):
        if checks is None:
            checks = self.run_all_checks()
        return HealthCheck.get_overall_status(checks)
```

---

## Expected Outcomes

**Before Refactoring:**
- 1,230+ lines of duplicate/boilerplate code
- 8 validator classes with identical structure
- 15+ try/except blocks in services
- 3 separate enumeration implementations
- Cyclomatic complexity: 8-12 in many methods

**After Refactoring:**
- ~1,230 lines consolidated (20-25% reduction)
- All validators inherit from BaseValidator
- Exception handling centralized in decorator
- Single FileEnumerationService for all file operations
- Cyclomatic complexity: 4-6 in refactored methods
- Better maintainability and testability

---

## Full Documentation

See detailed analysis in:
- **Analysis:** `docs/DRY_VIOLATIONS_ANALYSIS.md`
- **Implementation:** `docs/DRY_IMPLEMENTATION_PLAN.md`
