# ADR-0007: Define the compatibility and evolution contract

- Status: Accepted
- Date: 2026-08-10
- Scope: Public interfaces, schema migration, deprecation, and breaking changes

## Context

An architectural refactor can preserve behavior only if the project states
which behavior is public. Roadmap has long-lived repository data, CLI commands,
configuration, structured output, and internal Python modules with different
compatibility needs.

Without an explicit contract, internal cleanup can silently corrupt old
workspaces or break automation, while accidental internal module arrangements
can become permanent APIs.

## Decision

The following are public compatibility surfaces when documented or released:

- canonical document schemas and stable entity IDs;
- project configuration keys, scopes, defaults, and precedence;
- CLI command and option names;
- command exit-code categories;
- documented JSON, CSV, and other machine-readable output schemas; and
- explicitly documented extension or Python APIs, if any are introduced.

Human-readable terminal layout, color, spacing, and prose may evolve unless a
specific representation is explicitly documented as stable. Internal Python
module paths, classes, database schemas, caches, and composition details are not
public APIs merely because tests or other internal modules currently import
them.

### Canonical schema evolution

- Every canonical schema declares a version.
- Readers reject unsupported future versions without modifying them.
- A migration is explicit and idempotent, reports its scope, and supports
  preflight or dry-run behavior.
- Migration preserves stable IDs, relationships, user-authored content, and
  lifecycle history.
- Normal reads do not perform hidden canonical rewrites.
- Recovery guidance and a durable pre-migration state are required before a
  destructive or nontrivial migration commits.

### Behavioral evolution

- Breaking changes to a public surface require an intentional release boundary,
  migration or replacement guidance where applicable, and release notes.
- Deprecation is preferred when old and new behavior can safely coexist.
- Removed behavior is not retained through an architectural abstraction unless
  compatibility value justifies its cost.
- Contract tests protect public structured output, exit behavior, and supported
  canonical fixtures during internal refactoring.

ADR-0002 intentionally removes application-level remote synchronization from
the target product. Its eventual command, configuration, and documentation
cleanup is a declared breaking product change and must be communicated as such;
the old sync abstractions are not preserved as compatibility architecture.

## Consequences

### Positive

- The architecture can change aggressively behind explicit user contracts.
- Long-lived repositories have a predictable upgrade path.
- Automation receives deliberate rather than accidental stability.
- Internal packages can be reorganized without treating every import as public.

### Costs and constraints

- Public schema and CLI changes require migration and communication work.
- Structured outputs need versioned fixtures or contract tests.
- Compatibility claims must be documented narrowly enough to remain testable.
- The sync removal requires a deliberate release note even though its code is
  removed as architectural cleanup.

## Alternatives considered

### Preserve every observable behavior

Rejected because incidental module paths, formatting, and implementation quirks
would prevent the necessary architecture migration.

### Declare no compatibility before a future stable release

Rejected because existing repositories and automation already contain durable
user data and deserve explicit handling.

### Rewrite old documents automatically on read

Rejected because a read operation must not create an unreviewed repository diff
or make rollback difficult.

## Related decisions

- ADR-0002 identifies synchronization removal as intentional.
- ADR-0003 defines canonical schema authority.
- ADR-0005 supplies transactional migration guarantees.
- ADR-0006 distinguishes stable error categories from presentation prose.

## Migration boundary

This ADR does not promise compatibility for an interface that has never been
documented as public. A compatibility inventory and release plan precede the
production refactor.

