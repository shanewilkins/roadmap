# Domain and Application contracts for 0.2

- Status: Phase 4 target contract
- Date: 2026-08-16
- Decisions: ADR-0001, ADR-0003, ADR-0004, ADR-0008, ADR-0010
- Requirements: TR-003, TR-005, TR-020, TR-021, TR-028, TR-031

## Ownership

`roadmap.domain` contains immutable standard-library value objects, aggregates,
invariants, failure types, and explicit workflow/retention transition tables.
It does not create time, inspect paths, serialize documents, query SQLite, call
Git, log, or know about providers. `roadmap.application` contains immutable
request/response data, stable failure categories, clocks, aggregate-specific
load/save capabilities, the canonical unit-of-work capability, projection
maintenance, and read-only local Git inspection.

The 0.1.1 models and command routes remain active during this contract-only
phase. Later vertical slices translate at the adapter boundary and delete the
legacy implementation after each route switches; they do not make these target
types depend on the legacy models.

## Identity and lifecycle

- Existing Roadmap IDs enter `EntityId` unchanged. New IDs are complete,
  lowercase UUID4 values. Names, titles, paths, workflow, retention,
  relationships, and external references cannot replace or mutate identity.
- Issue, milestone, and project workflow states are separate enums with
  aggregate-specific transition tables. Repeating the current state is
  idempotent. Every other absent edge is rejected.
- Retention is common to all aggregates: `visible -> archived`,
  `archived -> visible`, and `archived -> purged`. Purged is terminal.
- Relationship values contain complete `EntityId` values. Domain rejects
  duplicates and self-links it can see inside one aggregate; Application owns
  existence, uniqueness-in-workspace, and cycle checks that need other
  aggregates.
- All operation times are explicit timezone-aware `Timestamp` inputs supplied
  through the Application clock. No Domain method reads global time.

## Complete 0.1.1 field mapping

The disposition for every field remains governed by CAN-001 through CAN-072 in
`compatibility-inventory-0.2.csv`. This section adds its target owner. A
"canonical envelope" entry is a known, supported document field retained
losslessly while its owning vertical slice defines behavior; it is not an
untyped Domain metadata dictionary. Unknown supported frontmatter is also held
only by the outbound document envelope and round-tripped unchanged.

### Issue

| Inventory | 0.1.1 field | Target representation |
| --- | --- | --- |
| CAN-001 | `id` | `Issue.id: EntityId` |
| CAN-002 | `title` | `Issue.title: Title` |
| CAN-003 | `headline` | `Issue.headline` |
| CAN-004 | `priority` | `Issue.priority: Priority` |
| CAN-005 | `status` | `Issue.status: IssueStatus`; legacy `archived` status maps to retention, not workflow |
| CAN-006 | `archived` | `Issue.retention: RetentionState` |
| CAN-007 | `issue_type` | `Issue.issue_type: IssueType` |
| CAN-008 | `milestone` | `Issue.relations.milestone_id: EntityId`; Phase 9 rewrites the name relation once |
| CAN-009 | `labels` | `Issue.labels` |
| CAN-010 | `remote_ids` | Canonical envelope until Phase 7 converts useful values to ordinary external references; no provider mapping enters Domain |
| CAN-011–CAN-012 | `created`, `updated` | `Issue.created`, `Issue.updated`: `Timestamp` |
| CAN-013–CAN-016 | `assignee`, `content`, `estimated_hours`, `due_date` | `Issue.assignee`, `content`, `estimated_hours`, `due_at` |
| CAN-017–CAN-018 | `depends_on`, `blocks` | `Issue.relations.depends_on`, `blocks`: complete `EntityId` tuples |
| CAN-019–CAN-020 | `actual_start_date`, `actual_end_date` | Canonical envelope; Phase 7 workflow history owns the normalized timestamps |
| CAN-021 | `progress_percentage` | `Issue.progress_percentage`, constrained to 0–100 |
| CAN-022–CAN-024 | `handoff_notes`, `previous_assignee`, `handoff_date` | Canonical envelope; Phase 7 assignment/history behavior owns the normalized values |
| CAN-025–CAN-027 | `git_branches`, `git_commits`, `completed_date` | Canonical envelope; explicit references move through the Phase 7/10 Git boundary and never trigger Domain I/O |
| CAN-028 | `comments` | Canonical envelope; Phase 7 comment/history types own stable identity, authorship, target, reply, and time |
| CAN-029 | `file_path` | Outbound adapter runtime detail; never canonical or Domain data |
| CAN-030 | `github_sync_metadata` | Removed after migration extracts any useful ordinary reference |

