# Requirements Register

This directory is the product and engineering input to the development
roadmap. The registers were triaged on 2026-08-16: every 0.2 requirement is
Accepted and assigned to an implementation phase, while deliberately postponed
directions are Deferred to post-0.2.

## Files

- [user-requirements.csv](user-requirements.csv) records user outcomes and
  observable acceptance criteria.
- [technical-requirements.csv](technical-requirements.csv) records system
  constraints, rationale, and verification methods.
- [Requirements as First-Class Artifacts](REQUIREMENTS_AS_ARTIFACTS.md) is the
  deferred product and architecture proposal for managing these records in
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
| `J-10` Manage requirements as code | Create, govern, link, verify, exchange, and plan from requirements. This application feature is Deferred to post-0.2; the CSV registers remain governance artifacts. |

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
