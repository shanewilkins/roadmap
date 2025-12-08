# Quick Reference: Strategic Updates & Next Steps
## December 8, 2025

---

## What Changed

### The Reframing
- **Before:** "Make the CLI POSIX-compliant"
- **After:** "Enable structured output modes for scripting, piping, and tool integration"
- **Impact:** Changes value proposition from compliance to composability

### The Architecture
- **Before:** Rich styling hardcoded in commands, no filtering/sorting support
- **After:** Metadata-driven tables (ColumnDef + TableData) enable multi-format output + filtering/sorting
- **Impact:** Unblocks feature development + improves code quality

### The Timeline
- **Before:** Phase 1 = 2-3 weeks (output only)
- **After:** Phase 1 = 3-4 weeks (output + filtering/sorting)
- **Impact:** +2 weeks upfront, but solves bottleneck and future-proofs architecture

---

## New Documents

| Document | Purpose | Read Time |
|----------|---------|-----------|
| [PHASE_1A_POSIX_AUDIT.md](../PHASE_1A_POSIX_AUDIT.md) | Technical audit of current state | 15 min |
| [OUTPUT_ARCHITECTURE_SPEC.md](../OUTPUT_ARCHITECTURE_SPEC.md) | Implementation guide for Phase 1b-1c | 20 min |
| [PLANNING_UPDATE_2025-12-08.md](./PLANNING_UPDATE_2025-12-08.md) | Strategic refinement summary | 10 min |
| [SESSION_SUMMARY_2025-12-08.md](./SESSION_SUMMARY_2025-12-08.md) | This session's complete work | 15 min |

---

## Updated Documents

| Document | What Changed |
|----------|--------------|
| [V1_0_0_SCOPE.md](./V1_0_0_SCOPE.md) | Added structured output + filtering/sorting as v.1.0.0 features |
| [PHASE_3C_STRATEGIC_ROADMAP.md](./PHASE_3C_STRATEGIC_ROADMAP.md) | Expanded Phase 1, updated all sections for new architecture |

---

## Key Architecture (TL;DR)

### Three Core Classes
```python
# Metadata for a column
ColumnDef(name="id", type="string", width=9, display_style="cyan")

# Structured table data
TableData(columns=[...], rows=[[...], ...])

# Multi-format renderer
OutputFormatter(table_data).to_json()  # JSON export
OutputFormatter(table_data).to_csv()   # CSV export
OutputFormatter(table_data).to_plain() # Plain-text POSIX
OutputFormatter(table_data).to_rich()  # Interactive Rich
```

### Output Modes
| Mode | Use Case | Example |
|------|----------|---------|
| **Rich** (default) | Interactive terminal | Colors, emoji, styling |
| **Plain-text** | Piping, POSIX | ASCII tables, no ANSI codes |
| **JSON** | Tool integration | Machine-readable export |
| **CSV** | Data analysis | Excel/Sheets compatible |

### Filtering/Sorting APIs
```python
# Filtering
table.filter("status", "open")
table.filter("priority", ["high", "critical"])

# Sorting
table.sort([("priority", "desc"), ("due-date", "asc")])

# Column selection
table.select_columns(["id", "title", "status"])
```

---

## Phase Breakdown

### Phase 1a: Output Audit (DONE ✅)
- Audited 36+ commands
- Identified 5 output patterns
- Documented breaking changes
- **Output:** PHASE_1A_POSIX_AUDIT.md

### Phase 1b: Core Abstractions (NEXT)
- Build ColumnDef, TableData, OutputFormatter
- Implement all four output modes
- Refactor pilot command (issue list)
- **Duration:** 1.5 weeks
- **Output:** Specification → OUTPUT_ARCHITECTURE_SPEC.md

### Phase 1c: Features
- Add filtering/sorting/column-selection
- Update all list commands
- Full integration testing
- **Duration:** 1 week
- **Output:** Ready for Phase 2a

---

## Why This Matters

### For v.1.0.0 Release
- Filtering/sorting now included (was blocked)
- JSON/CSV export now available
- Tool integration enabled
- POSIX-compliant plain-text mode available

### For Development
- Solves DRY violations in output layer
- Improves test stability (data vs. presentation)
- Creates reusable OutputFormatter class
- Unblocks filtering feature work

### For Future
- CSV, JSON, plain-text become first-class formats
- Easy to add new formats (HTML, Markdown, etc.)
- Can build web UI on top of same TableData
- Foundation for REST API

---

## Implementation Checklist

### Phase 1b Setup
- [ ] Create `roadmap/common/output.py`
- [ ] Implement ColumnDef class
- [ ] Implement TableData class
- [ ] Implement OutputFormatter class
- [ ] Add emoji mappings (✅ → [OK], etc.)
- [ ] Write unit tests (ColumnDef, TableData, OutputFormatter)

### Phase 1b Pilot (issue list)
- [ ] Refactor IssueService to return TableData
- [ ] Update issue list command to use OutputFormatter
- [ ] Test all four output formats
- [ ] Add CLI flags: --format, --json, --csv, --plain-text
- [ ] Write integration tests

### Phase 1c Expansion
- [ ] Add filtering API to TableData
- [ ] Add sorting API to TableData
- [ ] Add column selection API
- [ ] Update all list commands (project, milestone, etc.)
- [ ] Full integration testing

---

## Testing Strategy

### Unit Tests (Phase 1b)
```
test_column_def.py
test_table_data.py
test_output_formatter.py
  └── test_rich_format()
  └── test_plain_format()
  └── test_json_format()
  └── test_csv_format()
```

### Integration Tests (Phase 1b + 1c)
```
test_issue_list_outputs.py
  └── test_json_output()
  └── test_csv_output()
  └── test_plain_output()
  └── test_filtering()
  └── test_sorting()
  └── test_column_selection()
```

---

## Success Criteria

### Phase 1b ✅
- [ ] All four output formats working
- [ ] Plain-text mode POSIX-compliant
- [ ] JSON and CSV valid and parseable
- [ ] ≥85% test coverage
- [ ] Backwards compatible

### Phase 1c ✅
- [ ] Filtering/sorting work across all formats
- [ ] All list commands support new features
- [ ] Feature parity across command groups
- [ ] Integration tests passing
- [ ] Ready for Phase 2a

---

## Questions?

**Why the extra 2 weeks?**
We're solving the output architecture bottleneck that was blocking features. It's an investment that pays for itself by unblocking filtering/sorting.

**Will this break existing scripts?**
No—default behavior unchanged (Rich format). New modes are opt-in with flags.

**What about backwards compatibility?**
Fully maintained. New commands can use TableData, old ones continue working.

**When do we get filtering/sorting?**
Phase 1c (1 week after Phase 1b), so ~2.5 weeks total from now.

---

## Next Steps

1. **Review** OUTPUT_ARCHITECTURE_SPEC.md for design approval
2. **Begin** Phase 1b with core class implementation
3. **Test** with pilot command (issue list)
4. **Iterate** based on learnings
5. **Expand** to other commands

---

**Updated:** December 8, 2025
**Status:** Ready for Phase 1b Implementation
**Questions/Feedback:** See full documents above
