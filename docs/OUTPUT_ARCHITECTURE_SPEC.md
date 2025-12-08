# Output Architecture Specification
## Metadata-Driven Tables & Structured Output Modes

**Date:** December 8, 2025
**Phase:** 1b-1c Implementation Guide
**Status:** Specification for Review

---

## Executive Summary

This document specifies the architectural approach for implementing structured output modes (Rich, plain-text, JSON, CSV) with metadata-driven tables and filtering/sorting support. It's both a design specification and an implementation guide.

---

## Problem Statement

Current architecture problems:
1. **No separation of data from presentation** - Rich styling hardcoded in commands
2. **No filtering/sorting support** - Tables built with static columns
3. **No machine-readable output** - All output is styled for human display
4. **Test brittleness** - Test output assertions depend on styling
5. **Feature duplication** - Each command rebuilds table logic

---

## Solution Architecture

### Core Classes (roadmap/common/output.py)

#### ColumnDef

Defines metadata for a single column.

```python
class ColumnDef:
    """Metadata for a table column."""

    name: str                    # Column identifier (e.g., "id")
    display_name: str            # Human-readable header (e.g., "ID")
    type: str                    # "string" | "int" | "float" | "date" | "enum" | "bool"
    width: Optional[int]         # Suggested width for display (e.g., 9)
    description: str             # For documentation and help text
    display_style: Optional[str] # Rich style (e.g., "cyan", "bold green") - DISPLAY ONLY
    enum_values: Optional[list]  # For type="enum", list of valid values
    sortable: bool = True        # Can users sort by this column?
    filterable: bool = True      # Can users filter by this column?

    def to_dict(self) -> dict:
        """Export column metadata."""

    @staticmethod
    def from_dict(data: dict) -> "ColumnDef":
        """Import column metadata."""
```

**Example:**
```python
ColumnDef(
    name="id",
    display_name="ID",
    type="string",
    width=9,
    description="Issue identifier",
    display_style="cyan",
    sortable=True,
    filterable=True,
)
```

#### TableData

Contains structured table data with metadata.

```python
class TableData:
    """Structured table data with metadata."""

    columns: list[ColumnDef]     # Column definitions
    rows: list[list]             # Data rows (list of lists)
    title: Optional[str]         # Table title
    description: Optional[str]   # Table description
    filters_applied: dict        # {column_name: filter_value}
    sort_by: list[tuple]         # [(column_name, "asc"|"desc"), ...]
    selected_columns: list[str]  # Column names to display (for --columns)
    total_count: Optional[int]   # Total rows before filtering
    returned_count: Optional[int] # Rows returned after filtering

    def filter(self, column: str, value: Any) -> "TableData":
        """Apply filter and return new TableData."""

    def sort(self, column: str, direction: str) -> "TableData":
        """Apply sort and return new TableData."""

    def select_columns(self, columns: list[str]) -> "TableData":
        """Select specific columns to display."""

    def to_dict(self) -> dict:
        """Export as dictionary (for JSON)."""

    def to_csv(self) -> str:
        """Export as CSV string."""
```

**Example:**
```python
table = TableData(
    columns=[
        ColumnDef(name="id", display_name="ID", type="string", width=9),
        ColumnDef(name="title", display_name="Title", type="string"),
        ColumnDef(name="status", display_name="Status", type="enum", enum_values=["open", "closed"]),
    ],
    rows=[
        ["123", "Fix bug", "open"],
        ["124", "Add feature", "closed"],
    ],
    title="Issues",
)
```

#### OutputFormatter

Handles formatting for all output modes.

```python
class OutputFormatter:
    """Format TableData for different output modes."""

    def __init__(self, table_data: TableData):
        self.table = table_data

    def to_rich(self) -> str:
        """Format as Rich table (with colors, styling)."""
        # Returns Rich Table object (not string) for console.print()

    def to_plain_text(self) -> str:
        """Format as plain ASCII text (POSIX-compliant)."""
        # Returns string suitable for pipes, no ANSI codes
        # Emoji: ✅ → [OK], ❌ → [ERROR], etc.

    def to_json(self) -> str:
        """Format as JSON."""
        # Returns JSON array with headers
        # Example: {"columns": [...], "rows": [...]}

    def to_csv(self) -> str:
        """Format as CSV."""
        # Returns CSV string with headers

    def to_markdown(self) -> str:
        """Format as Markdown table."""
        # Returns Markdown table syntax (future use)
```

### Output Modes

#### 1. Rich Mode (Default, Interactive)

**Trigger:** No flag, or `ROADMAP_OUTPUT_FORMAT=rich` or `--format rich`
**Use case:** Human-facing terminal output with colors and styling
**Features:**
- Colors, bold, styles from ColumnDef.display_style
- Unicode emoji: ✅, ❌, 📋, 🆔, etc.
- Rich table box drawing
- Width-based column sizing
- Pagination for large tables (if using Rich Progress)

