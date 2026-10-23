# Explainable next-work policy for 0.4

Implements UR-063/TR-050. The maintainer approved the revised policy before
implementation: **critical defects outrank merely overdue work**. This is a
local, explicit product policy, not a ranking standard imposed by a Git host.

## Read-only public surface

```sh
roadmap next-work
roadmap next-work --at 2026-10-23T13:00:00-05:00 --format json
roadmap next-work --limit 5
```

The Application reads one canonical unit of work with `read_only=True`. It never
accepts requirements, updates priorities, closes issues, writes evidence, or
contacts a provider. SQLite is not authoritative. Requirements adoption is not
required: issue-only workspaces can recommend justified maintenance without
creating requirement documents or upgrading configuration.

Planning time comes from the injected Application clock or an explicit `--at`
ISO-8601 timestamp with a UTC offset. Date-only and offset-free input is rejected
rather than assuming the machine's timezone. The report normalizes `as_of` to UTC.
`--limit` must be positive and applies only after the full recommendation order;
`recommended_total`, current work, blocked work, and unblocking values remain
untruncated.

Terminal and schema-version-1 JSON render the same `roadmap.next-work:v1` report.
JSON includes `as_of`, `current_work`, `recommended`, `blocked`, and
`recommended_total`. Every action exposes identity, title, action kind, urgency,
effective priority/deadline with explicit sources, requirement/milestone scope,
reasons, blockers, direct unblocking count, and exact IDs it would unblock.

## Eligibility and action kinds

All populations exclude archived source artifacts and Closed issues.
Governed intent is visible Accepted, In Progress, or Verified intent with current
acceptance, using the same eligibility helper as gap reporting.

- `plan-requirement`: visible unverified requirement with no existing visible
  implementation work. Ungoverned Draft/stale intent is shown as blocked, not
  automatically accepted. Deferred, Rejected, and Verified requirements do not
  generate requirement actions.
- `verify-requirement`: visible unverified requirement with visible implementation
  work. It becomes actionable only when all linked issues exist, are visible,
  and are Closed, and requirement dependencies are satisfied. Missing, failed,
  or incomplete criterion evidence is explained: this is a recommendation to
  perform verification work, not a claim that verification will already pass.
- `start-issue`: Todo implementation linked from at least one visible governed
  requirement.
- `review-issue`: an otherwise eligible issue in Review.
- `start-maintenance`: Todo issue without a governing requirement, with exact
  `maintenance` label and a nonempty Markdown rationale.

Unjustified issues are visible in `blocked`, not ranked as eligible. In Progress
eligible issues appear in `current_work`; issues with blockers stay in `blocked`
regardless of priority, deadline, or recorded progress.

An issue dependency must exist and be Closed. Retained archived Closed issue
dependencies can satisfy completion, but an archived open issue cannot.
A requirement dependency must be visible and effectively Verified. Missing
targets and unresolved dependencies block, including dependencies inherited from
every governing requirement of an issue. Explicit Blocked issue status requires
explicit unblocking even after its dependencies close. Broken canonical
requirement relations also block the affected action.

## Deterministic lexicographic order

No weighted score or duration heuristic is used. Sort by:

1. Urgency band:
   1. Critical defect: bug issue with effective Critical priority.
   2. Overdue: effective deadline strictly earlier than `as_of`.
   3. Finish/review: requirement verification or issue review.
   4. Normal eligible work.
2. Earliest effective deadline; unknown dates last.
3. Priority: Critical, High, Medium, Low.
4. Highest direct unblocking value.
5. Action kind: verify requirement, review issue, start implementation, plan
   requirement, start maintenance.
6. Entity UUID, then entity type as a defensive cross-type tie-breaker.

Effective issue priority is the highest explicit priority on the issue or any
governing requirement. Requirement actions use their own priority. All original
source priorities remain visible and unchanged.

Effective issue deadline is the earliest of its own due date and its visible open
milestone's due date. Requirement actions use their visible open milestone
target's due date. Closed/archived milestone dates do not drive recommendations.
An unknown deadline means unavailable in canonical data, not proof of no remote
deadline. Estimates do not affect eligibility or order; missing issue estimates
are explicitly reported without a fabricated default.

Unblocking value counts distinct direct action IDs whose **only** remaining
prerequisite would be satisfied by closing this issue or verifying this
requirement. It does not count all graph descendants, actions with another
blocker, or duplicate edges. Planning a requirement does not verify it and
therefore receives no hypothetical verification-unblocking credit.

## Approved examples

With no other blockers:

| Candidate | Result |
| --- | --- |
| Critical bug without a deadline | First, ahead of overdue medium work |
| Medium feature overdue yesterday | After critical defect, before ordinary review |
| High requirement ready for verification | Finish/review band |
| High implementation directly unblocking three eligible actions | Before otherwise identical high implementation with no unblocking value |
| Medium maintenance with label and rationale | Eligible normal work |
| Critical issue with an open dependency | Blocked only; never actionable |
| Two identical candidates differing only by UUID | Ascending UUID order |
| One candidate without an estimate | Still eligible; no duration assumed |

## Hosting-provider boundary

The calculation uses known local facts, not an assertion of complete remote
state. GitHub, GitLab, and Gitea differ in priority/status/date representations,
API capabilities, versions, and paid-tier availability. No new provider adapter
or synchronization is introduced here.

Future mappings must retain explicit source values/provenance and distinguish
unavailable fields from known absent values. Derived priorities, inherited
deadlines, and ranking must not silently overwrite provider fields. A remote
issue may close as duplicate, rejected, or abandoned: remote closure alone must
not be silently mapped to successful implementation, and local Closed
implementation never automatically verifies a requirement.
