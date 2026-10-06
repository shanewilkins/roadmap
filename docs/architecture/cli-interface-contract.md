# CLI interface contract and correctness plan

- Accepted: 2026-10-06, following the maintainer's interface review.
- Status: implemented in the step-three correctness pass; legacy spellings are deprecated through 0.3 and retired at the 0.4 boundary.
- Scope: commands, options, selection, side effects, diagnostics, compatibility.

Step-three outcomes, compatibility decisions and evidence are recorded in
[CLI correctness closeout](cli-correctness-closeout.md) and the checked
[command/option behavior matrix](cli-behavior-matrix.json). Step-one and step-two
evidence documents retain the historical findings that motivated the fixes.

Step-two selections, output evidence and unmet machine-interface contracts are
tracked in [CLI query/output evidence](cli-query-output-evidence.md).

This contract records step zero of the CLI correctness pass. It is a target,
implemented with the compatibility exceptions described below. The existing
[compatibility inventory](compatibility-inventory-0.2.csv) continues to describe
the live interface and remains checked by the existing policy tests. Update
that inventory alongside implementation, not ahead of it.

## Shared contracts

### Verbose and debug

`--verbose/-v` explains normal operation. Retain it on issue, milestone, and
project archive/restore, backup cleanup, migration, and health repair. Useful
information includes candidate selection, reasons for skipping candidates,
validated migration stages, and completed repair stages. Each explanation
must describe an actual decision or completed stage; it must not claim a
mutation occurred during preview.

All verbose explanations go to stderr. Turning verbosity on must leave stdout,
structured schemas, selected records, validation, exit status, and side effects
unchanged. It does not enable tracebacks. Other current verbose occurrences
are deprecated, rather than retained as switches that do nothing.

Global `--debug` displays unexpected-error tracebacks, including command import
and workspace startup failures. Expected user/input failures remain concise.
Tracebacks go to stderr and omit local-variable dumps. Verbose and debug can
be used together. Use standard Python logging for internal diagnostics; no
JSON logging, telemetry, or new logging dependency is required.

### Representation and destination

`--format` selects a representation; `--output PATH` selects a report file.
Never use `--output` to mean a format. Keep current supported format sets except
the explicit consolidations below; every advertised format must be functional.
Report-file creation refuses existing destinations and reports write failures.
Warnings, progress, and destination acknowledgments go to stderr.

`--print-id` on issue/project/milestone creation emits only the complete created
ID on stdout. Warn on stderr if canonical data committed but cache or optional
Git work failed. Report the committed outcome truthfully so users can inspect
the entity before retrying a partially completed workflow.

Single-entity `view --format json` must expose a versioned representation;
issue inspection includes recorded history. Empty structured collections keep
their schema. Column selection and sorting must agree with the advertised
representation and produce valid output for zero, one, and multiple records.

### Confirmation, overrides, and previews

`--yes` skips confirmation only. It never skips validation or integrity guards.
`--force` requests a named, documented override, not implicit consent:

- Project close: allow closing with open milestones, without changing them.
- Milestone close: allow closing with open issues, without changing them.
- Git branch operations: permit the documented dirty-worktree condition;
  do not silently replace an existing branch.
- Initialization: retain only explicitly documented reinitialization behavior;
  do not overwrite canonical documents or accept an unsupported schema.

Project close retains confirmation separately controlled by `--yes`. Archive retains `--force` as a bounded override allowing non-completed records;
`--yes` is its independent consent option and never overrides that guard.
Restore and cleanup use `--yes`, replacing their confirmation-only `--force`.
During 0.3, archive and project close preserve legacy force-as-consent behavior
with a warning; in 0.4 request both behaviors with `--force --yes`. Initialization
is idempotent and has no legitimate force override: its ineffective `--force`
is deprecated through 0.3, rather than pretending it changes behavior.
Compatibility handling must not silently change the meaning of an old spelling.

`--dry-run` validates and describes a mutation without modifying canonical data,
configuration, projections, recovery journals, backups, or Git branches. Prefer
reporting a blocker to giving a plan that could not actually execute. Tests must
check bytes and relevant filesystem/Git state, not just a printed preview label.

