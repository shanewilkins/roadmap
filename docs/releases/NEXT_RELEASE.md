# Next release preparation

The published version is 0.3.0. The local release candidate is 0.3.1; it is
not yet tagged or published. This checklist prepares a reviewable release;
it does not authorize a tag, push, merge, publication or permission change.

The [October 8 review follow-up](../governance/bplus-followup-2026-10-08.md)
records the current local fixes and baseline CI evidence. Maintainer-selected version:
**0.3.1**, retaining the planned 0.4 feature and
deprecation-removal boundary. Baseline CI is not proof of the final candidate.

## Candidate and compatibility

- [x] Select 0.3.1 with the maintainer; never reuse immutable PyPI 0.3.0.
- [ ] Record the clean candidate SHA, requirement evidence and green CI URL.
- [x] Move delivered entries to the dated 0.3.1 candidate section.
- [x] Update package version and lock metadata together; artifact verification recorded below.
- [x] Full local suite: 1,188 passed, 97.21% statement coverage, no deprecation warnings.
- [x] In the 0.3 line, preserve deprecated spellings and warnings.
  Removal belongs to 0.4, with replacement commands in the migration notes.
- [x] Document bounded `health fix --fix-type projection|recovery`, read-only
  previews, `--yes` consent vs `--force` lifecycle override, and stderr diagnostics.
- [x] Retain the explicit 0.1.1 migration and supported macOS/Linux limitations.

The [CLI contract](../architecture/cli-interface-contract.md) and
[candidate changelog](../../CHANGELOG.md#031---2026-10-08) are the candidate roster.
Internal Python APIs and SQLite schema are not public integration contracts.
The [draft announcement](0.3.1-announcement.md) is prepared for the matching
GitHub Release after publication verification.

## Verification

Run [contributor checks](../../CONTRIBUTING.md#local-quality-checks) using the
explicit coverage configuration. The floor is 90% statement coverage; branch
coverage is informational and must not be silently compared to that floor.
Current CI also requires the hashed dependency audit and actionlint, tests
Python 3.12–3.14, and checks wheel/sdist on Ubuntu x64 and macOS ARM64.

```sh
uv lock --check
uv build --out-dir /tmp/roadmap-release-candidate
# Substitute the selected version in both artifact paths.
uv run --locked python scripts/smoke_package.py /tmp/roadmap-release-candidate/roadmap_cli-VERSION-py3-none-any.whl
uv run --locked python scripts/smoke_package.py /tmp/roadmap-release-candidate/roadmap_cli-VERSION.tar.gz
```

- [ ] Check metadata documentation URL resolves to `master` or the candidate tag.
- [x] Install the exact built wheel in a clean environment and run
  `scripts/checkpoint_journey.py` with that environment's absolute `roadmap` path.
- [x] Verify repeated migration/recovery, unchanged canonical digests, JSON
  stdout and explicit selection/repair behavior.

The [October 8 follow-up](../governance/bplus-followup-2026-10-08.md#verification-performed)
records wheel/sdist hashes, clean-install results and the installed cumulative
journey. Artifacts remain local and unpublished.
- [x] Maintainer approved commit/push, the version tag and PyPI release on October 8.
  Review capacity and remaining evidence limits stay explicit in the follow-up report.

## Publication, only after approval

1. Publish the reviewed commit/tag through `.github/workflows/release.yml`; its
   reusable CI gate precedes build and trusted PyPI publishing.
2. Verify the workflow's index-install job and install the new version from PyPI.
   Confirm help/version and a retained-user journey, not just index presence.
3. Create or update the matching GitHub Release announcement from the changelog
   after the package is verified. Do not label master as a published release.
4. Update README and installation guidance together, linking the tagged docs.
   Record version, SHA, CI run, publication URL and installed-artifact evidence.

The older [0.2 checklist](0.2.0-checklist.md) remains historical release evidence;
its branch, coverage and matrix details are not current instructions.
