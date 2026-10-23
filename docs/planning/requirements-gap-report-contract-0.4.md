# Requirement gap report contract for 0.4

`roadmap requirement gaps` is a read-only calculation over canonical records.
Terminal output and versioned JSON render the same immutable Application report.
Neither form writes canonical Markdown or relies on the disposable SQLite
projection.

## Eligible populations

- The default population is every visible requirement and visible issue.
- Governed intent is a requirement with a current acceptance: Accepted, In
  Progress, or Verified without a later semantic intent change.
- Archived issues do not plan or complete current work. A relation to a retained
  archived requirement or issue is still resolvable and therefore is not a
  broken link.
- Maintenance work is justified without a product requirement only when the issue
  has the exact `maintenance` label and a nonempty Markdown body explaining it.

## Exact categories

- **Accepted without planned work**: governed intent has no visible, existing
  `implemented-by` target.
- **Work without requirement or maintenance rationale**: a visible issue is not
  linked from governed intent and does not satisfy the maintenance rule.
- **Implemented awaiting verification**: governed intent has one or more
  implementation links, every target is visible and exists, every linked issue is
  Closed, and the requirement is not Verified.
- **Stale evidence**: a visible requirement retains evidence that no longer
  applies to active governed intent, including withdrawn, deferred, rejected, or
  semantically changed intent.
- **Failed or incomplete evidence**: the latest criterion result in the current
  acceptance includes `fail` or `incomplete`.
- **Broken links**: a canonical relation target does not exist in the appropriate
  requirement, issue, project, or milestone repository.
- **Blocked requirements**: a dependency is missing or not Verified, or a linked
  visible issue is explicitly Blocked.

Each category contains deterministically sorted IDs and sorted reasons. Counts
are derived from those category tuples rather than calculated independently.

## Grouped coverage

The report derives journey, priority, milestone, and release groups from the
already classified IDs. Requirement journey and priority come from requirement
metadata; milestone comes from `milestone-target`; release comes from
`release:<value>` labels on linked visible issues. Unjustified issues can
contribute their own release labels but are `unassigned` for requirement-owned
dimensions. Missing dimension values are reported as `unassigned`.

An ID may appear in more than one release group when its linked work spans
releases. Each group lists exact IDs for all seven categories and derives counts
from those lists. Grouping never changes the global category population.
