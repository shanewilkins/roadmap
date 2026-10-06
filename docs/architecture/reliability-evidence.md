# Reliability guarantees and evidence

Date: 2026-10-06. Baseline: master `65a3f324`, with local dependency, review
closeout, and reliability changes. These changes are not yet committed or
verified by remote CI. This is evidence for specific guarantees, not a new
overall quality-review grade.

Canonical persistence follows the [persistence contract](canonical-persistence-contract-0.2.md).
User-facing procedures live in the [recovery guide](../user_guide/RECOVERY.md).
Requirement IDs below refer to the [technical register](../requirements/technical-requirements.csv).

## Guarantee map

| Guarantee | Requirements | Automated evidence |
| --- | --- | --- |
| Canonical bytes remain authoritative; damaged projections are replaceable | TR-002 | Existing `test_projection_is_disposable_and_rebuilds_without_canonical_writes`; new `test_cli_projection_repair_preserves_canonical_bytes` covers missing, corrupt, and truncated SQLite through separate CLI processes |
| Failed ordinary writes restore the complete old state and permit retry | TR-008 | Existing commit-stage injection tests; new `test_replacement_failure_restores_all_files_and_allows_retry` injects EACCES/ENOSPC at the actual replacement boundary after the first file changes |
| An interrupted prepared transaction recovers consistently after restart | TR-008, TR-034 | New `test_sigkill_recovers_complete_transaction_on_fresh_process` kills update/delete workers after preparation, first replacement, and before cleanup; a fresh process recovers and a second recovery preserves bytes |
| Unprepared intent is never applied | TR-008 | New `test_sigkill_before_prepared_journal_discards_only_uncommitted_intent` |
| Incomplete rollback remains a rollback on retry | TR-008 | New `test_failed_rollback_is_retried_as_rollback_not_as_new_commit` |
| Recovery preserves edits made after interruption and validates the complete transaction before writing | TR-007, TR-008, TR-034 | New unit cases for missing/corrupt snapshots, malformed/empty journals, escaping snapshot paths, and post-interruption edits; `test_cli_recovery_refuses_to_overwrite_post_crash_manual_edit` checks the user-facing refusal |
| Roadmap writers cannot steal each other's lock or lose each other's successful comments | TR-008 | New `test_separate_writer_cannot_steal_lock_and_sigkill_releases_it` and `test_two_cli_writers_preserve_both_comments` |
| Failed recovery or lock-metadata writes release acquired kernel locks | TR-008 | New `test_failed_recovery_releases_lock_even_when_unit_is_retained` and `test_lock_metadata_failure_releases_kernel_lock` |
| Health preview is non-mutating and confirmed recovery is repeatable | TR-033, TR-034 | Existing diagnostics contracts and new `test_cli_previews_then_recovers_interrupted_transaction` |
| Migration preserves identities/content and safely retries after process death | TR-035 | Existing migration contracts plus new `test_sigkill_migration_retries_without_losing_ids_or_content`, including interruption after canonical commit but before projection rebuild |

The unit cases are in
`tests/unit/adapters/persistence/test_transaction_recovery.py`; process and CLI
cases are in `tests/integration/persistence/test_process_recovery.py`. Existing
document, projection, diagnostics, and migration tests remain in
`tests/unit/adapters/persistence/`.

## Defects corrected

- Recovery previously applied early entries before discovering a later
  missing snapshot, and could overwrite post-interruption manual edits.
- Snapshot paths could escape the transaction directory; new snapshots carry
  digests so accidental corruption is detected before replay.
- Recovery failure and lock-metadata fsync failure could retain an acquired
  lock when the owning object remained alive.
- Transaction snapshots lacked explicit durable writes. Preparation now
  persists snapshots/journal before publishing the transaction for replay;
  unprepared and completed directories have distinct cleanup-only names.
- A failed rollback previously retained a journal that requested roll-forward.
  Rollback intent is now persisted before restoring the old state.
- Migration retry could report a current canonical schema without rebuilding
  a projection missing after a post-commit crash.
- CI, pre-commit, and contributor check commands now explicitly select the
  development extra so the checks use the locked development tools.

## Results

- 32 added cases: 15 recovery unit cases and 17 process/CLI cases.
- Full suite: **541 passed**, **85.90%** coverage against the 85% gate.
- Installed-wheel drill: **32 passed** using the wheel's site-packages and
  console entry point, with source-checkout imports excluded.
- Ruff formatting/lint, Pyright, ty, architecture enforcement, Xenon gates,
  and the changed-file pre-commit hooks all passed. Radon average: A (3.08).
  Bandit reported no unsuppressed findings; the two previously reviewed local
  Git subprocess exceptions remain scoped to B404/B603.
- Wheel and source distribution built successfully. The tested wheel SHA-256
  is `b8319a5442323b1a598acff44df53492e8f057e922c0d13e954d123ff0f69a1d`.

Logs for this local session are `/tmp/roadmap-reliability-full-suite.log` and
`/tmp/roadmap-reliability-installed-tests.log`; temporary logs are not durable
release evidence. The evidence map and regression tests are repository files.

## Reproduce

```bash
uv sync --all-extras --locked
uv run --locked --extra dev pytest -n 0 tests/unit/adapters/persistence tests/integration/persistence tests/integration/cli/test_cli_migrate_command.py
uv run --locked --extra dev pytest --cov=roadmap --cov-config=config/.coveragerc --cov-report=term
```

The normal CI test matrix includes these tests on Python 3.12, 3.13, and 3.14.
The local installed-wheel drill uses a separate virtual environment containing
the built wheel and the locked test dependencies. It invokes pytest with
`--import-mode=importlib` from isolated Python (`-I`), first asserting that
`roadmap.__file__` is inside that environment's site-packages. This prevents
the source checkout or an editable installation from substituting for the
artifact under test. It runs both new test modules; child writers and console
commands use that environment's Python and installed `roadmap` executable.

## Evidence limits

Local verification is on macOS ARM64 with Python 3.14.2. Remote matrix results
for these changes remain pending. SIGKILL proves behavior after abrupt process
death; it does not simulate hardware power loss, filesystem damage, or every
filesystem's durability semantics. EACCES/ENOSPC tests inject syscall errors;
they do not exhaust an actual disk or alter machine permissions. Locks govern
cooperating Roadmap processes, not arbitrary editors. Journals predating the
digest fields retain compatibility but cannot provide the new snapshot-digest
check. Persistent inability to write/restore requires manual recovery from
trusted data. Evidence records implementation behavior; requirement governance
status is not changed automatically by passing tests.
