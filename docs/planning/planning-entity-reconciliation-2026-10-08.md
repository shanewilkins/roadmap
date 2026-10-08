# Milestone and project reconciliation — 2026-10-08

## Result

The confirmed local project is `99d80769` (`roadmap`). Its current content now
describes actual delivery/governance and has the repository URL. Replaced generic
template content while preserving its original record in the
[before snapshot](planning-entities-before-2026-10-08.json).

Only three milestones remain visible: backlog, current 0.4 and current 0.5.
All 14 milestone/project relationships are reciprocal. Eleven superseded plans
are closed/archived locally; this means retirement, not verified delivery.
Stable IDs, original creation timestamps, issue references and retained metadata
are preserved. Historical names are prefixed `historical-` so they cannot be
confused with accepted current release commitments.

Nine GitHub milestone records were captured in full: five existing local IDs
reused, four missing records created. Full source payloads and untruncated
descriptions live in their canonical milestone bodies; source state/dates remain
attributed snapshots. Eight remote milestones are still open; no remote lifecycle
change was performed. Local retirement does not assert remote closure.

## Remote milestone mapping

| Source | Local canonical record | Capture |
| --- | --- | --- |
| [GitHub #1](https://github.com/shanewilkins/roadmap/milestone/1) | [67251c1c-613e-4628-ae4d-9b0d29ace7b8](../../.roadmap/milestones/67251c1c-613e-4628-ae4d-9b0d29ace7b8.md) | New record |
| [GitHub #2](https://github.com/shanewilkins/roadmap/milestone/2) | [v0-2-0](../../.roadmap/milestones/v0-2-0.md) | Existing ID retained |
| [GitHub #3](https://github.com/shanewilkins/roadmap/milestone/3) | [v.0.3.0](../../.roadmap/milestones/v.0.3.0.md) | Existing ID retained |
| [GitHub #4](https://github.com/shanewilkins/roadmap/milestone/4) | [v.0.4.0](../../.roadmap/milestones/v.0.4.0.md) | Existing ID retained |
| [GitHub #5](https://github.com/shanewilkins/roadmap/milestone/5) | [v.0.5.0](../../.roadmap/milestones/v.0.5.0.md) | Existing ID retained |
| [GitHub #6](https://github.com/shanewilkins/roadmap/milestone/6) | [7a2d27d8-4a8b-4d09-b63b-d62aa1e5d558](../../.roadmap/milestones/7a2d27d8-4a8b-4d09-b63b-d62aa1e5d558.md) | New record |
| [GitHub #7](https://github.com/shanewilkins/roadmap/milestone/7) | [3449a413-88df-4b4f-8dd5-bf5de4b84f44](../../.roadmap/milestones/3449a413-88df-4b4f-8dd5-bf5de4b84f44.md) | New record |
| [GitHub #8](https://github.com/shanewilkins/roadmap/milestone/8) | [20ec2354-fad0-4f60-900e-cb79751f529d](../../.roadmap/milestones/20ec2354-fad0-4f60-900e-cb79751f529d.md) | New record |
| [GitHub #9](https://github.com/shanewilkins/roadmap/milestone/9) | [v.1.0.0](../../.roadmap/milestones/v.1.0.0.md) | Existing ID retained |

[Complete remote milestone snapshot](github-milestones-2026-10-08.json) and
[mapping/audit results](planning-entity-reconciliation-2026-10-08.json) retain
source hashes and the explicit local/remote lifecycle distinction.

## Method and verification

All entity creation, membership repair, descriptions, retirement and archives
used installed published roadmap-cli 0.3.1. Archive previews preceded application;
no force flag or issue cascade was used. Existing one-sided membership was
repaired through explicit clear/reassign operations, because reassigning the
same project does not reconstruct a missing reverse link. Health initially
reported zero findings; its current checks validate target existence but do not
detect these reciprocal membership omissions or placeholder product content.

A complete source-payload round-trip audit passed. All 138 issue documents
present before cleanup were compared using their complete parsed frontmatter
and exact Markdown bodies before cleanup-task comments were added. Their IDs,
states, assignments, external snapshots and content were unchanged by the
milestone/project operations. Subsequent issue changes are the new maintenance
task, its completion, and two explicit follow-ups; unrelated issues are untouched.

The CLI lacks a setter for the headline rendered in milestone list descriptions.
Three bounded manual edits populated current project/0.4/0.5 summaries, updated
their timestamps and corrected the project's legacy template description. IDs,
other fields and Markdown bodies were preserved. Changes are enumerated in the
audit JSON. Then the supported health repair preview offered rebuild-projection;
confirmed application rebuilt SQLite and the final scan returned zero findings.

- [Repair preview](health-entities-repair-preview-2026-10-08.json).
- [Applied repair](health-entities-repair-applied-2026-10-08.json).
- [Post-repair health](health-after-entity-cleanup-2026-10-08.json).
- [Completed local cleanup task](../../.roadmap/issues/ab3e7120-430a-470a-b9b9-30b0cc87d635.md).
- [CLI summary-editing follow-up](../../.roadmap/issues/211aaa05-945a-4b72-82e6-88be97855259.md), unscheduled maintenance finding.

Current project totals include backlog history. Use the specific release
milestone and requirement evidence for sprint delivery; aggregate project
progress is not proof of release completion. No new date/estimate commitments
were invented and no archived legacy feature scope was adopted.

## GitHub Projects access and inventory

Initial discovery was blocked by a token without `read:project`. Read-only
Projects authorization has now completed. The owner inventory, explicitly
including closed projects, returned `projects: []` and `totalCount: 0`.
There are no additional GitHub Projects under the repository owner to import.
The confirmed local project remains `99d80769`; its old access-gap note was
updated through the CLI. No remote project or milestone was changed.

[Complete inventory snapshot](github-projects-2026-10-08.json) records the command,
owner, inclusion of closed projects, capture time and exact result. The
[previously blocked follow-up](../../.roadmap/issues/185fd22b-0683-45d3-8b61-1a96271b6934.md) is now
closed with this verification evidence. Earlier access failures remain in its
history rather than being presented as the current inventory result.

## Follow-up metadata completeness pass

All nine historical milestone headlines now contain the full external description
instead of truncated legacy summaries. The four newly captured milestones also
retain the same ordinary `github_milestone` source-number field as the five
legacy records. Canonical local UUID/legacy identity and full repository-qualified
source URLs remain distinct. The CLI exposes neither metadata setter, so these
were bounded manual edits with body/identity preservation and enumerated changed
fields in the audit JSON. No issue records or remote tracker state changed.

Exact source payload, source identifier, full description, archive state and all
14 reciprocal project memberships were audited successfully. Supported projection
repair preview/application and the post-repair scan are retained:

- [Metadata repair preview](health-milestone-metadata-preview-2026-10-08.json).
- [Metadata repair application](health-milestone-metadata-applied-2026-10-08.json).
- [Post-metadata health](health-after-milestone-metadata-2026-10-08.json), zero findings.

The subsequent authorized Projects inventory is complete and contains zero
projects, including closed projects; see the inventory evidence above.
