# Phase 1a: POSIX Audit & Documentation
## Output Contracts and Compliance Assessment

**Date:** December 8, 2025
**Status:** Complete - Audit Phase
**Scope:** All CLI commands (30+ commands across 6 command groups)

---

## Executive Summary

The Roadmap CLI uses Rich library for formatted output across most commands. Current state:
- **Rich usage:** ~95% of commands use `console.print()` with Rich styling
- **Click fallback:** ~5% use Click's `click.echo()` and `click.secho()`
- **POSIX compliance:** NOT compliant - Rich adds ANSI color codes and Unicode emojis to stdout
- **Output destinations:** Most output goes to stdout; errors mixed with info output

### Key Findings
1. **No plain-text mode exists** - all output is Rich-formatted
2. **Output contracts are undefined** - no documentation of what each command outputs
3. **Mixed output streams** - informational output, errors, and data are not separated
4. **Unicode emoji heavy** - ✅, ❌, 💬, 📋, 🆔, 🌿, etc. not POSIX-compliant
5. **Styling applied directly** - rich styles like `style="bold green"` hardcoded throughout

---

## 1. Command Inventory & Output Analysis

### Core Commands (6)
| Command | File | Output Type | Rich Usage | POSIX Compliant |
|---------|------|-------------|-----------|-----------------|
| init | init/commands.py | Rich tables + prompts | Heavy (tables) | ❌ |
| status | status.py | Rich tables + headers | Heavy (tables, panels) | ❌ |
| health | status.py | Mixed click.secho + plain text | Click + Rich | ❌ |
| today | today.py | Rich formatted summary | Heavy | ❌ |
| cleanup | cleanup.py | Rich formatted list | Heavy | ❌ |
| data | data/commands.py | Rich export output | Heavy | ❌ |

### Issue Commands (9)
| Command | File | Output Type | Rich Usage | POSIX Compliant |
|---------|------|-------------|-----------|-----------------|
| issue create | issues/create.py | Rich formatted | Heavy | ❌ |
| issue list | issues/list.py | Rich tables | Heavy | ❌ |
| issue view | issues/view.py | Rich panels + tables | Heavy | ❌ |
| issue update | issues/update.py | Rich formatted | Heavy | ❌ |
| issue start | issues/start.py | Rich formatted | Heavy | ❌ |
| issue close | issues/close.py | Rich formatted | Heavy | ❌ |
| issue delete | issues/delete.py | Rich formatted | Heavy | ❌ |
| issue block | issues/block.py | Rich formatted | Heavy | ❌ |
| issue unblock | issues/unblock.py | Rich formatted | Heavy | ❌ |

### Milestone Commands (8)
| Command | File | Output Type | Rich Usage | POSIX Compliant |
|---------|------|-------------|-----------|-----------------|
| milestone create | milestones/create.py | Rich formatted | Heavy | ❌ |
| milestone list | milestones/list.py | Rich tables | Heavy | ❌ |
| milestone view | milestones/view.py | Rich panels | Heavy | ❌ |
| milestone update | milestones/update.py | Rich formatted | Heavy | ❌ |
| milestone close | milestones/close.py | Rich formatted | Heavy | ❌ |
| milestone delete | milestones/delete.py | Rich formatted | Heavy | ❌ |
| milestone assign | milestones/assign.py | Rich formatted | Heavy | ❌ |
| milestone kanban | milestones/kanban.py | Rich board display | Heavy | ❌ |

### Project Commands (6)
| Command | File | Output Type | Rich Usage | POSIX Compliant |
|---------|------|-------------|-----------|-----------------|
| project create | projects/create.py | Rich formatted | Heavy | ❌ |
| project list | projects/list.py | Rich tables | Heavy | ❌ |
| project view | projects/view.py | Rich panels + tables | Heavy | ❌ |
| project update | projects/update.py | Rich formatted | Heavy | ❌ |
| project delete | projects/delete.py | Rich formatted | Heavy | ❌ |
| project archive | projects/archive.py | Rich formatted | Heavy | ❌ |