### Selection and updates

Use complete IDs or existing unambiguous selectors. Ambiguous selection fails
with candidate choices. Different filters narrow results together; repeated
values of the same supported filter match any of those values. Reject conflicting
selectors rather than silently choosing precedence. Preserve explicit lifecycle
scope and documented shortcut filters.

Setting and clearing the same field in one call is an error. Omitted fields
remain unchanged; explicit clearing removes a value. Repeatable label additions
and removals operate on the existing label set; the same label in both is a
conflict. Invalid dates, negative estimates, invalid statuses, missing entities,
and dependency cycles fail before partial writes.

Explicit branch-only options require a requested branch action. Defaults for
checkout or other paired options must not count as an explicit request when
checking combinations. Optional Git failure after canonical commit must report
the two outcomes separately.

### Workspace selection

Global `--workspace PATH` identifies the canonical workspace directory itself
(for example `/work/project/.roadmap`), not its parent repository. Explicit
selection wins over default discovery; unreadable or invalid explicit paths
must not silently fall back to another workspace. Workspace initialization may
create that destination. A conflicting explicit `init --name` is a usage error.
Normal commands default to the current directory's `.roadmap`; they do not
automatically select a parent workspace. Initialization always targets the
current directory unless `--workspace` selects an exact destination. Explicit
selection overrides both defaults and never falls back. Relative paths are
relative to the current working directory; Git operates in the selected
workspace's parent directory; informational help/version must remain independent
of workspace validity.

## Preferred roster

The table is exhaustive for preferred command paths and explicit options.
Click's standard `--help` is available where applicable. Existing short aliases
remain where listed. Parameter type names are descriptive; choices are listed
in braces. Required creation fields and defaults remain part of the live
contract unless explicitly changed here. Commands with no options still need
behavioral evidence for arguments, selection, errors, and side effects.

