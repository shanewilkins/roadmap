# ADR-0009: Assign configuration ownership and scope

- Status: Accepted
- Date: 2026-08-10
- Scope: Project policy, user preferences, secrets, runtime overrides, and configuration injection

## Context

Configuration currently crosses CLI, domain, coordination, persistence, security,
Git, and provider concerns. A single ambient configuration object makes hidden
dependencies easy, gives unrelated code access to secrets, and makes it unclear
whether a value is shared project policy or one user's preference.

ADR-0001 requires dependencies to be explicit and ADR-0002 assigns Git remotes,
authentication, and transport to Git. Configuration must preserve those
boundaries and remain compatible with the versioned canonical storage and
migration rules selected by ADR-0003 and ADR-0007.

## Decision

Every configuration key has one declared scope. A value is invalid when supplied
through a scope that is not authorized for that key.

### Project configuration

Shared project policy lives in the versioned, canonical
`.roadmap/config.yaml` document and is committed with the repository.

Project configuration contains behavior that collaborators must interpret
consistently, such as supported schema choices and project-level workflow
policy. It does not contain machine-specific paths, presentation preferences,
credentials, tokens, Git remotes, or Git transport policy.

### User configuration

User preferences live outside the repository in the platform-appropriate user
configuration location. They are limited to keys explicitly declared
user-scoped, primarily presentation and local convenience preferences.

User configuration cannot override project invariants or change the meaning of
canonical data for one collaborator.

### Secrets

Secrets live only in a supported environment variable or the system credential
facility. They are never written to project or user configuration, canonical
documents, projections, exports, diagnostics, or telemetry.

Roadmap does not store Git remote credentials or synchronization-backend
credentials. Git owns its remotes, credentials, authentication helpers, and
transport configuration under ADR-0002.

### Runtime and CLI values

Documented environment variables may supply secrets and explicitly approved
runtime values. CLI options may override only keys declared overridable for one
invocation. Neither mechanism can bypass a domain invariant or silently alter a
canonical schema.

There is no universal precedence chain across unrelated scopes. Configuration
is resolved by declared key scope:

1. built-in defaults establish a complete valid base;
2. project-scoped keys come from project configuration;
3. user-scoped keys may come from user configuration;
4. documented environment values apply only to environment-enabled keys; and
5. an explicit CLI value has highest precedence only for a key that permits a
   per-invocation override.

### Loading and injection

Bootstrap discovers, loads, validates, and resolves configuration once for a CLI
invocation. It creates an immutable typed configuration snapshot and supplies
collaborators only the specific typed settings they need.

- Domain never reads configuration, environment variables, global settings, or
  filesystem locations.
- Application does not query a global configuration service. A use case receives
  a narrow settings value only when behavior genuinely varies by configuration.
- Adapters receive boundary-specific settings during construction.
- Configuration parsing, filesystem discovery, environment access, and keyring
  access remain adapter concerns coordinated by Bootstrap.
- Invalid configuration fails before a mutating use case starts.

Configuration schemas are versioned. Normal reads do not rewrite configuration,
and migrations follow ADR-0007.

## Consequences

### Positive

- Project behavior is reproducible across collaborators.
- Personal preferences do not pollute committed state.
- Secrets and Git policy remain outside canonical Roadmap data.
- Domain and Application dependencies become visible in constructors and use
  case inputs.
- Configuration tests can cover each scope and override rule independently.

### Costs and constraints

- Existing keys require classification and migration.
- Code that reads ambient settings must accept explicit typed values.
- Some historically convenient overrides will be rejected because they would
  change shared project meaning.
- Bootstrap must report the source and scope of invalid non-secret values without
  exposing sensitive content.

## Alternatives considered

### One merged global configuration object

Rejected because it obscures ownership, exposes unrelated values broadly, and
allows user preferences to override shared policy accidentally.

### Store every setting in the repository

Rejected because machine preferences and secrets are not portable project state.

### Let every module read environment variables directly

Rejected because it creates hidden process-global dependencies and bypasses
schema validation.

### Duplicate Git configuration in Roadmap

Rejected because ADR-0002 makes Git the sole owner of repository transport and
authentication.

## Related decisions

- ADR-0001 defines Bootstrap and dependency direction.
- ADR-0002 assigns synchronization and remote configuration to Git.
- ADR-0003 makes project configuration a versioned canonical document.
- ADR-0006 defines boundary validation and error translation.
- ADR-0007 defines configuration compatibility and migration.

## Migration boundary

This ADR does not relocate or rename current keys. The refactor implementation
specification requires a key-by-key scope and compatibility inventory before the
configuration slice moves.
