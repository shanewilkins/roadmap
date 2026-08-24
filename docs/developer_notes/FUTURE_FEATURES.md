# Product direction

This file no longer maintains a speculative version-by-version feature list.
The authoritative planning inputs are:

- the [requirements registers](../requirements/README.md);
- the [0.2 public contract](../architecture/public-contract-0.2.md);
- the [0.2 architecture plan](../architecture/roadmap-0.2.md); and
- the [phased execution plan](../architecture/refactor-execution-plan.md).

## 0.2 focus

Roadmap 0.2 makes the existing local, file-first product smaller and reliable:
stable identity, canonical files, rebuildable SQLite projections, explicit
lifecycle semantics, typed configuration, predictable errors and structured
output, safe migration, and a disciplined dependency structure.

Provider synchronization, Roadmap-managed credentials, automatic Git hooks,
and commit-message mutation are outside the 0.2 product boundary.

## Post-0.2 candidates

The registers deliberately defer these directions for later product decisions:

- reversible Git-hook and explicit commit-reference automation; and
- requirements as first-class repository-native application entities; and
- application authentication and authorization if a hosted or genuinely
  multi-user Roadmap product creates a trust boundary that the operating
  system, Git, and repository-host permissions cannot satisfy.

## Road to 1.0 authentication decision gate

Roadmap remains account-free through 0.2. Local execution authority belongs to
the operating system, Git owns remote credentials, configured user identity is
descriptive rather than verified, and repository permissions and review govern
which changes are accepted.

Before 1.0, maintainers shall explicitly review whether concrete product
requirements now need application authentication. Authentication is considered
only when evidence identifies protected resources, actors, trust boundaries,
and authorization decisions that the local Git-native model cannot enforce. A
proposal must include threat modeling, credential and recovery ownership,
offline behavior, data migration, and a separate architecture decision. In the
absence of that evidence, 1.0 retains the account-free model.

Deferred means uncommitted. A candidate becomes planned only through the
governed requirement lifecycle and a compatible architecture decision.
