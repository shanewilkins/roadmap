# Migrating a 0.1.1 workspace to 0.2

Roadmap 0.2 has one bounded migration from the supported 0.1.1 workspace
layout. It is explicit, conflict-aware, repeatable, and never runs during an
ordinary read. Canonical Markdown/YAML remains the authority throughout.

## Before upgrading

1. Commit or copy the complete `.roadmap/` directory.
2. Confirm that the repository has no unresolved Git conflicts.
3. Install Roadmap 0.2 without deleting the existing workspace.
4. Do not delete the old SQLite files manually; the migration identifies and
   replaces derived state safely.

## Preview

From the repository root, run:

```bash
roadmap migrate --dry-run
roadmap migrate --dry-run --format json
```

The preview performs the same validation and collision checks as execution but
does not change project files, user configuration, or databases. Resolve every
reported duplicate ID, ambiguous relationship, malformed document, or target
path collision before continuing.

## Execute and verify

```bash
roadmap migrate --yes
roadmap health scan --details
roadmap issue list --format json
roadmap milestone list
roadmap project list
git diff -- .roadmap
```

Review IDs, relationships, comments, user-authored bodies, lifecycle states,
and the Git diff. Running `roadmap migrate --yes` again must report that no
migration is required.

The migration writes versioned documents at stable-ID paths, externalizes user
preferences, removes obsolete provider credential/reconciliation fields, and
rebuilds SQLite from the migrated files. It does not fetch, push, contact a
provider, or infer conflict resolutions.

## If verification fails

Stop using the migrated workspace. Preserve its output for diagnosis, then
restore the pre-migration `.roadmap/` tree from the commit or copy made above
and reinstall 0.1.1. Do not merge selected old database files into migrated
canonical files. See the [0.2 rollback plan](../releases/0.2.0-rollback.md) for
the release-level procedure.

The removed provider-sync commands have no 0.2 replacement. Use ordinary Git
for repository transport; SQLite projection refresh remains automatic and
local. The [remote-sync removal guide](REMOTE_SYNC_REMOVAL_0_2.md) lists the
exact boundary.
