# Requirements as First-Class Artifacts

**Decision status:** Draft
**Recommendation:** Adopt after the core stabilization gate, using a small
optional requirements domain that links intent to delivery work.

## Recommendation

Roadmap should support user and technical requirements as first-class,
repository-native artifacts. This is a natural extension of “project management
as code”: requirements are durable intent, issues are implementation work,
milestones schedule delivery, and projects or roadmaps communicate investment.

The feature should not turn Roadmap into a heavyweight requirements-management
suite. The first release should focus on stable identifiers, lifecycle,
traceability, verification evidence, and CSV interchange.

## Product boundary

| Artifact | Answers | Lifecycle role |
| --- | --- | --- |
| Requirement | What outcome or constraint must be satisfied, and why? | Governed intent and acceptance evidence. |
| Issue | What work will change the product? | Executable implementation task. |
| Milestone | When will related work be delivered? | Delivery grouping and progress. |
| Project / roadmap | Why are we investing and in what sequence? | Strategic grouping and communication. |

Requirements must remain optional. Existing repositories that only need issues
and milestones should not gain extra ceremony or required files.

## Canonical storage

The canonical format should match the existing file-first model:

```text
.roadmap/
└── requirements/
    ├── user/
    │   └── UR-001.md
    └── technical/
        └── TR-001.md
```

CSV should be an import/export and bulk-review format, not the canonical store.
One Markdown file per requirement reduces merge contention, preserves readable
history, and leaves space for rationale and verification evidence.

Suggested frontmatter:

```yaml
---
id: UR-001
type: user
title: Initialize a repository
statement: The CLI shall initialize a repository-local Roadmap workspace.
journey_id: J-01
stage: Initialize
priority: must
status: accepted
owner: maintainer
acceptance_criteria:
  - A new repository can be initialized without partial state.
relations:
  depends_on: []
  derived_from: []
  satisfied_by: [issue-abc123]
  verified_by: [test-init-clean-repository]
supersedes: []
created_at: 2026-08-09T00:00:00Z
updated_at: 2026-08-09T00:00:00Z
---
```

Technical requirements use the same envelope with `type: technical`,
`verification`, and `supports` relations to user requirements.

## Lifecycle

Use the existing governed states:

```text
Draft → Accepted → In Progress → Verified
  └──────────────→ Deferred
  └──────────────→ Rejected
```

- Only `Accepted` requirements are eligible for roadmap commitment.
- `In Progress` is derived from or reconciled with linked active work.
- `Verified` requires recorded evidence; closing an issue is not sufficient.
- Meaningful changes to an accepted requirement are reviewable and retain
  history.
- Superseded requirements remain addressable and link to replacements.

## Typed relationships

The graph should support these initial relationships:

- `depends_on`: requirement sequencing or prerequisite.
- `derived_from`: technical requirement derived from a user requirement or
  decision.
- `supports`: technical requirement supporting one or more user requirements.
- `satisfied_by`: issue, milestone, or external work item implementing it.
- `verified_by`: test, review, document, or evidence artifact.
- `supersedes`: replacement of an older requirement.

Relationships must be validated for missing targets, invalid types, duplicate
edges, and cycles where cycles are not meaningful.

## Minimum CLI journey

```text
roadmap requirement create --type user --title "..."
roadmap requirement list --journey J-01 --status accepted
roadmap requirement view UR-001
roadmap requirement update UR-001 --status accepted
roadmap requirement link UR-001 --satisfied-by issue-abc123
roadmap requirement verify UR-001 --evidence tests/test_init.py
roadmap requirement coverage --milestone v0-2-0
roadmap requirement export --format csv
roadmap requirement import requirements.csv --dry-run
```

Every mutating command needs dry-run or confirmation when it can overwrite,
supersede, bulk-link, or change governed status.

## Traceability views

The first useful views are:

1. Accepted requirements with no planned work.
2. In-progress work with no linked requirement.
3. Completed work whose requirement is not verified.
4. Requirements with missing dependencies or evidence.
5. Milestone coverage by user journey and priority.
6. Technical requirements supporting each user requirement.

Coverage means “linked and evidenced,” not merely “a row exists.” Roadmap should
show gaps without inventing or auto-approving links.

## Delivery sequence

### Phase 0 — governance and schema

- Triage the CSV registers and approve the artifact boundary.
- Define identifiers, fields, lifecycle, relation semantics, and migrations.
- Add acceptance tests for round-trip serialization and invalid graphs.

### Phase 1 — local artifact management

- Create, list, view, update, archive, and supersede requirements.
- Validate files and relationships through health checks.
- Import/export CSV with dry-run, conflict reporting, and round-trip fidelity.

### Phase 2 — delivery traceability

- Link requirements to issues, milestones, projects, tests, and evidence.
- Add coverage and orphan reports.
- Reconcile lifecycle without silently changing governed states.

### Phase 3 — optional remote interoperability

- Export traceability reports for GitHub and CI.
- Consider remote sync only after local semantics are stable. Requirements must
  not be flattened into GitHub issues by default.

## Risks and controls

| Risk | Control |
| --- | --- |
| Requirements duplicate issues | Enforce the product boundary and typed links. |
| Process becomes heavyweight | Keep the domain optional; support a minimal schema and sensible defaults. |
| CSV and Markdown diverge | Make Markdown canonical and CSV transactional import/export. |
| Status changes become misleading | Require explicit governance actions and evidence for verification. |
| Traceability becomes stale | Add health checks and coverage reports; never fabricate links. |
| More scope before core stability | Do not implement until packaging, data-safety, and quality-gate blockers are resolved. |

## Decision criteria

Accept this proposal if the project wants to differentiate on end-to-end
requirements-to-delivery traceability and is willing to keep the feature small.
Defer it if the next release cannot first prove safe local storage, a working
installed CLI, and enforceable quality gates.
