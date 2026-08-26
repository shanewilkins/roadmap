# Runtime dependency boundaries

Roadmap 0.2 has three direct runtime dependencies. Each belongs to a named
adapter boundary; Domain and Application import none of them.

| Dependency | Owning boundary | Retained purpose |
| --- | --- | --- |
| Click | `roadmap.adapters.inbound.cli` | Parse commands and options, dispatch requests, enforce confirmation, and assign process exit behavior. |
| Rich | `roadmap.adapters.inbound.cli` | Render interactive terminal tables, panels, Markdown, and styled diagnostics. Machine-readable output does not depend on Rich rendering. |
| PyYAML | `roadmap.adapters.outbound.persistence` and the configuration CLI adapter | Parse and serialize versioned canonical/configuration YAML. The CLI adapter uses it only to render and parse declared configuration values. |

Bootstrap performs manual constructor injection and uses only the standard
library. SQLite support uses Python's standard-library `sqlite3` module and is
a disposable outbound projection, not a separate runtime package or source of
truth.

New runtime dependencies require all of the following:

1. a retained user or technical requirement that cannot be met reasonably by
   the standard library or an existing dependency;
2. one named owning boundary;
3. no import from Domain or Application unless a separate ADR changes the
   architecture rule;
4. package, security, type, and supported-platform verification; and
5. removal when the owning behavior is removed.

The dependency lock may contain transitive packages required by these three
libraries and by development tooling. A package appearing in the lock does not
make it an approved direct runtime dependency.