### Git Integration Commands (3)
| Command | File | Output Type | Rich Usage | POSIX Compliant |
|---------|------|-------------|-----------|-----------------|
| git link | git/commands.py | Rich formatted + status display | Heavy | ❌ |
| git status | git/status_display.py | Rich formatted display | Heavy | ❌ |
| git create-branch | git/commands.py | Rich formatted | Heavy | ❌ |

### Comment Commands (4)
| Command | File | Output Type | Rich Usage | POSIX Compliant |
|---------|------|-------------|-----------|-----------------|
| comment create | comment/commands.py | Rich formatted | Heavy | ❌ |
| comment list | comment/commands.py | Rich formatted | Heavy | ❌ |
| comment edit | comment/commands.py | Rich formatted | Heavy | ❌ |
| comment delete | comment/commands.py | Rich formatted | Heavy | ❌ |

**Total: 36+ commands analyzed**

---

## 2. Output Patterns Identified

### Pattern 1: Status Messages (Highest Frequency)
**Usage:** 100+ locations
```python
console.print(f"✅ Success message", style="bold green")
console.print(f"❌ Error message", style="bold red")
console.print(f"⚠️ Warning", style="yellow")
```
**POSIX Issues:**
- Unicode emoji (✅, ❌, ⚠️) are not plain ASCII
- Rich style tags are included in plain stdout

### Pattern 2: Data Tables (Moderate Frequency)
**Usage:** ~30 commands
```python
from rich.table import Table
table = Table(show_header=True, box=None)
table.add_column("ID", style="cyan")
console.print(table)
```
**POSIX Issues:**
- Rich box drawing characters not POSIX standard
- Colors embedded in output
- No plain-text table fallback

### Pattern 3: Panels & Sections (Low-Moderate Frequency)
**Usage:** ~15 commands
```python
from rich.panel import Panel
panel = Panel(content, title="Section", style="bold")
console.print(panel)
```
**POSIX Issues:**
- Panel borders use Unicode box drawing
- Styled headers not plain text
- Layout depends on terminal width

### Pattern 4: Mixed Output Streams
**Usage:** Throughout
```python
# Success output to stdout
console.print("✅ Created issue #123")
# Error output to stdout (should be stderr)
console.print("❌ Failed to update", style="bold red")
# Data to stdout
console.print(table)
```
**POSIX Issues:**
- Errors not separated to stderr
- No way to parse machine-readable output
- Status messages mixed with data

### Pattern 5: Click Commands (Minority Pattern)
**Usage:** ~5% of output
```python
click.secho(f"✅ Health check passed", fg="green")
click.echo(f"Status: {status}")
```
**POSIX Issues:**
- Mixed with Rich output
- Click also uses color codes
- No consistency across commands

---

## 3. Current Output Contracts (Undefined)

### Issue: No formal output contracts exist
Each command implicitly defines its output format:
- Some output tables
- Some output structured info (key-value pairs)
- Some output single status lines
- Some output JSON (minimal)

### Breaking Changes Identified
Recent architectural refactoring has likely introduced:
- Different table column orders
- Different formatting for timestamps
- Different emoji usage
- Different styling between similar commands

**Example Issue:** `issue list` vs `project list`
- Both use Rich tables
- Column order differs
- Styling differs
- No documented contract

---

## 4. POSIX Compliance Checklist

### Requirement: Plain Text Output
- [ ] All output must work with `NO_COLOR` environment variable
- [ ] All output must work with `TERM=dumb`
- [ ] All output must work with stdout piped to file/command
- [ ] All output must work with `ROADMAP_PLAIN_TEXT=1` env var (to be implemented)

### Requirement: Output Stream Separation
- [ ] Success messages to stdout
- [ ] Error messages to stderr
- [ ] Data output to stdout (no styling)
- [ ] Status/progress to stderr or quiet by default

