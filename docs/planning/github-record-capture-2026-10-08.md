# GitHub source-record capture — 2026-10-08

Captured at 2026-10-08T12:50:05.620407+00:00 from `shanewilkins/roadmap` through read-only `gh` calls.

All 11 current open issues match the frozen baseline; no later arrivals were
found. Every mapped canonical Roadmap issue now contains a source snapshot
comment added with published roadmap-cli 0.3.1. The original local issue bodies,
metadata, triage comments and history were preserved. No GitHub issue changed.

Each snapshot contains the exact original description, full REST issue metadata,
all paginated discussion comments and all paginated timeline event payloads.
Original authors, timestamps, labels, assignees, milestone, state, links and
closure metadata remain source attributes rather than local lifecycle changes.
All 11 remote issues currently have zero discussion comments. Attachments remain
URLs; linked/binary content and unavailable private edit history are outside the
capture. These snapshots are dated evidence, not an automatic sync mechanism.

## Capture index

| GitHub source | Canonical Roadmap issue | Local source comment | Timeline events |
| --- | --- | --- | --- |
| [#3676](https://github.com/shanewilkins/roadmap/issues/3676) | [847923fe-b895-4569-8cf6-9c8e1b677982](../../.roadmap/issues/847923fe-b895-4569-8cf6-9c8e1b677982.md) | 2 | 1 |
| [#3687](https://github.com/shanewilkins/roadmap/issues/3687) | [b902692e](../../.roadmap/issues/b902692e.md) | 2 | 4 |
| [#3689](https://github.com/shanewilkins/roadmap/issues/3689) | [8a1080c8](../../.roadmap/issues/8a1080c8.md) | 2 | 6 |
| [#3703](https://github.com/shanewilkins/roadmap/issues/3703) | [76d11a36](../../.roadmap/issues/76d11a36.md) | 2 | 2 |
| [#3715](https://github.com/shanewilkins/roadmap/issues/3715) | [09c69060](../../.roadmap/issues/09c69060.md) | 2 | 2 |
| [#3716](https://github.com/shanewilkins/roadmap/issues/3716) | [1007b6f2](../../.roadmap/issues/1007b6f2.md) | 2 | 6 |
| [#3749](https://github.com/shanewilkins/roadmap/issues/3749) | [07b21448](../../.roadmap/issues/07b21448.md) | 2 | 1 |
| [#3753](https://github.com/shanewilkins/roadmap/issues/3753) | [444e2773-9d34-4216-bd5d-78a598d834ad](../../.roadmap/issues/444e2773-9d34-4216-bd5d-78a598d834ad.md) | 1 | 1 |
| [#3754](https://github.com/shanewilkins/roadmap/issues/3754) | [65ec3783-e287-4e6c-bbb6-9e387ea7d657](../../.roadmap/issues/65ec3783-e287-4e6c-bbb6-9e387ea7d657.md) | 1 | 0 |
| [#3755](https://github.com/shanewilkins/roadmap/issues/3755) | [74684a37-de5a-448a-89c3-bef4fd4cdf96](../../.roadmap/issues/74684a37-de5a-448a-89c3-bef4fd4cdf96.md) | 1 | 0 |
| [#3756](https://github.com/shanewilkins/roadmap/issues/3756) | [9928b489-c652-4116-8f7d-831700b4c7fd](../../.roadmap/issues/9928b489-c652-4116-8f7d-831700b4c7fd.md) | 1 | 0 |

## Verification

The [machine-readable index](github-record-capture-2026-10-08.json) records source
hashes and local comment IDs. Every stored JSON source record was parsed back
from the canonical comment and compared for exact equality with the fetched
issue/comments/timeline payload. The readable description was also preserved
verbatim. Prior canonical fields, body and comments/history were checked for
preservation. A repeated capture of the same payload made no further mutations.

[Post-capture health scan](health-after-github-capture-2026-10-08.json) exited 0
with zero findings. This validates data capture, not the underlying fixes.

An initial import-helper verification incorrectly treated an embedded Markdown
separator as a frontmatter delimiter. The CLI wrote a valid record; correcting
the helper and retrying left identical snapshot comments 1 and 2 on #3676.
Both are retained as history; the index names comment 2. The helper now parses
actual delimiter lines and detects prior snapshots from decoded comments.
This was an import-helper error, not an application corruption or remote comment.