**Example output:**
```
┏━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ ID  ┃ Title        ┃ Status ┃
┡━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━┩
│ 123 │ Fix bug      │ open   │
│ 124 │ Add feature  │ closed │
└─────┴──────────────┴────────┘
```

#### 2. Plain-Text Mode (POSIX)

**Trigger:** `ROADMAP_OUTPUT_FORMAT=plain` or `--format plain` or `--plain-text`
**Use case:** Piping to other tools, POSIX compliance
**Features:**
- No ANSI color codes
- No Unicode emoji (replaced with ASCII equivalents)
- ASCII table borders (pipes and dashes)
- Fixed-width columns based on ColumnDef.width
- No styling applied

**Emoji mappings:**
- ✅ → [OK]
- ❌ → [ERROR]
- ⚠️ → [WARN]
- 📋 → [INFO]
- 🆔 → [ID]
- 📊 → [STAT]
- etc.

**Example output:**
```
ID  | Title        | Status
----|--------------|-------
123 | Fix bug      | open
124 | Add feature  | closed
```

#### 3. JSON Mode (Machine-Readable)

**Trigger:** `ROADMAP_OUTPUT_FORMAT=json` or `--json` or `--format json`
**Use case:** Tool integration, scripting, dashboards
**Output format:**
```json
{
  "command": "issue list",
  "timestamp": "2025-12-08T10:30:00Z",
  "columns": [
    {"name": "id", "type": "string", "display_name": "ID"},
    {"name": "title", "type": "string", "display_name": "Title"},
    {"name": "status", "type": "enum", "display_name": "Status"}
  ],
  "rows": [
    ["123", "Fix bug", "open"],
    ["124", "Add feature", "closed"]
  ],
  "metadata": {
    "total": 2,
    "returned": 2,
    "filters_applied": {},
    "sort_by": []
  }
}
```

#### 4. CSV Mode (Data Analysis)

**Trigger:** `ROADMAP_OUTPUT_FORMAT=csv` or `--csv` or `--format csv`
**Use case:** Excel/Sheets analysis, data export
**Output format:**
```csv
ID,Title,Status
123,Fix bug,open
124,Add feature,closed
```

---

## Implementation Phases

### Phase 1b: Core Abstractions (1.5 weeks)

**Goal:** Build ColumnDef, TableData, OutputFormatter classes and basic output modes

**Tasks:**
1. Create `roadmap/common/output.py` with three core classes
2. Implement OutputFormatter methods for all four formats
3. Add emoji mappings for plain-text mode
4. Implement plain-text table builder (ASCII borders)
5. Write unit tests for each format
6. Add environment variable support: `ROADMAP_OUTPUT_FORMAT`

**Deliverables:**
- Core output abstraction classes
- All four format handlers working
- Unit tests (80%+ coverage)
- Documentation with examples

**Success Criteria:**
- ColumnDef and TableData can represent any table structure
- OutputFormatter produces valid output in all formats
- Plain-text mode is POSIX-compliant (no ANSI codes)
- JSON mode is valid, parseable JSON
- CSV mode is RFC4180 compliant

### Phase 1c: Command Integration & Features (1 week)

**Goal:** Update commands to use TableData + OutputFormatter, add CLI flags

**Tasks:**
1. Add CLI flags to all list commands:
   - `--format {rich|plain|json|csv}` (or `-f`)
   - `--plain-text` (shorthand)
   - `--json` (shorthand)
   - `--csv` (shorthand)
2. Update issue list command to use new architecture (pilot)
3. Verify filtering/sorting support in OutputFormatter
4. Update remaining list commands (project, milestone)
5. Test all output formats for all commands
6. Update documentation with examples

**Deliverables:**
- Updated list commands using TableData/OutputFormatter
- CLI flags working correctly
- Integration tests for all output formats
- User documentation with examples

**Success Criteria:**
- All list commands support all four formats
- `--format` flag changes output correctly
- Filtering/sorting can be applied (prep for Phase 1c.2)
- Tests pass with all output formats
- No breaking changes to existing behavior

---

## Implementation Guidelines

### For Service Layer

Services should return TableData instead of complex objects:

**Before:**
```python
def list_issues(core) -> list[Issue]:
    return core.issues.list()
```

**After:**
```python
def get_issues_table(core) -> TableData:
    issues = core.issues.list()
    return TableData(
        columns=[
            ColumnDef("id", "ID", "string", width=9),
            ColumnDef("title", "Title", "string"),
            ColumnDef("status", "Status", "enum", enum_values=["open", "closed"]),
        ],
        rows=[[issue.id, issue.title, issue.status.value] for issue in issues],
        title="Issues",
    )
```

### For Command Layer

Commands should use OutputFormatter to handle display:

**Before:**
```python
@click.command()
def list_issues(ctx):
    issues = IssueService.get_all(ctx.obj["core"])

    table = Table()
    table.add_column("ID", style="cyan")
    table.add_column("Title")

    for issue in issues:
        table.add_row(str(issue.id), issue.title)

    console.print(table)
```

