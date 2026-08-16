# Retired milestone synchronization

Provider milestone synchronization is not part of Roadmap 0.2. The complex
remote dependency ordering and reconciliation described here before Phase 1
belonged to an experimental 0.1.1 subsystem and is scheduled for removal.

Roadmap continues to support local milestone planning:

```bash
roadmap milestone create --title "0.2" --due-date 2026-09-30
roadmap milestone assign <issue-id> "0.2"
roadmap milestone view "0.2"
roadmap milestone recalculate "0.2"
```

Share those canonical changes through ordinary Git. See
[Supported workflows](WORKFLOWS.md) and the
[0.2 public contract](../architecture/public-contract-0.2.md).