| Command | Positional arguments | Options |
|---|---|---|
| `roadmap` | — | `--version`; `--debug`; `--workspace PATH` |
| `roadmap analysis` | — | — |
| `roadmap analysis critical-path` | — | `--milestone/-m TEXT`; `--include-closed`; `--format {plain,json,csv}`; `--output/-o FILE` |
| `roadmap cleanup` | — | `--keep INTEGER`; `--days INTEGER`; `--dry-run`; `--verbose/-v`; `--yes/-y` |
| `roadmap config` | — | — |
| `roadmap config explain` | KEY | `--format {plain,json}` |
| `roadmap config get` | KEY | — |
| `roadmap config reset` | — | `--project`; `--yes` |
| `roadmap config set` | KEY; VALUE | `--project` |
| `roadmap config view` | — | `--project`; `--level {user,project,merged}` |
| `roadmap data` | — | — |
| `roadmap data export` | — | `--format {json,csv,markdown}`; `--output/-o FILE`; `--filter TEXT` |
| `roadmap git` | — | — |
| `roadmap git branch` | ISSUE_ID | `--checkout/--no-checkout`; `--force` |
| `roadmap git link` | ISSUE_ID | — |
| `roadmap git status` | — | — |
| `roadmap health` | — | — |
| `roadmap health fix` | — | `--verbose/-v`; `--format/-f {plain,json}`; `--fix-type/-t {projection,recovery}` (required); `--dry-run`; `--yes/-y` |
| `roadmap health scan` | — | `--format/-f {plain,json,csv}`; `--filter-entity/-e {issue,milestone,project} (repeatable)`; `--filter-severity/-s {info,warning,error,critical} (repeatable)`; `--with-dependencies/--no-dependencies`; `--summary-only`; `--output/-o PATH` |
| `roadmap init` | — | `--name/-n TEXT`; `--project-name/-p TEXT`; `--description/-d TEXT`; `--skip-project`; `--dry-run`; `--force/-f` |
| `roadmap issue` | — | — |
| `roadmap issue archive` | ISSUE_ID (optional) | `--all-closed`; `--orphaned`; `--list`; `--dry-run`; `--verbose/-v`; `--yes/-y`; `--force` (bounded lifecycle override) |
| `roadmap issue block` | ISSUE_ID | `--reason/-r TEXT` |
| `roadmap issue close` | ISSUE_ID | `--reason/-r TEXT`; `--record-time/-t`; `--date TEXT` |
| `roadmap issue comment` | — | — |
| `roadmap issue comment add` | ISSUE_ID; BODY | `--author/-a TEXT`; `--reply-to/-r INTEGER` |
| `roadmap issue comment list` | ISSUE_ID | `--format/-f {text,json}` |
| `roadmap issue create` | — | `--print-id`; `--title TEXT`; `--priority/-p {critical,high,medium,low}`; `--type/-t {feature,bug,other}`; `--milestone/-m TEXT`; `--assignee/-a TEXT`; `--labels/-l TEXT (repeatable)`; `--estimate/-e FLOAT`; `--depends-on TEXT (repeatable)`; `--blocks TEXT (repeatable)`; `--content/-d TEXT`; `--git-branch`; `--checkout/--no-checkout`; `--branch-name TEXT`; `--force`; `--due-date DATE` |
| `roadmap issue delete` | ISSUE_ID | `--yes/-y` |
| `roadmap issue deps` | — | — |
| `roadmap issue deps add` | ISSUE_ID; DEPENDENCY_ID | — |
| `roadmap issue deps remove` | ISSUE_ID; DEPENDENCY_ID | — |
| `roadmap issue deps update` | ISSUE_ID; OLD_DEPENDENCY_ID; NEW_DEPENDENCY_ID | — |
| `roadmap issue list` | FILTER_TYPE (optional) | `--milestone/-m TEXT`; `--backlog`; `--unassigned`; `--open`; `--blocked`; `--next-milestone`; `--assignee/-a TEXT`; `--my-issues`; `--status/-s {todo,in-progress,blocked,review,closed}`; `--priority/-p {critical,high,medium,low}`; `--issue-type/-t {feature,bug,other}`; `--overdue`; `--search TEXT`; `--scope {visible,closed,archived,all}`; `--format {rich,plain,json,csv,markdown}`; `--columns TEXT`; `--sort-by TEXT`; `--filter TEXT` |
| `roadmap issue progress` | ISSUE_ID; PERCENTAGE | — |
| `roadmap issue restore` | ISSUE_ID (optional) | `--all`; `--status {todo,in-progress,blocked,review,closed}`; `--dry-run`; `--verbose/-v`; `--yes/-y` |
| `roadmap issue start` | ISSUE_ID | `--date TEXT`; `--git-branch/--no-git-branch`; `--checkout/--no-checkout`; `--branch-name TEXT`; `--force` |
| `roadmap issue unblock` | ISSUE_ID | `--reason/-r TEXT` |
| `roadmap issue update` | ISSUE_ID | `--title TEXT`; `--priority/-p {critical,high,medium,low}`; `--status/-s {todo,in-progress,blocked,review,closed}`; `--assignee/-a TEXT`; `--milestone/-m TEXT`; `--description/-d TEXT`; `--estimate/-e FLOAT`; `--reason/-r TEXT`; `--clear-assignee`; `--clear-milestone`; `--clear-estimate`; `--due-date DATE`; `--clear-due-date`; `--add-label LABEL (repeatable)`; `--remove-label LABEL (repeatable)` |
| `roadmap issue view` | ISSUE_ID | `--format {plain,json}` |
| `roadmap migrate` | — | `--dry-run`; `--yes/-y`; `--format {plain,json}`; `--verbose/-v` |
| `roadmap milestone` | — | — |
| `roadmap milestone archive` | MILESTONE_NAME (optional) | `--all-closed`; `--list`; `--dry-run`; `--verbose/-v`; `--yes/-y`; `--force` (bounded lifecycle override) |
| `roadmap milestone assign` | ISSUE_ID; MILESTONE_NAME | — |
| `roadmap milestone close` | MILESTONE_NAME | `--force` |
| `roadmap milestone create` | — | `--title/-t TEXT`; `--description/-d TEXT`; `--due-date TEXT`; `--project/-p TEXT`; `--print-id` |
| `roadmap milestone delete` | MILESTONE_ID | `--yes/-y` |
| `roadmap milestone kanban` | MILESTONE_NAME | — |
| `roadmap milestone list` | — | `--overdue`; `--format {rich,plain,json,csv,markdown}`; `--columns TEXT`; `--sort-by TEXT`; `--filter TEXT` |
| `roadmap milestone progress` | MILESTONE_NAME (optional) | `--method {effort_weighted,count_based}` |
| `roadmap milestone restore` | MILESTONE_NAME (optional) | `--all`; `--dry-run`; `--verbose/-v`; `--yes/-y` |
| `roadmap milestone update` | MILESTONE_ID | `--name TEXT`; `--description/-d TEXT`; `--due-date TEXT`; `--status {open,closed}`; `--project/-p TEXT`; `--clear-project`; `--clear-due-date` |
| `roadmap milestone view` | MILESTONE_NAME | `--status {todo,in-progress,blocked,review,closed} (repeatable)`; `--priority {critical,high,medium,low} (repeatable)`; `--only-open`; `--format {plain,json}` |
| `roadmap project` | — | — |
| `roadmap project archive` | PROJECT_NAME (optional) | `--all-closed`; `--list`; `--dry-run`; `--verbose/-v`; `--yes/-y`; `--force` (bounded lifecycle override) |
| `roadmap project close` | PROJECT_ID | `--force`; `--yes/-y` |
| `roadmap project create` | — | `--title/-t TEXT`; `--description/-d TEXT`; `--repository/-r TEXT`; `--owner TEXT`; `--priority {critical,high,medium,low}`; `--print-id` |
| `roadmap project delete` | PROJECT_ID | `--yes/-y` |
| `roadmap project list` | — | `--status {planning,active,on-hold,completed,cancelled}`; `--owner TEXT`; `--priority {critical,high,medium,low}`; `--overdue`; `--format {rich,plain,json,csv,markdown}`; `--columns TEXT`; `--sort-by TEXT`; `--filter TEXT` |
| `roadmap project restore` | PROJECT_NAME (optional) | `--all`; `--dry-run`; `--verbose/-v`; `--yes/-y` |
| `roadmap project update` | PROJECT_ID | `--name TEXT`; `--description/-d TEXT`; `--repository/-r TEXT`; `--status {active,inactive,completed}`; `--owner TEXT`; `--priority {critical,high,medium,low}`; `--clear-owner` |
| `roadmap project view` | PROJECT_ID | `--format {plain,json}` |
| `roadmap status` | — | `--format/-f {rich,plain,json,csv,markdown}`; `--output/-o FILE` |
| `roadmap today` | — | — |

