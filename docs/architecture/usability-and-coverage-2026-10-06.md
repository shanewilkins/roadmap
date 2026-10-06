# Usability and 90% coverage pass: 2026-10-06

This is separate work after the reliability/tooling PR #3774 was merged.
The changes target small workflow improvements and observable reliability
promises, with no new runtime dependencies or release publication.

## User-facing behavior

- Ambiguous issue/project/milestone IDs list matching IDs and labels. Duplicate
  project/milestone names also fail explicitly, with exact IDs available to select.
- Plain health findings with a safe recovery/projection action show the exact
  dry-run command. Suggestions do not apply repairs, and arbitrary action names
  cannot turn into suggested commands.
- `roadmap config explain KEY [--format json]` reports the effective value,
  project/user owner, and default/configured source without machine paths.
  Existing `config get` continues to report explicitly stored values.
- `roadmap issue create --print-id` puts only the full created ID on stdout.
  Projection warnings and optional branch notifications go to stderr. A branch
  failure returns nonzero after creation; the emitted ID can be inspected before
  retrying, and the issue remains committed.
- [Shell completion](../user_guide/SHELL_COMPLETION.md) documents built-in command,
  option, and choice completion. Installed-entry-point tests cover source generation
  for Bash/Zsh/Fish and priority-value completion outside a workspace. Entity-ID
  completion is not introduced in this pass.

The public contract inventory records the new command and option, with links to
existing configuration, stable-output, and execution requirements.

## Reliability defects found

Manually edited configuration could provide a number/list for declared text
fields even though scoped writes reject those values. Reads now use the same
value validation before commands can mutate data; boolean schema versions are
also rejected. Existing null-boolean/default compatibility is preserved.

Broken-reference findings used only a filename as their scope. Entity filtering
therefore hid them and could return a healthy exit code. Findings now use the
workspace-relative canonical path, retaining the finding and unhealthy exit code
when filtering by entity.

## Verification

The full local suite passed **686 tests** with the exact CI coverage configuration:
**93.33% statement coverage (5,203 / 5,575)**, up from **88.15% (4,872 / 5,527)**.
The coverage floor is raised from 87% to **90%**. No new exclusions, skipped
failures, or instrumentation changes were used to reach it.

The pass adds 62 tests: 24 usability cases, 15 real-storage command journeys,
and 23 configuration validation/fault cases. The same 70 selected cases,
including existing configuration tests, are checked against a non-editable
wheel with an isolated Python import assertion. Final CI/package results are
recorded on the separate PR's checks and description.

Coverage grew through checked postconditions: typed configuration refusal and
failed replacement preserve bytes; lookup errors and reporting do not mutate
canonical documents; repair preview/decline leave the projection untouched;
confirmed repair rebuilds it; exports refuse overwrite and retain existing bytes;
comments retain reply parents; reciprocal dependency edits reject cycles and
update both sides. Planning views and daily summaries assert entity/workflow
scope rather than merely exercising renderers.

Ruff, ty, architecture contracts, Bandit, Xenon, wheel/sdist builds, and pre-commit
remain required. Coverage is statement coverage of pytest execution; completion
subprocess tests independently assert behavior rather than implying branch or
subprocess coverage. The 79 existing Click fixture deprecation warnings remain
visible; these new fixtures use pytest temporary directories.
