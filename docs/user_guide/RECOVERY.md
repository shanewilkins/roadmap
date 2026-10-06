# Diagnose and recover a workspace

Roadmap's Markdown/YAML documents are authoritative. SQLite is a disposable
projection. Interrupted writes also leave transaction evidence under
`.roadmap/db/transactions/`; preserve that evidence when backing up a damaged
workspace.

This guide describes the recovery safeguards added after 0.3.0. Use a build
containing those changes before relying on the stricter conflict checks.

## Inspect before repairing

Stop other Roadmap writers, then copy the entire `.roadmap/` directory to a
separate backup location. Include the `db/transactions/` directory, even if
you normally exclude disposable database files from Git.

```bash
roadmap health --format json
roadmap health fix --dry-run --format json
```

Both commands inspect without applying repair. Health exit codes are `0` for
healthy, `1` for warnings/degraded state, and `2` for errors/unhealthy state.
Repair previews retain the current health exit code: a nonzero preview exit
does not mean the preview changed data or failed to run.

## Missing or corrupt SQLite projection

`projection.not-current` identifies a missing, stale, corrupt, or incompatible
projection. If canonical documents are valid, preview and rebuild it:

```bash
roadmap health fix --fix-type projection --dry-run --format json
roadmap health fix --fix-type projection --yes --format json
roadmap health --format json
```

The rebuild reads canonical documents and must leave their bytes unchanged.
Canonical errors block automatic projection repair; correct those errors
before trying again. A subsequent issue query can also refresh derived state,
but the health workflow makes the repair explicit and reviewable.

## Interrupted canonical transaction

`transaction.interrupted` means a transaction directory remains. Preview and
apply recovery, then refresh any stale projection:

```bash
roadmap health fix --fix-type recovery --dry-run --format json
roadmap health fix --fix-type recovery --yes --format json
roadmap health fix --fix-type projection --yes --format json
roadmap health --format json
```

Prepared transactions finish the complete recorded write set; transactions
whose ordinary failure began rollback restore the complete previous state.
Unprepared staging and completed cleanup directories can be discarded without
rewriting canonical documents. Recovery is repeatable. The next Roadmap
mutation also attempts transaction recovery under the workspace lock.

Before applying a pending transaction, recovery checks every target and
snapshot. Targets must match the recorded before or after state. New journals
include snapshot digests; snapshot filenames must stay in their transaction
directory. Missing/corrupt snapshots, malformed journals, and post-interruption
manual edits stop recovery and leave the transaction available for inspection.

## Successful writes with maintenance warnings

A transaction-cleanup warning means canonical changes already committed. Do
not repeat the mutation merely because cleanup could not finish. The next
mutation retries journal cleanup under the workspace lock; health can show
remaining transaction state. Preserve journals if recovery itself reports an
error rather than deleting them manually.

If projection refresh or its stale marker cannot be written, canonical changes
also remain committed. The next query compares canonical content with the
projection and refreshes it. Use health and the projection-repair workflow if
the storage problem persists. An unreadable canonical directory blocks repair
so an incomplete inventory cannot overwrite the projection.

Backup retention cleanup rejects symbolic links and requires its selected files
to remain inside the backups directory after confirmation. Correct unsafe paths
before retrying; cleanup does not follow links to delete external backup files.

## When automatic recovery stops

Keep the backup and the original transaction directory. The error identifies
the transaction and why it cannot be replayed. Inspect `journal.json`, its
target paths, and the corresponding before/after snapshots against a trusted
backup or Git history. A manual edit that does not match either recorded state
is intentionally preserved rather than overwritten.

Reconcile the complete affected write set from trusted data before retrying.
If snapshots or the journal itself are damaged, manual recovery must establish
a consistent canonical state and retain the damaged journal outside the
active transaction directory as evidence. Removing the journal alone does not
repair a partially written workspace. Run health and explicitly rebuild the
projection after reconciliation.

For invalid YAML, duplicate IDs, broken references, or Git conflict markers,
repair the canonical document using its backup/history; health does not guess
the intended content.

## Writer contention and migration retries

`workspace lock timed out` means another process holds the advisory lock.
Wait for that writer to finish, then retry. The kernel releases its lock if
the process dies; the PID text in the lock file is diagnostic metadata, not
the lock itself. Removing the lock file while a writer is active can allow
two different lock files to be used and must not be used as a repair.

If migration is interrupted, preserve the backup and transaction directory,
then retry the documented [migration workflow](MIGRATING_TO_0_2.md). Migration
rechecks its plan and resumes transaction recovery; a missing projection after
canonical migration is rebuilt on retry. Review any reported conflicts before
confirming the retry.

See the [reliability evidence map](../architecture/reliability-evidence.md) for
tested guarantees and the boundaries of those tests.
