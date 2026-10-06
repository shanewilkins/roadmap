# Maintainer handover runbook

There is one maintainer and no designated backup. This runbook makes a handover
executable; it does not assign authority or establish independent review.

## Handover record

Copy this table into the agreed issue or private record. Public entries must not
include credentials, private security reports or personal contact details.

| Field | Record |
| --- | --- |
| Mode | Maintenance pause / temporary delegation / permanent handover |
| Maintainer and accepting delegate | Name the willing person, or explicitly `none` |
| Start, end and contact route | Dates and the approved public/private contact route |
| Duties | Review, merge, release and security duties individually; include exclusions |
| Baseline | Commit SHA, published version, current CI URL and installation evidence |
| Pending work | Open critical bugs, unpublished changes and unresolved verification rows |
| Access confirmation | Repository administration/merge, CI environment, PyPI trusted publishing, private advisories; each confirmed privately or `not delegated` |
| Decision | Who approved the scope, when, and where the delegate accepted |
| Completion | Return/review date, outstanding reports and access revocation/reconfirmation |

If nobody accepts, record a pause. Do not claim continuous releases or security
response during the absence. Follow the [90-day inactivity policy](README.md#continuity-and-inactivity)
and preserve the right to a clearly identified compatible fork.

## Candidate checkout drill

1. Read [requirements and verification](../requirements/README.md),
   [accepted ADRs](../architecture/README.md), [recovery procedures](../user_guide/RECOVERY.md),
   [security reporting](../../SECURITY.md) and [next-release checks](../releases/NEXT_RELEASE.md).
2. In a candidate checkout, run `git status --short`, `git rev-parse HEAD` and
   `uv lock --check`. Record local edits; do not overwrite them to make a green run.
3. Run [local quality checks](../../CONTRIBUTING.md#local-quality-checks),
   including the full configured suite where approved, and the dependency audit.
   Read current CI jobs for that SHA; a green earlier SHA is not candidate proof.
4. Build and install the wheel/sdist in temporary clean environments with
   `scripts/smoke_package.py`. Run the cumulative checkpoint journey against the
   clean wheel's command. Never drill migration or destructive repair in live data.
5. Inspect the evidence ledger's partial requirements and canonical-state
   guarantees; verify preview, consent, recovery retry and output isolation.
6. Record commands, results, candidate SHA, platform, artifact digest and remaining
   limits. Local success does not prove delegated service access or the CI matrix.

## Access and return

The existing maintainer confirms access using each service's controls only after
the delegate accepts the named duties. Keep secrets in those controls, not this
repository. Confirm trusted publisher repository/workflow/environment identity;
do not introduce a shared long-lived package token. Private security access is
separate from permission to review code. If access is unavailable, mark that duty
uncovered and pause the affected operations.

At the agreed end, record pending reports/releases, review delegated permissions,
and revoke or renew them explicitly. Resume maintenance publicly without exposing
private advisory details. CODEOWNERS changes require an actual accepted owner;
the current drill does not invent one.
