# Analysis-only Vulture whitelist; never imported or shipped in the package.
# ruff: noqa: F821, B018
# Click supplies debug to the group callback; the error handler reads ctx.params.
_.debug
# Retained compatibility options for the plain-text board; both are no-ops.
_.compact
_.no_color
# Positional context-manager arguments required by the Application port.
_.exc
_.traceback
