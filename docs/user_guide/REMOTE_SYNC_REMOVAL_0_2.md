# Remote synchronization removal in 0.2

Roadmap 0.2 is a local, Git-native planning tool. Canonical Markdown and YAML
under `.roadmap/` are the durable data. SQLite is a disposable local projection
for queries and validation. Git—not Roadmap—is the network collaboration layer.

## What was removed

The 0.1.1 experimental provider protocol is absent in 0.2:

- `roadmap sync`, `roadmap git sync`, and sync metrics;
- provider issue link, lookup, unlink, and status reconciliation commands;
- provider milestone replication, baselines, merge/conflict engines, retries,
  checkpoints, mappings, and linkage repair;
- Roadmap-installed automatic Git hooks;
- provider tokens, credentials, configuration, and authentication; and
- provider-specific derived tables and caches.

Invoking a removed command returns Click's standard “No such command” error.
Roadmap does not silently select another backend or emit a lazy-registration
warning.

## Collaboration after upgrading

Commit the canonical files and use the repository's ordinary Git workflow:

```bash
git add .roadmap/
git commit -m "Update roadmap"
git pull --rebase
git push
```

Roadmap retains only bounded local Git conveniences: inspecting the worktree,
creating a safe issue branch, and linking an issue to the current local branch.
It never fetches, pulls, rebases, pushes, authenticates to, or reconciles a
remote.

## SQLite still refreshes from canonical files

Removing remote synchronization does not remove local projection maintenance.
Normal commands detect a stale SQLite projection and refresh or rebuild it from
canonical files. Manual edits and Git-authored changes to `.roadmap/` therefore
remain visible to Roadmap queries.

Use the health commands to diagnose or explicitly repair derived state:

```bash
roadmap health scan --details
roadmap health fix --dry-run --fix-type projection
roadmap health fix --fix-type projection
```

Projection repair only reads canonical files and writes SQLite. It never writes
SQLite state back into canonical documents.

## One-time migration and cleanup

Run `roadmap migrate --dry-run` against a 0.1.1 workspace, review the plan, make
a Git commit or backup, and then run `roadmap migrate`. The migration preserves
supported canonical entities, stable IDs, relationships, timestamps,
user-authored bodies, and ordinary external reference URLs. It does not migrate
provider credentials, transport policy, sync baselines, or reconciliation
state.

When a legacy local database is opened, obsolete provider-only tables are
dropped: `issue_remote_links`, `sync_metrics`, `sync_base_state`,
`sync_metadata`, and `file_sync_state`. These tables were derived protocol
state, not canonical user data. The remaining SQLite projection can always be
rebuilt from `.roadmap/` documents.

Remove Roadmap-specific provider tokens from shell profiles, CI secrets, and
credential stores, then revoke any token created solely for Roadmap. Core
workflows are fully offline and require no account or provider credential.

## External references

An external tracker URL may remain ordinary user-authored content. Roadmap
stores and displays such references but does not validate, authenticate,
replicate, or reconcile the referenced service.