**After:**
```python
@click.command()
@click.option("--format", "-f", type=click.Choice(["rich", "plain", "json", "csv"]),
              default="rich")
@click.option("--json", "output_json", is_flag=True)
def list_issues(ctx, format, output_json):
    output_format = "json" if output_json else format

    table = IssueService.get_issues_table(ctx.obj["core"])
    formatter = OutputFormatter(table)

    if output_format == "json":
        click.echo(formatter.to_json())
    elif output_format == "csv":
        click.echo(formatter.to_csv())
    elif output_format == "plain":
        click.echo(formatter.to_plain_text())
    else:  # rich
        console.print(formatter.to_rich())
```

### For Tests

Tests should assert on structured data, not formatting:

**Before:**
```python
def test_issue_list(runner):
    result = runner.invoke(list_issues)
    assert "ID" in result.output
    assert "[cyan]123[/cyan]" in result.output
```

**After:**
```python
def test_issue_list(runner):
    # Get structured data
    table = IssueService.get_issues_table(core)

    # Assert on data, not formatting
    assert table.rows[0] == ["123", "Fix bug", "open"]
    assert len(table.rows) == 2

    # Test formatting separately
    formatter = OutputFormatter(table)
    json_output = json.loads(formatter.to_json())
    assert json_output["rows"][0] == ["123", "Fix bug", "open"]
```

---

## Filtering & Sorting (Phase 1c.2)

### Filtering

**API:**
```python
table = TableData(...)
filtered = table.filter("status", "open")  # Where status == "open"
filtered = table.filter("priority", ["high", "critical"])  # Where priority IN (...)
```

**CLI:**
```bash
roadmap issue list --filter status=open
roadmap issue list --filter priority=high,critical
```

### Sorting

**API:**
```python
table = TableData(...)
sorted_table = table.sort([("priority", "desc"), ("due_date", "asc")])
```

**CLI:**
```bash
roadmap issue list --sort-by priority:desc,due-date:asc
```

### Column Selection

**API:**
```python
table = TableData(...)
selected = table.select_columns(["id", "title"])  # Only these columns
```

**CLI:**
```bash
roadmap issue list --columns id,title,status
```

---

## Error Handling

Commands should handle format errors gracefully:

```python
try:
    if output_format == "json":
        click.echo(formatter.to_json())
    # ...
except ValueError as e:
    click.echo(f"Error formatting output: {e}", err=True)
    raise SystemExit(1)
```

---

## Environment Variables

| Variable | Values | Example | Purpose |
|----------|--------|---------|---------|
| ROADMAP_OUTPUT_FORMAT | rich, plain, json, csv | `ROADMAP_OUTPUT_FORMAT=json` | Default output format |
| ROADMAP_PLAIN_TEXT | 1, 0, true, false | `ROADMAP_PLAIN_TEXT=1` | Force plain-text (legacy) |
| NO_COLOR | 1, 0, true, false | `NO_COLOR=1` | Disable all colors (standard) |

---

## Migration Strategy

**Order of operations:**
1. Build core abstraction classes (ColumnDef, TableData, OutputFormatter)
2. Refactor `issue list` command (pilot)
3. Add unit/integration tests
4. Refactor other list commands (project, milestone)
5. Add filtering/sorting support
6. Update documentation
7. Announce feature in release notes

**Backwards compatibility:**
- Default output remains Rich (no change visible to users)
- Old `--format` flag may conflict with existing flags (check each command)
- Plain-text mode is opt-in

---

## Testing Strategy

### Unit Tests
- ColumnDef: serialization/deserialization
- TableData: filtering, sorting, column selection
- OutputFormatter: all four format handlers
- Emoji mapping: ✅ → [OK], etc.

### Integration Tests
- `issue list --format json` produces valid JSON
- `issue list --format plain` is POSIX-compliant
- `issue list --format csv` is RFC4180 compliant
- All output modes produce same data (different presentation)
- Filtering works across all output modes
- Sorting works across all output modes

### Manual Tests
- Run `roadmap issue list` (default Rich)
- Run `roadmap issue list --format plain`
- Run `roadmap issue list --json`
- Run `roadmap issue list --csv > issues.csv` (verify in Excel)
- Run `roadmap issue list --json | jq` (verify JSON parsing)

---

## Success Metrics

| Metric | Target | Verification |
|--------|--------|---------------|
| Output formats supported | 4 (Rich, plain, JSON, CSV) | All working, tested |
| Commands using TableData | All list commands (issue, project, milestone) | Refactored |
| Test coverage | ≥85% | Coverage report |
| Backwards compatibility | 100% | No breaking changes |
| Performance | <2s for 1000 issues | Benchmarked |
| POSIX compliance (plain-text) | Yes | No ANSI codes, ASCII emoji |
| JSON validity | RFC 7159 | `jq` can parse it |
| CSV validity | RFC 4180 | Excel can import |

---

**Document Version:** 1.0
**Author:** GitHub Copilot
**Status:** Ready for Implementation Review
