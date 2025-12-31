# Milestone Naming Conventions

## Overview

This document defines the naming conventions for milestones in the Roadmap project. Clear, consistent naming prevents errors, confusion, and makes the CLI tool more reliable.

## Problem: Why Naming Conventions Matter

The roadmap system stores:
1. **Milestone display names** - Used by humans (e.g., "v0-8-0", "Sprint 1")
2. **Safe milestone filenames** - Used by the filesystem (e.g., "v0-8-0", "sprint-1")

**The Problem:** When display names don't follow a consistent pattern, they get converted to different safe names, causing:
- Issues assigned to "v.0.8.0" but file is "v0-8-0.md" → **CLI lookup fails**
- Issues with "Future (Post-v1.0)" but folder is "future-post-v10" → **Mismatches**
- Multiple display names for same version → **Confusion**

## Solution: Unified Naming

**The Rule:** Use the safe name directly as the display name.

This means:
- **NO conversion needed** (display name = filesystem name)
- **NO confusion** (what you see is what you get)
- **NO lookup failures** (names always match)

## Approved Naming Patterns

### 1. Version Releases

**Pattern:** `v{major}-{minor}-{patch}` (hyphens, no ambiguity)

**Examples:**
- ✅ `v0-7-0` (for v0.7.0 release)
- ✅ `v0-8-0` (for v0.8.0 release)
- ✅ `v1-0-0` (for v1.0.0 release)
- ✅ `v2-0-0` (for v2.0.0 release)

**Why:** Hyphens are filesystem-safe and unambiguous. `v100` could mean v1.0.0 or v10.0, so we use `v1-0-0` instead.

### 2. Sprint-Based Development

**Pattern:** `sprint-{identifier}` (lowercase, hyphen-separated)

**Examples:**
- ✅ `sprint-1` (first sprint)
- ✅ `sprint-q1-2025` (Q1 2025 sprint)
- ✅ `sprint-january` (named sprint)

**Why:** Hyphens are safe for filenames and are convention in web development.

### 3. Development Phases

**Pattern:** `phase-{identifier}` (lowercase, hyphen-separated)

**Examples:**
- ✅ `phase-alpha`
- ✅ `phase-beta`
- ✅ `phase-1`
- ✅ `phase-mvp`

### 4. Release Planning

**Pattern:** `release-{identifier}` (lowercase, hyphen-separated)

**Examples:**
- ✅ `release-dec-2025` (specific month)
- ✅ `release-2025-q2` (specific quarter)
- ✅ `release-holiday` (named release)

### 5. Special Collections

**Pattern:** `{descriptor}` (lowercase, hyphen-separated)

**Examples:**
- ✅ `backlog` (unscheduled work)
- ✅ `future-post-v1-0` (far future work)
- ✅ `experimental` (experimental features)
- ✅ `deprecated` (deprecated features)

## Character Rules

### Allowed Characters
- **Alphanumeric:** a-z, A-Z, 0-9
- **Separators:** hyphens (`-`), underscores (`_`), dots (`.`) - but use sparingly
- **Length:** 1-100 characters

### Forbidden Characters
- ❌ Spaces (use hyphens instead)
- ❌ Parentheses (e.g., "Future (Post-v1.0)")
- ❌ Dots (except in version patterns like "v1.0.0" in display names, but NOT in filenames)
- ❌ Forward/backward slashes
- ❌ Special symbols (@, #, $, %, &, etc.)

### Invalid Examples
- ❌ `v.0.8.0` (dots in filename)
- ❌ `Future (Post-v1.0)` (parentheses)
- ❌ `Q1/2025` (forward slash)
- ❌ `Sprint #1` (hash symbol)
- ❌ `v0_8_0` (underscores for version numbers)

## Migration Guide

### If You See Display Names Like...

| Display Name | Should Be | Action |
|---|---|---|
| `v.0.7.0` | `v0-7-0` | Update issue metadata |
| `v.0.8.0` | `v0-8-0` | Update issue metadata |
| `v.0.9.0` | `v0-9-0` | Update issue metadata |
| `v.1.0.0` | `v1-0-0` | Update issue metadata |
| `Future (Post-v1.0)` | `future-post-v10` | Update issue metadata |
| `Development` | `backlog` | Update issue metadata |
| (empty string) | `backlog` | Update issue metadata |

### Automated Fix
Run the health check to automatically convert all non-compliant names:

```bash
roadmap health fix --fix-type milestone_naming_compliance
```

This will:
1. **Scan** all issues for non-compliant milestone names
2. **Convert** display names to safe equivalents
3. **Update** issue metadata automatically

## Why These Rules?

1. **Filesystem Compatibility:** Safe names work with any filesystem (Windows, Mac, Linux)
2. **URI Compatibility:** Names are URL-safe without encoding
3. **CLI Simplicity:** No conversion confusion - what you type is what you get
4. **Git Friendliness:** Works perfectly with Git without special escaping
5. **Human Readability:** Clear at a glance what the milestone represents

## Creating New Milestones

When creating a new milestone, use the `roadmap milestone create` command. It will:

1. ✅ **Validate** your name against these conventions
2. ✅ **Suggest** the safe filename version
3. ✅ **Create** both the display name and file correctly

Example:
```bash
roadmap milestone create "v0-8-0" --description "Version 0.8.0 release"
```

The system will:
- Use `v0-8-0` as the display name
- Create file as `v0-8-0.md`
- Warn if names don't match these conventions

## Questions?

If you have questions about milestone naming, check:
- `.roadmap/milestones/` - See actual milestone file names
- `roadmap milestone list` - See all current milestones
- `.roadmap/issues/` - See issue organizations by milestone

## Current Compliant Milestones

- ✅ `backlog` - Unscheduled work
- ✅ `v0-7-0` - Version 0.7.0
- ✅ `v0-8-0` - Version 0.8.0
- ✅ `v0-9-0` - Version 0.9.0
- ✅ `v1-0-0` - Version 1.0.0
- ✅ `future-post-v1-0` - Future work beyond v1.0

---

**Last Updated:** December 26, 2024
**Version:** 1.0
