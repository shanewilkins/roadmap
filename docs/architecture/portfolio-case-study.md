# Case study: rescuing Roadmap CLI through controlled contraction

## The problem

Roadmap began as a useful local planning idea buried in a generated codebase of
54,225 production Python code lines across 504 files. It had overlapping data
models, duplicate persistence/configuration/health paths, speculative provider
sync, misleading release claims, and no enforceable architecture. Installation
was also broken by an unrelated runtime package that shadowed the CLI module.

A rewrite in Rust would have changed the language without first resolving the
product and ownership problems. The project instead chose a measurable salvage:
preserve valuable user journeys and data, delete unsupported scope, and replace
the internal architecture incrementally behind executable contracts.

## Constraints and decisions

- Canonical Markdown/YAML is the only durable authority; SQLite is a disposable
  local projection.
- Git owns transport. Roadmap performs no provider synchronization and stores no
  provider credentials.
- Domain and Application code are framework-free. Inbound/outbound Adapters own
  translation and Bootstrap permanently owns composition.
- Every phase ends in a green checkpoint and explicit maintainer approval.
- Production CLOC may not increase between accepted phases without an explicit
  exception.
- Compatibility is decided item by item: preserve, replace with migration,
  remove explicitly, or keep internal.

## Execution

Thirteen phases first repaired lifecycle behavior, then inventoried the public
contract, installed architecture policy, introduced a composition root and pure
domain/application boundaries, replaced persistence with atomic canonical
writes plus rebuildable projection, migrated complete issue/planning/operations
journeys, added a bounded 0.1.1 workspace migration, removed remote sync, and
finally deleted the legacy ownership zones.

The final hardening phase added adversarial failure, concurrency, projection
corruption, migration, output, offline, artifact, test-quality, and measured
performance gates. Release documentation explicitly separates preparation from
the irreversible version/tag/publish actions.

## Measured result

| Metric | Initial baseline | Phase 13 candidate | Change |
|---|---:|---:|---:|
| Production Python code lines | 54,225 | 9,200 | -45,025 (-83.0%) |
| Production Python files | 504 | 106 | -398 (-79.0%) |
| Test modules | 540 | 52 | -488 (-90.4%) |
| Architecture exceptions | not enforced | 0 | enforceable |
| Runtime dependencies | sprawling mixed set | 3 | Click, Rich, PyYAML |
| Average cyclomatic complexity | not governed | A (3.47) | enforced in CI |

The smaller suite is not a claim that deletion creates quality. Its 212 source
test functions (4,892 Python code lines) concentrate on retained behavior, with
an installed cumulative
journey and policy preventing silent skips, disabled files, duplicate module
names, stale imports, and tautological assertions. The 500-issue performance
envelope defines honest regression ceilings rather than unverifiable speed
claims.

## What this demonstrates

The portfolio value is the engineering judgment: refusing a fashionable
rewrite, reducing product scope, making data authority explicit, protecting
compatibility with a one-time migration, turning architecture into executable
policy, and using evidence to delete roughly five-sixths of production code.
The result is a comprehensible offline tool and a release process that can say
what is supported, what was removed, and how to recover when something fails.

Markdown documentation remains intentional. A documentation framework would
add build and navigation machinery without improving this repository-sized
audience's most important problem: accuracy. The project can adopt a generated
site later if readership or API-reference needs provide measured justification.
