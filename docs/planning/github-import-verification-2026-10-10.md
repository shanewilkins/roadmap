# Live GitHub importer verification — 2026-10-10

Implementation: `67b3bc7559ed96b63a5405805db1f8a99c333f86`.
[CI](https://github.com/shanewilkins/roadmap/actions/runs/38088800715) passed,
including quality, supported Python tests and installed-package import journeys
on Ubuntu and macOS. The maintainer committed and pushed the implementation.

Used the freshly installed candidate CLI against the actual project workspace:

```sh
roadmap github import --repo shanewilkins/roadmap \
  3756 3755 3754 3753 3749 3716 3715 3703 3689 3687 3676
roadmap github import --repo shanewilkins/roadmap \
  3756 3755 3754 3753 3749 3716 3715 3703 3689 3687 3676 --apply
```

Preview reused eleven existing local IDs and wrote zero canonical files. Apply
captured one source revision in each of those eleven original records. The local
identity set, every planning field, prior comments/history and unknown frontmatter
were compared before/after and preserved. Unrelated issue records, projects,
milestones and workspace YAML were unchanged. The historical #3676 triage copy
was preserved; its previously recorded duplicate disposition was made explicit
with `github-source-owner:d2bedb30` through Roadmap before this run.

Repeated the same apply command against live GitHub. All eleven actions were
`unchanged`; SHA-256 comparisons of all canonical Markdown/YAML confirmed zero
writes. No local issue was created or removed. No GitHub mutation was performed
by these commands. The source snapshots include the current remote dispositions;
they do not themselves close or reopen local work.

A separate fresh GitHub open-issue inventory returned `[]`. All eleven captured
source issue states were checked closed; earlier baseline evidence retains each
fix or not-planned rationale and its outbound publication proof.

The [machine-readable result](github-import-verification-2026-10-10.json) records
qualified targets, retained local IDs and source fingerprints. The
[architecture review](../architecture/checkpoints/0.4-github-import-review-2026-10-10.md)
records the preceding checks; this run completes its pending live/CI evidence.
The installed candidate still reports 0.3.1 package metadata; this is 0.4
development evidence, not a new PyPI release. Requirement register statuses were
not promoted merely because issues were closed.
