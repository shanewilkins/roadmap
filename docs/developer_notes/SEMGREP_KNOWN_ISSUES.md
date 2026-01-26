# Known Issues: Semgrep + Import-Linter Dependency Conflict

## Dependency Conflict (Active)

We can't use the latest semgrep or import-linter, because import-linter>2.6 requires rich > 14, and semgrep requires rich = 13.5. Hopefully semgrep will update to latest rich soon.

## Completion Status (January 26, 2026)

✅ **All Semgrep violations have been resolved!**

**Final Metrics:**
- Started with: 115 violations across 12 rules
- Fixed phases:
  - Phase 1: Fixed 36 event-name violations (f-strings → static with context)
  - Phase 2: Fixed 7 silent-pass/silent-return violations
  - Phase 3: Fixed 4 remaining silent-pass violations  
  - Phase 4: Fixed 4 silent-return violations in credentials.py
  - Phase 5: Fixed 12 remaining violations (event names, exc_info, severity)
- Ended with: **0 violations** (100% compliance)

**Key Accomplishments:**
1. All exception handlers now log before silent exits
2. All logger calls use structured logging with event names
3. All error logs include severity categorization
4. All warning logs on silent returns are properly logged
5. No exc_info=True on non-error log levels

See `SEMGREP_RULES.md` for detailed reference on each rule. 
