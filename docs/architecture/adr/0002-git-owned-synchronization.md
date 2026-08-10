# ADR-0002: Use Git as the sole synchronization mechanism

- Status: Accepted
- Date: 2026-08-10
- Scope: Repository synchronization and third-party tracker integration

## Context

Roadmap is a file-first, Git-native application. Human-readable roadmap files
live with the project and are intended to be versioned with its repository.

The current implementation also contains an application-level synchronization
system for reconciling local roadmap entities with remote tracker entities. It
introduces provider backends, synchronization baselines, checkpoints,
three-way reconciliation, conflict policies, retries, linkage repair, and
provider-specific mappings. This creates a second distributed-state protocol on
top of Git and allows both local files and remote tracker records to behave as
writable sources.

The Git backend in that abstraction performs no synchronization; users already
use ordinary Git operations to exchange repository state. Retaining the larger
abstraction would therefore make the application responsible for a complex
capability that is not necessary to its file-first model.

## Decision

Git is Roadmap's sole synchronization mechanism. Roadmap files in the project
repository are the canonical source of truth.

Users synchronize and collaborate through ordinary Git workflows, including
fetch, pull, merge or rebase, conflict resolution, and push. Roadmap will not
implement a parallel synchronization protocol for its entities.

Specifically:

- Roadmap will not provide continuous or command-triggered bidirectional
  synchronization between roadmap entities and GitHub Issues, GitHub
  Milestones, GitHub Projects, or another third-party tracker.
- The application will not maintain synchronization baselines, remote/local
  checkpoints, provider linkage state for reconciliation, or a second conflict
  resolution engine.
- The application will not implicitly fetch, pull, merge, rebase, or push a Git
  repository as part of an ordinary roadmap operation.
- Git authentication, remotes, transport, distributed history, and merge
  conflicts remain Git's responsibility.
- Any SQLite database, search index, cache, or analytics projection is derived
  state. It must be rebuildable from canonical roadmap files and must not become
  a competing source of truth.

Roadmap may inspect local repository information through a narrow
Application-owned port when a product feature genuinely needs it. Examples
include the current branch, working-tree status, or commit metadata. This is
version-control awareness, not synchronization. It does not authorize hidden
network operations or a generic Git service exposed throughout the application.

### Third-party integrations

A third-party tracker may be supported later only through an explicit,
bounded operation such as:

- importing selected external records as new roadmap items;
- exporting or publishing a snapshot;
- creating a remote record from a roadmap item once; or
- storing an external URL or identifier as an ordinary reference.

Such an operation must identify its source and destination clearly and must not
claim eventual consistency. It must not silently introduce baselines,
reconciliation, or a second writable source. A concrete integration requires a
separate product decision and does not belong to the core architecture merely
because provider code already exists.

## Architectural placement

There is no synchronization subsystem in the target Application zone selected
by ADR-0001.

If repository inspection is retained, Application owns a narrow port for the
specific information it needs and an outbound Git adapter implements that port.
The CLI invokes Application use cases; it does not construct or coordinate Git
or provider clients directly.

Explicit future import, export, publishing, or linking features would be
ordinary use cases with provider-specific outbound adapters. They would not
implement a `SyncBackend` abstraction.

## Consequences

### Positive

- There is one canonical representation of roadmap state.
- Collaboration uses Git's existing history, authentication, branching,
  offline operation, recovery, and conflict tooling.
- Roadmap no longer needs to reproduce distributed reconciliation above Git.
- Provider data models cannot distort the core roadmap domain.
- The architecture loses a large cross-cutting state machine and its associated
  partial-failure modes.

### Product changes and costs

- Users will not be able to edit roadmap state through GitHub Issues and expect
  those changes to converge automatically with local files.
- Existing sync commands, documentation, configuration, requirements, and tests
  will eventually need to be retired or reframed.
- Removing public synchronization behavior may require release notes and a
  deliberate compatibility boundary.
- Teams that prefer an issue tracker as their primary interface must use an
  explicit future integration or choose a tracker-native workflow instead.

## Alternatives considered

### Preserve bidirectional remote synchronization

Rejected because it requires two writable sources plus provider-specific
identity, mapping, baseline, conflict, retry, and recovery semantics. Its cost
and architectural reach are disproportionate for a Git-native roadmap whose
canonical data already lives in a repository.

### Provide one-way synchronization

Rejected as a general product mode because the word synchronization still
creates ambiguity about authority and subsequent edits. Explicitly named
import, export, or publish operations may be considered individually when a
concrete user need justifies them.

### Wrap `git pull` and `git push` in Roadmap commands

Rejected as an architectural responsibility. A wrapper would inherit policy for
credentials, remotes, dirty worktrees, merge versus rebase, conflicts, hooks,
and failure recovery while adding little capability beyond Git itself.

## Migration boundary

This ADR fixes the product and architecture decision. It does not remove the
existing synchronization implementation, commands, tests, configuration, or
documentation. That cleanup requires a separately reviewed refactor plan.

