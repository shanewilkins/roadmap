# Error diagnostics and deferred verbosity work

## Failure behavior

Missing configuration files use defaults. Permission errors and other read
failures are errors, not evidence that configuration is absent.

Unexpected CLI errors exit nonzero and go to stderr. Use
`roadmap --debug COMMAND` to display their traceback, including command-loading
and workspace-startup failures. Expected validation errors remain concise.
Debug tracebacks omit local-variable dumps; exception messages and source lines
can still contain sensitive information, so inspect diagnostics before sharing.

Projection refresh failures after a canonical commit use standard Python logging
with exception information. The mutation remains successful: the canonical data
was saved. The CLI warns on stderr and offers a repair preview. Logging does not
create files, configure the root logger, add JSON formatting, or send telemetry.

## Verbosity disposition (completed)

Archive/restore, cleanup, migration and health repair now explain validated
selection or completed stages on stderr. They keep stdout, exits and side effects
unchanged. The other former no-op verbose flags warn that they are deprecated
through 0.3 and removed in 0.4; they do not enable debug tracebacks.

See the [interface contract](cli-interface-contract.md),
[closeout](cli-correctness-closeout.md), and checked
[behavior matrix](cli-behavior-matrix.json) for the supported roster and tests.
