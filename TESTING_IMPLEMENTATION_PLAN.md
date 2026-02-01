# Coverage Gap Analysis & Strategic Playbook

## Current State
- **Coverage**: 78.81% (7,354 tests)
- **Target**: 85%
- **Gap**: 6.2% (~250-300 statements)

## Critical Low Coverage Files (Highest Impact)

### Tier 1: CRITICAL (20-40% coverage) - HIGH VALUE
These are smaller files with major gaps. Easy wins.

1. **remote_state_normalizer.py** - 20% (45 lines, 36 uncovered)
   - Purpose: Normalize remote GitHub state
   - Impact: Core sync functionality
   - Effort: LOW (small file)
   - Expected gain: 0.1-0.15%

2. **missing_headlines_validator.py** - 20% (50 lines, 40 uncovered)
   - Purpose: Validation of issue headlines
   - Impact: Data quality
   - Effort: LOW (small file)
   - Expected gain: 0.1-0.15%

3. **git_hooks_handler.py** - 22% (45 lines, 35 uncovered)
   - Purpose: Git hook installation/management
   - Impact: Git integration
   - Effort: MEDIUM (needs hook mocking)
   - Expected gain: 0.15-0.2%

### Tier 2: IMPORTANT (45-59% coverage)
These have moderate coverage gaps with significant impact.

1. **git_coordinator.py** - 59% (61 lines, 25 uncovered)
   - Purpose: Git operations coordination
   - Impact: Sync & Git integration
   - Effort: MEDIUM
   - Expected gain: 0.15-0.2%

2. **validation_gateway.py** - 56% (18 lines, 8 uncovered)
   - Purpose: Validation orchestration
   - Impact: Data validation
   - Effort: LOW
   - Expected gain: 0.05-0.1%

3. **milestone_consistency_validator.py** - 54% (35 lines, 16 uncovered)
   - Purpose: Milestone validation
   - Impact: Data consistency
   - Effort: MEDIUM
   - Expected gain: 0.1-0.15%

### Tier 3: MODERATE (65-75% coverage)
Moderate gaps in larger files.

1. **analysis/commands.py** - 80% (132 lines, 26 uncovered)
   - Purpose: CLI analysis commands
   - Impact: CLI functionality
   - Effort: MEDIUM-HIGH
   - Expected gain: 0.15-0.2%

2. **hooks_config.py** - 90% (81 lines, 8 uncovered)
   - Purpose: Git hooks configuration
   - Impact: Git integration
   - Effort: LOW
   - Expected gain: 0.05-0.1%

3. **milestone_naming_compliance_fixer.py** - 70% (81 lines, 24 uncovered)
   - Purpose: Milestone naming fixes
   - Impact: Data quality
   - Effort: MEDIUM
   - Expected gain: 0.1-0.15%

## Strategic Attack Plan

### PHASE 8 (Weeks 1-2): Quick Wins
Focus on Tier 1 (small files, big gaps):

**Priority 1**: `remote_state_normalizer.py` + `missing_headlines_validator.py`
- Combined: 90 lines, 76 uncovered statements
- Estimated time: 2-3 hours
- Expected coverage boost: +0.2-0.3%
- Tests to create: ~20-25 tests

**Priority 2**: `git_hooks_handler.py`
- Small but tricky (hook handling)
- Estimated time: 2-3 hours
- Expected coverage boost: +0.15-0.2%
- Tests to create: ~15-20 tests

**Subtotal after Priority 1+2**: ~80.0-80.5% coverage

### PHASE 9 (Weeks 3-4): Medium Impact
Focus on Tier 2 (moderate files, sizable gaps):

**Priority 3**: `git_coordinator.py` + `validation_gateway.py`
- Combined: 79 lines, 33 uncovered statements
- Estimated time: 3-4 hours
- Expected coverage boost: +0.2-0.3%
- Tests to create: ~25-30 tests

**Priority 4**: `milestone_consistency_validator.py`
- Estimated time: 2-3 hours
- Expected coverage boost: +0.1-0.15%
- Tests to create: ~15-20 tests

**Subtotal after Priority 3+4**: ~80.4-80.95% coverage

### PHASE 10 (Weeks 5-6): Balanced Push
Focus on Tier 3 + remaining gaps:

**Priority 5**: `analysis/commands.py` + other CLI commands
- Larger file but well-structured
- Estimated time: 4-5 hours
- Expected coverage boost: +0.2-0.25%
- Tests to create: ~30-40 tests

**Priority 6**: Remaining validation + coordinate files
- Various small gaps across infrastructure
- Estimated time: 3-4 hours
- Expected coverage boost: +0.3-0.4%
- Tests to create: ~30-40 tests

**Subtotal after Priority 5+6**: ~81.2-81.6% coverage

### PHASE 11 (Weeks 7-8): Final Sprint
Target 85% with focused effort on:
- Backend-specific implementations (GitHub/Git adapters)
- Error paths and edge cases
- Integration scenarios

## Test Creation Strategy

### For State Normalizers (20% coverage)
- Test each normalization path
- Test error conditions
- Test edge cases (None values, empty dicts, etc.)
- **Estimate**: 15-20 tests per file

### For Validators (20-54% coverage)
- Test valid scenarios (should pass)
- Test invalid scenarios (should fail)
- Test boundary conditions
- **Estimate**: 15-25 tests per validator

### For Handlers (22% coverage)
- Mock system interactions (hooks, git commands)
- Test success paths
- Test failure paths
- **Estimate**: 15-20 tests per handler

### For Coordinators (59% coverage)
- Test orchestration logic
- Test service delegation
- Test error handling
- **Estimate**: 20-30 tests

## Math to 85%

Current: 78.81% (5,530 covered out of 7,005 total statements)

To reach 85%: Need 5,954 covered statements
- **Gap**: 424 statements needed to cover

With Phase 8-11 approach:
- Phase 8: +50 tests → ~80.3% coverage ✓
- Phase 9: +50 tests → ~80.9% coverage ✓
- Phase 10: +80 tests → ~81.8% coverage ✓
- Phase 11: +100 tests → 85%+ coverage ✓

**Total new tests needed**: ~280-300 tests
**Total time estimate**: 8-10 weeks at current pace
**Bottleneck**: Most gains come from error paths, not happy paths

## Quick Wins THIS WEEK

1. **remote_state_normalizer.py** - 20 tests (2 hours)
   - Test each normalization branch
   - Test error cases
   - Gain: +0.1-0.15%

2. **missing_headlines_validator.py** - 20 tests (2 hours)
   - Test valid/invalid headlines
   - Test edge cases
   - Gain: +0.1-0.15%

3. **validation_gateway.py** - 10 tests (1 hour)
   - Test routing logic
   - Test validator delegation
   - Gain: +0.05-0.1%

**This week's target**: +0.25-0.4% → **79.1-79.2% coverage**

## Why Phase 7 Only Gained 0.03%

Phase 7 tested **APIs & structure**, not **logic paths**:
- YAMLIssueRepository tests hit mostly already-tested list/get methods
- Git commands tests were about decorator existence, not CLI flows
- SyncMergeOrchestrator tests were imports, not actual merge logic
- SyncRetrievalOrchestrator tests were properties, not baseline creation

**Lesson**: Need to target **execution paths**, **error handlers**, and **edge cases** - not just API surface.

## Next Action

Start with `remote_state_normalizer.py` and `missing_headlines_validator.py`.
Those two files alone have 76 uncovered statements in just 90 lines.
Low complexity, high ROI.
