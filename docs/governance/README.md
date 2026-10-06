# Project Governance

Roadmap CLI uses maintainer-led, repository-native governance. The goal is to
make scope and quality decisions visible without adding meetings or a large
process layer.

## Decision principles

When tradeoffs are necessary, prefer:

1. User data safety and credential security.
2. Correct, predictable CLI behavior.
3. Backward compatibility and portable plain-text data.
4. Offline operation and scriptability.
5. Maintainable architecture and testability.
6. New features and convenience.

## Roles and decision rights

| Role | Responsibilities | Decision rights |
| --- | --- | --- |
| Maintainer | Own product direction, review changes, manage releases, and handle security reports. | Final approval for requirements, priorities, breaking changes, releases, and security decisions. |
| Requirement owner | Clarify a requirement, maintain its acceptance criteria, and collect verification evidence. The maintainer is the default owner. | Recommend status and priority changes. |
| Contributor | Propose requirements, implement focused changes, add tests, and update documentation. | Make proposals through issues and pull requests. |
| Reviewer | Check behavior, architecture, tests, security, and documentation. | Approve changes when delegated by the maintainer. |

Repository ownership is defined in [CODEOWNERS](../../.github/CODEOWNERS).
This governance model does not require a committee or quorum.

### Current review capacity

The project currently has one maintainer and no designated backup maintainer.
Independent human review is encouraged when available but is not claimed as
an established practice. Automated checks provide evidence; they do not count
as independent approval. The maintainer may approve a change using the quality
gate below and must record material risks and accepted exceptions in its pull
request or decision record.

The [October review closeout](review-closeout-2026-10-06.md) records the observed
review evidence and its limits. Revisit this status when a reviewer is delegated
or repository ownership changes.

## Governance artifacts

Existing project policies remain authoritative in their specific areas:

| Artifact | Purpose |
| --- | --- |
| [CONTRIBUTING.md](../../CONTRIBUTING.md) | Contribution workflow and local checks. |
| [CODE_OF_CONDUCT.md](../../CODE_OF_CONDUCT.md) | Community behavior and enforcement. |
| [SECURITY.md](../../SECURITY.md) | Private vulnerability reporting and response. |
| [Architecture decisions](../architecture/README.md) | Accepted system design and dependency decisions. |
| [Naming conventions](../NAMING_CONVENTIONS.md) | Stable milestone naming rules. |
| [User requirements](../requirements/user-requirements.csv) | User outcomes and acceptance criteria. |
| [Technical requirements](../requirements/technical-requirements.csv) | Engineering constraints and verification methods. |
| [Requirements artifact proposal](../requirements/REQUIREMENTS_AS_ARTIFACTS.md) | Draft boundary and lifecycle for first-class requirements in Roadmap. |
| `CHANGELOG.md` | User-visible release history. |
| `.roadmap/` | Implementation work items and, after planning, the development roadmap. |

If two documents conflict, the more specific policy controls. The maintainer
resolves unresolved conflicts and records material architecture decisions as
ADRs in the architecture decision directory.

## Requirement lifecycle

1. **Propose.** Add a complete row with a stable ID and `Draft` status.
2. **Triage.** Check the outcome, scope, acceptance criteria, priority, owner,
   duplicates, dependencies, and security implications.
3. **Decide.** The maintainer changes the status to `Accepted`, `Deferred`, or
   `Rejected`. A reason belongs in the associated issue or pull request.
4. **Plan.** Link accepted requirements to `.roadmap` issues or milestones and
   assign a roadmap target.
5. **Implement.** Pull requests reference the requirement IDs they satisfy and
   include proportionate tests, documentation, and changelog updates.
6. **Verify.** The requirement owner confirms the recorded acceptance criteria
   or verification method and changes the status to `Verified`.

Status meanings:

| Status | Meaning |
| --- | --- |
| `Draft` | Proposed or inventoried; not yet approved for delivery. |
| `Accepted` | Approved and eligible for roadmap planning. |
| `In Progress` | Linked implementation work has started. |
| `Verified` | Delivered and checked against its stated evidence. |
| `Deferred` | Valid, but intentionally not scheduled. |
| `Rejected` | Not part of the intended product direction. |

## Change control

- Editorial fixes that do not change meaning may be merged through the normal
  review process.
- Behavioral changes must update or reference at least one requirement.
- New scope starts as `Draft`; implementation should not be used as implicit
  approval.
- Security, data-format, CLI compatibility, or architecture-boundary changes
  require maintainer review and explicit migration or rollback notes.
- Breaking changes require an accepted requirement, an architecture decision
  when design-wide, release notes, and a documented migration path.
- Requirement IDs are never reused. Superseded rows remain for history and
  point to their replacements through the linked work item or review record.

## Quality gate

A change is ready to merge when its acceptance criteria are demonstrably met,
relevant automated tests pass, documentation is current, architecture checks
pass, security implications are addressed, and CI is green. The exact local
commands and pull-request expectations live in
[CONTRIBUTING.md](../../CONTRIBUTING.md); automated checks live in
[tests.yml](../../.github/workflows/tests.yml).

## Operating cadence

- Triage draft requirements before each roadmap-planning session.
- Review accepted requirements when milestones are created or changed.
- Review stale `In Progress` items and unverified completed work at least once
  per release.
- Revisit this governance document when ownership, release practice, or the
  contribution model changes.

## Continuity and inactivity

For a planned absence, the maintainer should either announce a maintenance
pause or name a willing temporary maintainer in a public issue. Record the
scope and duration of delegated review, merge, release, and security duties.
Update CODEOWNERS and repository permissions only after the delegate accepts;
review access when the delegation ends. Never place credentials or private
security reports in a public handover record.

After 90 days without a maintainer response to a substantive issue or pull
request, contributors may open a maintenance-status issue asking whether the
project remains active. This is a review trigger, not automatic transfer of
ownership or a promise that a replacement maintainer exists. Without an
authorized delegate, contributors should treat fixes and releases as delayed.

A handover should reference the requirements registers, accepted ADRs, open
issues, recovery guide, latest green CI run, and release workflow. Confirm
repository administration and package publishing access through the service's
own access controls, and exercise an installed-package check before a release.
Private vulnerability reports continue through SECURITY.md's channels;
security access must be delegated privately before claiming another responder.

If the maintainer returns, they should record resumed maintenance and review
outstanding reports and delegated access. If continuity cannot be arranged,
contributors may maintain a clearly named fork under the project license,
while preserving canonical-data compatibility and documenting any divergence.
The fork must identify its own maintainers and security reporting channels.
