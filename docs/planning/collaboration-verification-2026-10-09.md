# Completion after pull: verification on 2026-10-09

Scope: UR-067/TR-055, work item `355390b8-7f70-4f89-8042-34252d6d4981`.

## Installed-package findings

Published 0.3.1 already carries valid completion through ordinary Git exchange.
It has one observed gap: a body-only unresolved Git conflict is diagnosed by
health but accepted by issue inspection as a closed canonical record. Metadata
conflicts alone do not expose this because malformed YAML already fails parsing.

The development candidate rejects complete unresolved Git hunks at the shared
document parser. Health uses the same detector. This covers filesystem reads and
committed-blob parsing; marker mentions inline in prose are not conflict hunks.
Resolution remains ordinary Git conflict resolution, followed by a normal read.
The candidate wheel retains the current development package metadata version
0.3.1; it is not a new PyPI release. The fix is intended for 0.4.

## Repeatable journey

```bash
python scripts/collaboration_journey.py --roadmap-command /absolute/path/to/roadmap
```

The runner creates a temporary local bare remote and two independent clones.
Each CLI subprocess uses an isolated personal home; Git system/global config is
disabled, identities are test-only, commands have 30-second timeouts, and the
source project workspace is not used. Canonical entity mutations use Roadmap.
The only direct canonical write models partial manual Git conflict resolution.
The CLI path resolves before changing directories, so the runner exercises an
installed executable rather than importing application code into the journey.

Bob captures a project, milestone and issue, assigns the work to himself, and
records explicitly attributed implementation context. Alice clones and warms
her projection while the issue is still todo. Bob closes the issue with a reason,
commits its canonical record and implementation file on a branch, merges with
`--no-ff`, and pushes. Alice pulls with `--ff-only`; her existing projection still
contains the old todo record immediately after pull.

Eight independent first-read scenarios restore that stale projection or remove
it before each detail, list, milestone and project query. All report the same
closed issue; milestone/project totals are one of one closed and 100% complete.
The issue ID, closure reason/history, assignee, comment body/author and Markdown
context survive. Canonical Markdown/YAML hashes remain unchanged by reads.
The implementation file arrives, the receiving clone stays Git-clean, and Bob's
personal configuration is not exchanged. Parent milestone/project lifecycle
states are not automatically closed by completing their issue.

Both clones then edit the issue context and create a real Git merge conflict.
The runner resolves the metadata using the incoming side while retaining a
conflicting Markdown body constructed from Git's index stages. Health reports
`canonical.git-conflict`; all four ordinary views refuse the record without
rewriting it. Resolving with Git's incoming canonical record and committing the
merge makes ordinary views succeed again with the original issue ID, closure
history and selected context. No reimport or health repair is required.

## Evidence and limits

- Published 0.3.1: eight valid-completion reads pass; body-conflict inspection
  fails the required refusal check by returning a closed issue successfully.
- Installed candidate wheel: eight first-read checks and all conflict/refusal
  and resolved-retry checks pass on macOS with Python 3.14.2.
- Scoped persistence, read-safety and closure-publication regressions: 388 passed.
- Eight document regressions cover issue/milestone/project bodies, LF/CRLF,
  resolved retry, inline mentions, diff3 and custom-width conflict markers.
- CI now runs the installed journey on Ubuntu/macOS with Python 3.12–3.14.
  [Live CI run 37983657896](https://github.com/shanewilkins/roadmap/actions/runs/37983657896)
  passed 1,275 tests on each Python version and all six installed collaboration
  journeys, each reporting eight first-read checks and successful conflict retry.
  The verified source commit is `0abbef57d6a07a34be16f82bf170198ec6abbb84`.
  Live CI outcomes are also retained in the Roadmap work item's comments.

This is verification of Git-authored canonical completion. GitHub-only closure
propagation remains the separate 0.5 requirement UR-069/TR-057. The journey does
not implement or verify the future requirements lifecycle; completing this issue
does not change the authoritative requirements registers' Accepted statuses.