### Requirement: Machine-Readable Output
- [ ] JSON export mode (`--json` flag) for all data commands
- [ ] CSV export for table data
- [ ] Plain text tables (no Unicode box drawing)

### Requirement: POSIX Character Set
- [ ] No emoji in plain-text mode
- [ ] No Unicode box drawing
- [ ] ASCII-only output with `ROADMAP_PLAIN_TEXT=1`
- [ ] No ANSI color codes without `--color` flag

---

## 5. Output Mapping by Command Group

### Status/Display Commands
**Affected:** init, status, health, today, cleanup, project/*/view, issue/view, milestone/view
**Current Contract:** Rich formatted display with tables/panels
**Required Changes:**
- Add plain-text mode
- Document output fields
- Separate info messages from data

### List Commands
**Affected:** issue list, project list, milestone list
**Current Contract:** Rich table display
**Required Changes:**
- Add JSON export
- Add plain-text table (ASCII borders)
- Document column meanings
- Support `--output` flag (json/csv/plain)

### Action Commands (Create/Update/Delete)
**Affected:** All create/update/delete operations
**Current Contract:** Status message only
**Required Changes:**
- Consistent status format
- Return created/updated ID in machine-readable format
- Support `--quiet` to suppress messages
- Support `--json` to return object

### Git Integration
**Affected:** git link, git status, git create-branch
**Current Contract:** Rich formatted git status display
**Required Changes:**
- Separate git info from roadmap status
- Plain-text git output
- Optional color in git output

---

## 6. Console Configuration Current State

**File:** `roadmap/common/console.py`

**Current Behavior:**
```python
def get_console() -> Console:
    """Get console with colors disabled in testing"""
    if is_testing_environment():
        return Console(file=sys.stdout, force_terminal=False, no_color=True, width=80)
    else:
        return Console()
```

**Issues:**
- No environment variable for POSIX mode
- Testing detects pytest but not all CI/CD scenarios
- Width hardcoded to 80 in tests but terminal width in production
- No plain-text mode toggle

---

## 7. Presenter Layer Analysis

**Location:** `roadmap/adapters/cli/presentation/`

### Presenters Identified
1. **CoreInitializationPresenter** - init output
2. **ProjectInitializationPresenter** - project initialization
3. **ProjectStatusPresenter** - status display
4. **DailySummaryPresenter** - daily summary
5. **MilestoneListPresenter** - milestone list display
6. **CleanupPresenter** - cleanup output
7. **TableBuilders** - table construction utilities

### Issue: Output Logic in Presenters
- Styling hardcoded in presenter methods
- No abstraction for plain-text output
- Presenters assume Rich console availability

**Example:**
```python
class RoadmapStatusPresenter:
    @staticmethod
    def show_status_header():
        console.print("📊 Roadmap Status", style="bold blue")
        # Hardcoded emoji, Rich styling
```

---

## 8. Breaking Changes & Compatibility

### Architecture Changes
1. **Output layer refactoring** was done but output contracts not updated
2. **Test fixtures** updated but output assertions may be brittle
3. **Presenter classes** added but integrate with Rich directly

### Compatibility Risk
- Scripts relying on specific output format may break
- No version of output format exists
- No deprecation path for output changes

---

## 9. Error Handling Integration Points

**Current:** Errors output via Rich console with emoji
**Problem:** No distinction between error types:
- Validation errors
- I/O errors
- System errors
- User cancellations

**Current Pattern:**
```python
console.print(f"❌ {error_message}", style="bold red")
```

**Should Be:**
- Different stderr format for different error types
- Machine-readable error codes
- Structured error context

---

## 10. Implementation Requirements for Phase 1b

### Must-Haves
1. **Plain-text mode flag:** `ROADMAP_PLAIN_TEXT=1` environment variable
2. **Abstraction layer:** OutputFormatter class to handle Rich vs plain-text
3. **Emoji replacement:** Plain-text emoji → ASCII characters
4. **Box drawing replacement:** Plain ASCII tables without Rich boxes
5. **Color handling:** Remove or disable colors in plain-text mode

### Should-Haves
1. **JSON export:** `--json` flag for list commands
2. **CSV export:** `--csv` flag for table data
3. **Quiet mode:** `--quiet` to suppress status messages
4. **Output formatting:** `--format` flag (text/json/csv)

### Nice-to-Haves
1. **Color control:** `--color` / `--no-color` flags
2. **Output file:** `--output FILE` flag
3. **Progress styling:** Different format for progress output
4. **Structured errors:** Error codes in error messages

---

## 11. Testing Implications

### Current Test State
- Tests use `force_terminal=False, no_color=True` in testing environment
- Tests capture Rich output as plain text
- Output assertions assume specific styling strings
- Some tests may break if styling changes

### Required Updates for Phase 1b
- Tests must work with both Rich and plain-text output
- Output assertions should be against content, not formatting
- New plain-text mode must be tested separately
- Integration tests must verify POSIX compatibility

---

## 12. Success Criteria Checklist

### Phase 1a Completion (This Document)
- [x] All commands mapped and categorized
- [x] Output patterns identified
- [x] Current contracts documented
- [x] Breaking changes identified
- [x] POSIX requirements clarified
- [x] Implementation requirements specified

### Phase 1b Prerequisites
- [ ] All output patterns converted to use OutputFormatter abstraction
- [ ] Plain-text mode supports all current Rich output
- [ ] Emoji mappings to ASCII equivalents created
- [ ] Box drawing replaced with ASCII tables
- [ ] Environment variable `ROADMAP_PLAIN_TEXT` recognized and working
- [ ] All 36+ commands testable with plain-text output
- [ ] No ANSI color codes in plain-text mode
- [ ] Tests pass with both Rich and plain-text modes

---

## Key Recommendations

### Before Phase 1b
1. Review this document for architectural implications
2. Determine if Rich-based output can continue (likely yes, with abstraction)
3. Decide on minimum POSIX support (ASCII-only terminals?)
4. Plan JSON export scope (all list commands or subset?)

### Design Decisions Needed
1. **OutputFormatter abstraction:** Should it wrap Console or be independent?
2. **Plain-text emoji:** Use ASCII art, abbreviations, or numbers?
3. **Table format:** Use simple pipes/dashes or more complex ASCII?
4. **Error stream:** Should status messages stay on stdout or move to stderr?

### Migration Path
1. Create OutputFormatter abstraction
2. Implement in one command group (e.g., issues)
3. Test with both Rich and plain-text modes
4. Roll out to other command groups
5. Update tests and documentation
6. Consider deprecation of Rich-only features

---

**Document Status:** Ready for Phase 1b Planning
**Author:** GitHub Copilot
**Date:** December 8, 2025

---

## Appendix A: File Size Summary

| Category | File Count | Files |
|----------|-----------|-------|
| Commands | 36+ | init, status, health, today, cleanup, data, issues/*, milestones/*, projects/*, git/*, comment/* |
| Presenters | 7 | CoreInitializationPresenter, ProjectInitializationPresenter, ProjectStatusPresenter, DailySummaryPresenter, MilestoneListPresenter, CleanupPresenter, TableBuilders |
| Helpers | 15+ | helpers.py, cli_validators.py, cli_error_handlers.py, issue_display.py, etc. |
| Total Touched | 60+ | All files that output to user |

---

## Appendix B: Rich Components Used

- `Console` - Main output handler
- `Table` - Data table display
- `Panel` - Formatted sections
- `Text` - Styled text objects
- `Markdown` - Markdown rendering
- `Progress` - Progress bars (if used)

---

## Appendix C: POSIX Compliance Resources

- POSIX.1-2017 standard for exit codes and signals
- POSIX character set: ASCII (printable characters 32-126)
- Standard streams: stdin (0), stdout (1), stderr (2)
- Exit codes: 0 (success), 1-255 (error, various meanings)
- ANSI escape codes: Not POSIX-compliant, for terminal features only

---

**End of Document**