### Milestone

| Inventory | 0.1.1 field | Target representation |
| --- | --- | --- |
| CAN-031 | `name` | New stable `Milestone.id: EntityId` plus retained `Milestone.name: Name` |
| CAN-032–CAN-034 | `headline`, `content`, `due_date` | `Milestone.headline`, `content`, `due_at` |
| CAN-035 | `status` | `Milestone.status: MilestoneStatus` |
| CAN-036 | `archived` | `Milestone.retention: RetentionState` |
| CAN-037 | `github_milestone` | Removed after migration extracts any useful ordinary reference |
| CAN-038–CAN-039 | `created`, `updated` | `Milestone.created`, `Milestone.updated`: `Timestamp` |
| CAN-040 | `project_id` | `Milestone.relation.project_id: EntityId` |
| CAN-041–CAN-044 | calculated progress/update/velocity/risk | Derived Application view/projection values; not independently canonical Domain state |
| CAN-045–CAN-047 | actual start/end and comments | Canonical envelope; Phase 8 planning/history behavior owns normalized values |
| CAN-048 | `file_path` | Outbound adapter runtime detail; never canonical or Domain data |

### Project

| Inventory | 0.1.1 field | Target representation |
| --- | --- | --- |
| CAN-049–CAN-050 | `id`, `name` | `Project.id: EntityId`, `Project.name: Name` |
| CAN-051–CAN-055 | headline/content/status/priority/owner | Same-named `Project` fields with typed status and priority |
| CAN-056–CAN-058 | start/target/actual end dates | Canonical envelope; Phase 8 planning behavior owns normalized timestamps |
| CAN-059–CAN-060 | `created`, `updated` | `Project.created`, `Project.updated`: `Timestamp` |
| CAN-061 | `milestones` | `Project.relations.milestone_ids`: unique complete `EntityId` values |
| CAN-062 | `estimated_hours` | `Project.estimated_hours`, constrained positive when present |
| CAN-063–CAN-064 | `actual_hours`, `repo_url` | Canonical envelope; Phase 8 owns actual effort and ordinary external-reference behavior |
| CAN-065–CAN-070 | calculated progress/update/end/variance/velocity/risk | Derived Application view/projection values; not independently canonical Domain state |
| CAN-071 | `comments` | Canonical envelope; Phase 8 planning/history behavior owns normalized comments |
| CAN-072 | `file_path` | Outbound adapter runtime detail; never canonical or Domain data |

Project retention has no trustworthy 0.1.1 model field; a new workspace starts
visible and Phase 9 migration reconciles legacy storage evidence explicitly.
No ordinary read infers or writes retention from a directory.

## Application capability map

The ports are deliberately capability-shaped rather than a generic repository,
backend, gateway, manager, service locator, or universal result:

- `Clock` supplies explicit Domain timestamps.
- `LoadIssue`/`SaveIssue`, `LoadMilestone`/`SaveMilestone`, and
  `LoadProject`/`SaveProject` state the aggregate and operation in their names.
- `UnitOfWork` commits or rolls back an enumerated canonical write set.
- `ProjectionMaintenance` refreshes changed stable IDs or rebuilds disposable
  derived state after canonical work.
- `InspectLocalGit` returns a data-only `GitSnapshot`; it does not fetch, merge,
  push, authenticate, or mutate Roadmap entities.

`IssueDraft`, `MutationReceipt`, and `GitSnapshot` are immutable boundary-neutral
request/response types. Application failures use a small category enum and do
not leak Click exceptions, SQLite errors, parser objects, or provider errors.
