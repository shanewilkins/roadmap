# ADR-0006: Assign validation and error ownership by boundary

- Status: Accepted
- Date: 2026-08-10
- Scope: Validation layers, exception taxonomy, and error translation

## Context

Validation and error handling currently occur across CLI commands, parsers,
models, services, repositories, and provider code. When ownership is unclear,
rules are duplicated, business policy leaks into adapters, and callers receive
inconsistent messages or unhandled implementation exceptions.

The target architecture needs one rule for where an invalid condition is
detected and where it is translated for a user or automation client.

## Decision

Validation belongs to the innermost zone that has enough meaning to decide the
rule correctly.

### Adapter validation

Inbound and outbound adapters validate representation and boundary mechanics:

- CLI syntax, option combinations, and textual conversion;
- document syntax, schema shape, encodings, and unsupported schema versions;
- configuration representation;
- filesystem, Git, database, keyring, and external response shape; and
- translation between boundary DTOs and Application or Domain types.

Adapters do not decide business invariants merely because they see input first.

### Domain validation

Domain constructors, value objects, and methods enforce invariants that are
true for one aggregate or value in every use case. Invalid domain state cannot
be constructed through a supported Domain API.

### Application validation

Application use cases enforce contextual and cross-aggregate rules, including
existence, workspace uniqueness, relationship validity, operation preconditions,
and authorization if authorization is introduced.

Persistence detects corruption and concurrency conflicts but does not invent
business policy.

## Error model

- Domain exposes a small typed hierarchy for violated domain rules.
- Application exposes typed use-case failures, including not found, conflict,
  invalid operation, and persistence-boundary failure categories.
- Adapters translate library and operating-system failures into the relevant
  Application port error without leaking provider-specific exception types
  inward.
- Inbound adapters translate expected Domain and Application failures into
  stable exit behavior and concise actionable messages.
- Unexpected failures retain their original cause for diagnostics and are not
  mislabeled as ordinary validation errors.
- Sensitive values never appear in error messages, structured output, or normal
  logs.

Python exceptions are the default control mechanism for failures. Roadmap will
not introduce a universal `Result[T, E]` abstraction. A bounded API may use a
result value when partial success is part of its domain contract, but that does
not replace the shared exception policy.

Error messages are presentation concerns. Stable error categories and exit
codes may be public contracts under ADR-0007; Rich markup and prose do not enter
Domain or Application.

## Consequences

### Positive

- Each rule has a clear owner and one primary test location.
- Domain behavior remains independent of CLI and persistence frameworks.
- Users receive consistent failures without implementation tracebacks in normal
  operation.
- Adapters can change libraries without changing inward-facing error contracts.

### Costs and constraints

- Existing duplicate validators will need consolidation.
- Boundary mappings must preserve useful causal context.
- Catch-all exception handlers cannot substitute for typed expected failures.
- Ports must specify their failure categories as well as success behavior.

## Alternatives considered

### Validate everything in the CLI

Rejected because files and future inbound adapters could bypass business rules.

### Validate everything in Domain

Rejected because syntax, storage corruption, cross-aggregate context, and
operating-system failures are not single-aggregate business invariants.

### Return a universal result object

Rejected because it adds a parallel failure convention throughout an idiomatic
Python application without resolving ownership.

## Related decisions

- ADR-0001 defines the zones that own each validation category.
- ADR-0004 defines aggregate and cross-aggregate rule boundaries.
- ADR-0007 identifies stable public error behavior.

## Migration boundary

This ADR does not select final class names. The refactor must inventory existing
validators and error types before consolidating them.