## Compatibility and consolidation roster

Deprecation happens in step three, with migration guidance and a release
boundary under ADR-0007. No deletion of a public spelling is implied by merely
recording this target. Emit compatibility warnings on stderr; do not corrupt
machine output. Record incompatible legacy behavior explicitly.

| Current surface | Preferred surface or disposition |
|---|---|
| `health check` | Compatibility entry point for default `health scan`. |
| Bare `health` options | Default scan entry point; prefer `health scan` for options. |
| `health db-integrity` | Deprecate duplicate diagnosis; use `health scan`. |
| `health scan --output FORMAT` | Deprecate format-valued spelling; use `--format FORMAT`. It conflicts with the new file-valued option, so do not silently reinterpret old values. |
| `analysis critical-path --export FORMAT` | Compatibility spelling for `--format FORMAT`. |
| `milestone recalculate --method` | Compatibility command for `milestone progress --method`; derived progress remains read-only. |
| Archive/project close `--force` | Retain lifecycle override; deprecate implicit consent through 0.3, then require `--yes` for consent in 0.4. |
| Restore/cleanup `--force` | Deprecate confirmation shortcut through 0.3; use `--yes`. |
| Other current `--verbose/-v` occurrences | Deprecate; no normal-operation explanation contract is assigned to them. |
| `init --interactive/--non-interactive`, `--yes`, `--force` | Deprecate through 0.3; initialization is noninteractive and idempotent. |
| `init --template`, `--template-path` | Deprecate; templates deferred. |
| `cleanup --backups-only` | Deprecate; backup cleanup is always scoped to backups. |
| Cleanup `--check-folders`, `--check-duplicates`, `--check-malformed` | Move useful diagnostics into health findings; provide replacement guidance for each check. |
| Health `--details`, `--group-by`, `--show-ids`, `--limit`, `--json` | Deprecate ineffective controls and duplicate representation selection; use scan filters, `--summary-only`, and `--format json`. |
| Separate health dependency toggles | One paired `--with-dependencies/--no-dependencies`. |
| Legacy health fix types | Only projection and recovery are executable targets. Retire unsupported choices and `all`/`data_integrity` shorthand with explicit guidance; never pretend canonical repair occurred. |
| Kanban `--compact`, `--no-color` | Deprecate while there is one uncolored layout. |

