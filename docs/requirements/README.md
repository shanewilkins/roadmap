# Requirements Register

This directory is the product and engineering input to the development
roadmap. The initial rows inventory requirements visible in the current code
and documentation; a row remains `Draft` until it is deliberately reviewed.

## Files

- [user-requirements.csv](user-requirements.csv) records user outcomes and
  observable acceptance criteria.
- [technical-requirements.csv](technical-requirements.csv) records system
  constraints, rationale, and verification methods.
- [Requirements as First-Class Artifacts](REQUIREMENTS_AS_ARTIFACTS.md) is the
  draft product and architecture recommendation for managing these records in
  Roadmap itself.

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
| `J-05` Collaborate through Git | Connect issues to branches, commits, and reversible Git-hook automation. |
| `J-06` Synchronize remotes | Configure, preview, reconcile, recover, and audit optional remote synchronization. |
| `J-07` Report and automate | Produce stable terminal, structured, export, and stakeholder reporting outputs. |
| `J-08` Diagnose and recover | Detect corruption or inconsistency, preview repair, recover data, and understand failures. |
| `J-09` Configure and evolve | Manage configuration and safely upgrade or migrate repository data. |
| `J-10` Manage requirements as code | Create, govern, link, verify, exchange, and plan from requirements. This journey is proposed, not accepted. |

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
