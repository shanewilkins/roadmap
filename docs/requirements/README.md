# Requirements Register

This directory is the product and engineering input to the development
roadmap. The initial 0.2 scope was triaged on 2026-08-16. `Accepted` means approved
scope, not delivered behavior. Selected implemented requirements now have scoped
verification records; postponed directions remain `Deferred`. Read the status
and evidence, not the roadmap target alone, to determine delivery.

## Files

- [user-requirements.csv](user-requirements.csv) records user outcomes and
  observable acceptance criteria.
- [technical-requirements.csv](technical-requirements.csv) records system
  constraints, rationale, and verification methods.
- [Requirements as First-Class Artifacts](REQUIREMENTS_AS_ARTIFACTS.md) records the reconciled product and architecture direction for managing these records in
  Roadmap itself.
- [Phase 1 requirements triage](phase-1-triage-2026-08-16.md) records the
  accepted scope, deferrals, counts, and scheduling rationale.

The registers use CSV so they remain diffable, scriptable, and easy to import
into Roadmap CLI or a spreadsheet. UTF-8 and RFC 4180-compatible quoting are
required.

## Shared fields

| Field | Rule |
| --- | --- |
| `id` | Stable identifier: `UR-###` for user requirements or `TR-###` for technical requirements. Never reuse an ID. |
| `title` | Short, unique summary. |
| `requirement` | One testable statement using `shall`. |
| `priority` | `Must`, `Should`, or `Could`. Priority is provisional while status is `Draft`. |
| `status` | `Draft`, `Accepted`, `In Progress`, `Verified`, `Deferred`, or `Rejected`. |
| `owner` | Accountable person or role; use `Maintainer` until explicitly delegated. |
| `source` | Repository evidence or decision record supporting the row. Multiple paths use `; `. |
| `roadmap_target` | Planned milestone or release; use `TBD` until planning. |
| `last_updated` | ISO date (`YYYY-MM-DD`). |

User requirements also include `journey_id`, `journey`, `stage`, `persona`,
observable `acceptance_criteria`, `depends_on`, and `linked_work_items`.
Technical requirements also include `area`, `rationale`, `verification`,
`supports_user_requirements`, and `depends_on`.

## Journey catalog

The user register groups requirements into complete journeys. An outcome row
states the journey goal; stage rows cover setup, the happy path, alternate
paths, observable completion, and recovery.

| Journey | Outcome |
| --- | --- |
| `J-01` Adopt and initialize | Install Roadmap, initialize or open a workspace, and establish safe defaults. |
| `J-02` Capture and triage work | Create, inspect, prioritize, assign, and organize issues. |
| `J-03` Execute daily work | Select work, manage state and dependencies, collaborate, and complete it. |
| `J-04` Plan delivery | Organize projects and milestones, review scope/progress, and close or archive delivery units. |
| `J-05` Collaborate through Git | Use ordinary Git collaboration plus explicit local issue/branch references. Automatic hooks and commit mutation are deferred beyond 0.2. |
| `J-07` Report and automate | Produce stable terminal, structured, export, and stakeholder reporting outputs. |
| `J-08` Diagnose and recover | Detect corruption or inconsistency, preview repair, recover data, and understand failures. |
| `J-09` Configure and evolve | Manage configuration and safely upgrade or migrate repository data. |
| `J-10` Manage requirements as code | Create, govern, link, verify, exchange, and plan from requirements. The minimal optional scope is Accepted for 0.4; broader interchange and supersession remain Deferred. CSV remains authoritative until verified cutover. |

## Editing rules

1. Add one outcome or constraint per row.
2. Write requirements independently of a preferred implementation unless the
   implementation is itself a constraint.
3. Make acceptance criteria and verification repeatable.
4. Reference requirement IDs from issues, pull requests, tests, and release
   notes where practical.
5. Update `last_updated` whenever meaning, priority, status, ownership, or
   traceability changes.
6. Do not delete historical requirements. Mark them `Rejected` or `Deferred`,
   or supersede them with a new ID and preserve the review link.
7. A complete user journey must include an observable outcome and recovery or
   failure behavior; a list of commands alone is not a journey.

Approval and status transitions follow the
[project governance process](../governance/README.md#requirement-lifecycle).

## Verification records

[verification-evidence.json](verification-evidence.json) records the assessed
requirements, baseline commit, candidate scope, date, named tests, commands and
remaining gaps. [October verification notes](verification-2026-10-06.md) explain
the scope and status decisions. This is repository governance data; it does not
introduce an in-app requirements feature or a second canonical workspace store.

- `Verified` requires a passing scoped record, concrete evidence and no known
  unmet acceptance criteria. It is verification of the candidate, not a claim
  that the code is already released or independently reviewed.
- A partial record keeps status `Accepted` and lists the missing proof. An
  unassessed requirement also stays `Accepted`; a related green test is not enough.
- Update `last_updated` and the `source` reference when the meaning/status changes.
  Preserve the earlier triage record as history. Revisit verification when the
  implementation, supported platform scope or contract changes.
- CI validates IDs, lifecycle/dependency states and verification prerequisites.
  Named test references prove traceability; passing tests and human review still
  determine whether their assertions satisfy the requirement.

## Accepted 0.4 scope

The [0.4.0 plan](../planning/0.4.0-plan.md) records nine accepted outcomes,
implementation recommendations and remaining design gates. The
[work items](../planning/0.4.0-work-items.md) link these registers to the live
Roadmap workspace. Accepted scope is not implemented or verified behavior.

## Collaboration and import release decision

[Completion after pull and bounded GitHub import](proposals/collaboration-completion-after-pull.md)
records the accepted 2026-10-08 scope decision: UR-067/UR-068 and TR-055/TR-056
target 0.4; GitHub-only closure correctness, UR-069/TR-057, targets 0.5.
The registers and live work items reflect that boundary.