The table preserves current unrelated spellings and choice sets. Differences
such as project update's legacy `inactive` spelling versus listing's `on-hold`,
comment output's `text` spelling versus `plain`, and creation `--title` versus
update `--name` need explicit clarification in step three. They are not license
to silently broaden statuses, change persisted values, or introduce aliases.

## Missing capabilities accepted for this pass

- Explicit workspace selection.
- Project/milestone ID-only creation and single-entity structured inspection.
- Explicit clearing of issue assignee, milestone, estimate, and due date;
  milestone project and due date; and project owner.
- Repeatable issue label additions/removals.
- Issue creation/update due dates and project creation/update owner and priority.

These require application-layer support and immutable update semantics where
currently missing; parsing a new Click option alone is not completion. Templates,
interactive editors, entity completion, and cosmetic board modes remain deferred.

## Delivery and evidence

0. Agree on and record this interface roster. Complete; this document is the
   approved target, with the current compatibility inventory kept separate.
1. Prove mutation safety: exact selection, confirmation, overrides, previews,
   dates, relationships, and Git outcomes. Include refusal and retry paths.
2. Prove query/output behavior: distinguishing records, exact filtering/sorting,
   representations, columns, destinations, and conflicting combinations.
3. Implement, clarify, or deprecate each target difference, including useful
   verbose output. Update live compatibility inventory and documentation with
   each change and rerun the applicable evidence from steps one and two.

For each command/option, the behavior matrix must identify its contract,
disposition, evidence test IDs, and unresolved gaps. Distinguish helper unit tests
from actual command journeys. Do not mark a row verified because it appears in
help, is accepted by Click, or is covered by a signature test. Require concrete
outcome assertions with positive and negative cases; shared tests can cover
common mechanisms, but command wiring still needs evidence.

Guard new live options against unreviewed roster/evidence drift when the matrix
is introduced. Every preferred surface needs implemented behavior and evidence;
every compatibility surface needs tested migration behavior. Statement coverage
remains a supporting signal, not the completion criterion for this pass.

## Resolved option semantics

- Shared list `--filter` supports equality (`column=value`, comma-separated AND).
  Other operators are explicitly rejected before querying; they are not ignored.
- Sort keys apply left to right with independent directions; missing values sort
  last for either direction. JSON lists preserve full column definitions and
  selected-column metadata; row cells follow the requested selection and order.
- Health `--summary-only` retains counts and severity-derived exit status but
  removes detailed findings in plain, JSON and CSV output.
- Project update's legacy `inactive` maps to persisted `on-hold`; it does not
  introduce a separate state. Creation uses `--title`, update uses `--name`;
  explicitly empty names are invalid. Comment lists retain `text` for plain text.
- `--output plain|json|csv` on health scan remains format-valued through 0.3 with
  a warning. Use `--format FORMAT --output PATH`; use `./json` (similarly `./csv`
  or `./plain`) to name a destination with a reserved legacy token. Conflicting
  explicit formats are refused. Bare health runs the default read-only scan.
- Health repair requires an explicit `projection` or `recovery` target. Recovery
  may leave a projection warning; preview/apply projection repair separately.
- Preview with pending canonical transactions refuses without replay or cleanup;
  the error points to `health fix --fix-type recovery --dry-run`.

Archive list mode refuses entity/batch selectors and mutation controls. Verbose
listing reports its read-only lifecycle selection. Health group options apply to
bare health only; place scan/fix/check options after the subcommand, otherwise
the CLI refuses rather than dropping them.
