# Roadmap CLI Reference

*Auto-generated on 2025-10-11 14:02:26*

Complete reference for all Roadmap CLI commands with examples, options, and usage patterns.

## 📋 Table of Contents

- [`activity`](#activity)
- [`analytics`](#analytics)
- [`analytics developer`](#analytics-developer)
- [`analytics enhanced`](#analytics-enhanced)
- [`analytics quality`](#analytics-quality)
- [`analytics team`](#analytics-team)
- [`analytics velocity`](#analytics-velocity)
- [`broadcast`](#broadcast)
- [`capacity-forecast`](#capacity-forecast)
- [`comment`](#comment)
- [`comment create`](#comment-create)
- [`comment delete`](#comment-delete)
- [`comment edit`](#comment-edit)
- [`comment list`](#comment-list)
- [`dashboard`](#dashboard)
- [`export`](#export)
- [`export analytics`](#export-analytics)
- [`export issues`](#export-issues)
- [`export milestones`](#export-milestones)
- [`git-branch`](#git-branch)
- [`git-commits`](#git-commits)
- [`git-hooks-install`](#git-hooks-install)
- [`git-hooks-uninstall`](#git-hooks-uninstall)
- [`git-link`](#git-link)
- [`git-status`](#git-status)
- [`git-sync`](#git-sync)
- [`handoff`](#handoff)
- [`handoff-context`](#handoff-context)
- [`handoff-list`](#handoff-list)
- [`init`](#init)
- [`issue`](#issue)
- [`issue block`](#issue-block)
- [`issue close`](#issue-close)
- [`issue complete`](#issue-complete)
- [`issue create`](#issue-create)
- [`issue delete`](#issue-delete)
- [`issue deps`](#issue-deps)
- [`issue list`](#issue-list)
- [`issue move`](#issue-move)
- [`issue progress`](#issue-progress)
- [`issue start`](#issue-start)
- [`issue unblock`](#issue-unblock)
- [`issue update`](#issue-update)
- [Main Command](#main-command)
- [`milestone`](#milestone)
- [`milestone assign`](#milestone-assign)
- [`milestone create`](#milestone-create)
- [`milestone delete`](#milestone-delete)
- [`milestone list`](#milestone-list)
- [`milestone update`](#milestone-update)
- [`notifications`](#notifications)
- [`predict`](#predict)
- [`predict deadline`](#predict-deadline)
- [`predict estimate`](#predict-estimate)
- [`predict intelligence`](#predict-intelligence)
- [`predict risks`](#predict-risks)
- [`report`](#report)
- [`report assignee`](#report-assignee)
- [`report summary`](#report-summary)
- [`smart-assign`](#smart-assign)
- [`status`](#status)
- [`sync`](#sync)
- [`sync bidirectional`](#sync-bidirectional)
- [`sync delete-token`](#sync-delete-token)
- [`sync pull`](#sync-pull)
- [`sync push`](#sync-push)
- [`sync setup`](#sync-setup)
- [`sync status`](#sync-status)
- [`sync test`](#sync-test)
- [`team`](#team)
- [`team assignments`](#team-assignments)
- [`team members`](#team-members)
- [`team workload`](#team-workload)
- [`timeline`](#timeline)
- [`timeline critical-path`](#timeline-critical-path)
- [`timeline show`](#timeline-show)
- [`workflow-automation-disable`](#workflow-automation-disable)
- [`workflow-automation-setup`](#workflow-automation-setup)
- [`workflow-sync-all`](#workflow-sync-all)
- [`workload-analysis`](#workload-analysis)

## Main Command

activity                     Show recent team activity and updates.

**Usage:**
```bash
main [OPTIONS] COMMAND [ARGS]...
```

**Options:**

- `--version` - Show the version and exit.
- `--help` - Show this message and exit.

**Available Commands:**

- `activity` - Show recent team activity and updates.
- `analytics` - 🔬 EXPERIMENTAL: Advanced analytics and...
- `broadcast` - Broadcast a status update to the team.
- `capacity-forecast` - Forecast team capacity and bottlenecks.
- `comment` - Manage issue comments.
- `dashboard` - Show your personalized daily dashboard with...
- `export` - 📊 Export roadmap data to various formats...
- `git-branch` - Create a Git branch for an issue.
- `git-commits` - Show Git commits that reference an issue.
- `git-hooks-install` - Install Git hooks for automated roadmap...
- `git-hooks-uninstall` - Remove roadmap Git hooks.
- `git-link` - Link an issue to the current Git branch.
- `git-status` - Show Git repository status and roadmap...
- `git-sync` - Sync issue status from Git commit activity.
- `handoff` - Hand off an issue to another team member.
- `handoff-context` - Show handoff context and history for an issue.
- `handoff-list` - List all recent handoffs in the project.
- `init` - Initialize a new roadmap in the current...
- `issue` - Manage issues.
- `milestone` - Manage milestones.
- `notifications` - Show team notifications about issues...
- `predict` - 🔬 EXPERIMENTAL: Predictive intelligence and...
- `report` - Generate detailed reports and analytics.
- `smart-assign` - Intelligently assign an issue to the best...
- `status` - Show the current status of the roadmap.
- `sync` - Synchronize with GitHub repository.
- `team` - Team collaboration commands.
- `timeline` - Generate project timelines and Gantt charts.
- `workflow-automation-disable` - Disable all workflow automation.
- `workflow-automation-setup` - Setup comprehensive workflow automation.
- `workflow-sync-all` - Sync all issues with their Git activity.
- `workload-analysis` - Analyze team workload and capacity.

**Examples:**

```bash
roadmap --help
```

```bash
roadmap --version
```

```bash
roadmap status
```

---

## `activity`

-d, --days INTEGER   Show activity for last N days

**Usage:**
```bash
main activity [OPTIONS]
```

**Options:**

- `-d, --days INTEGER` - Show activity for last N days
- `-a, --assignee TEXT` - Filter by assignee
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap activity --help
```

---

## `analytics`

developer  🔬 EXPERIMENTAL: Analyze individual developer productivity and...

**Usage:**
```bash
main analytics [OPTIONS] COMMAND [ARGS]...
```

**Options:**

- `--help` - Show this message and exit.

**Available Commands:**

- `developer` - 🔬 EXPERIMENTAL: Analyze individual developer productivity and...
- `enhanced` - 🔬 EXPERIMENTAL: Enhanced analytics with pandas-powered insights.
- `quality` - 🔬 EXPERIMENTAL: Analyze code quality trends and metrics.
- `team` - 🔬 EXPERIMENTAL: Analyze team performance and collaboration...
- `velocity` - 🔬 EXPERIMENTAL: Analyze project velocity trends over time.

**Examples:**

```bash
roadmap analytics
```

```bash
roadmap analytics --export --format excel
```

```bash
roadmap analytics --period month --export
```

---

## `analytics developer`

-d, --days INTEGER  Analysis period in days (default: 30)

**Usage:**
```bash
main analytics developer [OPTIONS] DEVELOPER_NAME
```

**Options:**

- `-d, --days INTEGER` - Analysis period in days (default: 30)
- `-s, --save TEXT` - Save report to file with given name
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap analytics developer --help
```

---

## `analytics enhanced`

-p, --period [D|W|M|Q]     Analysis period for velocity trends (D=daily,

**Usage:**
```bash
main analytics enhanced [OPTIONS]
```

**Options:**

- `-p, --period [D|W|M|Q]` - Analysis period for velocity trends (D=daily, W=weekly, M=monthly, Q=quarterly)
- `-d, --days INTEGER` - Days of recent data to analyze (default: 30)
- `-e, --export TEXT` - Export detailed analysis to file
- `-f, --format [json|excel]` - Export format (used with --export)
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap analytics enhanced --help
```

---

## `analytics quality`

-d, --days INTEGER  Analysis period in days (default: 90)

**Usage:**
```bash
main analytics quality [OPTIONS]
```

**Options:**

- `-d, --days INTEGER` - Analysis period in days (default: 90)
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap analytics quality --help
```

---

## `analytics team`

-d, --days INTEGER             Analysis period in days (default: 30)

**Usage:**
```bash
main analytics team [OPTIONS]
```

**Options:**

- `-d, --days INTEGER` - Analysis period in days (default: 30)
- `-s, --save TEXT` - Save report to file with given name
- `-f, --format [table|detailed]` - Output format (default: table)
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap analytics team --help
```

---

## `analytics velocity`

-p, --period [week|month|quarter]

**Usage:**
```bash
main analytics velocity [OPTIONS]
```

**Options:**

- `-c, --count INTEGER` - Number of periods to analyze (default: 12)
- `--chart` - Show ASCII chart of velocity trends
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap analytics velocity --help
```

---

## `broadcast`

-a, --assignee TEXT  Send update to specific assignee (defaults to team)

**Usage:**
```bash
main broadcast [OPTIONS] MESSAGE
```

**Options:**

- `-a, --assignee TEXT` - Send update to specific assignee (defaults to team)
- `-i, --issue TEXT` - Associate update with specific issue ID
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap broadcast --help
```

---

## `capacity-forecast`

-d, --days INTEGER   Forecast period in days

**Usage:**
```bash
main capacity-forecast [OPTIONS]
```

**Options:**

- `-d, --days INTEGER` - Forecast period in days
- `-a, --assignee TEXT` - Forecast for specific assignee
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap capacity-forecast --help
```

---

## `comment`

create  Create a new comment on an issue.

**Usage:**
```bash
main comment [OPTIONS] COMMAND [ARGS]...
```

**Options:**

- `--help` - Show this message and exit.

**Available Commands:**

- `create` - Create a new comment on an issue.
- `delete` - Delete a comment permanently.
- `edit` - Edit an existing comment.
- `list` - List all comments for an issue.

**Examples:**

```bash
roadmap comment --help
```

---

## `comment create`

--help  Show this message and exit.

**Usage:**
```bash
main comment create [OPTIONS] ISSUE_IDENTIFIER COMMENT_TEXT
```

**Options:**

- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap comment create --help
```

---

## `comment delete`

--force  Skip confirmation prompt

**Usage:**
```bash
main comment delete [OPTIONS] COMMENT_ID
```

**Options:**

- `--force` - Skip confirmation prompt
- `--yes` - Confirm the action without prompting.
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap comment delete --help
```

---

## `comment edit`

--help  Show this message and exit.

**Usage:**
```bash
main comment edit [OPTIONS] COMMENT_ID NEW_TEXT
```

**Options:**

- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap comment edit --help
```

---

## `comment list`

--help  Show this message and exit.

**Usage:**
```bash
main comment list [OPTIONS] ISSUE_IDENTIFIER
```

**Options:**

- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap comment list --help
```

---

## `dashboard`

-a, --assignee TEXT  Show dashboard for specific assignee (defaults to you)

**Usage:**
```bash
main dashboard [OPTIONS]
```

**Options:**

- `-a, --assignee TEXT` - Show dashboard for specific assignee (defaults to you)
- `-d, --days INTEGER` - Number of days to look ahead (default: 7)
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap dashboard --help
```

---

## `export`

analytics   Export comprehensive analytics to Excel with multiple sheets.

**Usage:**
```bash
main export [OPTIONS] COMMAND [ARGS]...
```

**Options:**

- `--help` - Show this message and exit.

**Available Commands:**

- `analytics` - Export comprehensive analytics to Excel with multiple sheets.
- `issues` - Export issues to CSV, Excel, or JSON format.
- `milestones` - Export milestones to CSV, Excel, or JSON format.

**Examples:**

```bash
roadmap export --help
```

---

## `export analytics`

-f, --format [csv|excel|json]  Export format

**Usage:**
```bash
main export analytics [OPTIONS]
```

**Options:**

- `-f, --format [csv|excel|json]` - Export format
- `-o, --output TEXT` - Output file path (auto-generated if not provided)
- `-p, --period [D|W|M|Q]` - Analysis period (D=daily, W=weekly, M=monthly, Q=quarterly)
- `-d, --days INTEGER` - Number of days of history to analyze
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap export analytics --help
```

---

## `export issues`

-f, --format [csv|excel|json]   Export format

**Usage:**
```bash
main export issues [OPTIONS]
```

**Options:**

- `-f, --format [csv|excel|json]` - Export format
- `-o, --output TEXT` - Output file path (auto-generated if not provided)
- `-m, --milestone TEXT` - Filter by milestone Filter by status Filter by priority
- `-m, --milestone TEXT` - Filter by milestone Filter by status Filter by priority
- `-m, --milestone TEXT` - Filter by milestone Filter by status Filter by priority
- `-a, --assignee TEXT` - Filter by assignee
- `--labels TEXT` - Filter by labels (comma-separated)
- `--date-from TEXT` - Filter issues created from date (YYYY-MM-DD)
- `--date-to TEXT` - Filter issues created to date (YYYY-MM-DD)
- `--completed-from TEXT` - Filter issues completed from date (YYYY-MM-DD)
- `--completed-to TEXT` - Filter issues completed to date (YYYY-MM-DD)
- `--search TEXT` - Search text in title and content
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap export issues --format csv
```

```bash
roadmap export issues --format excel --milestone 'v1.0'
```

```bash
roadmap export issues --format json --status done --priority critical
```

---

## `export milestones`

-f, --format [csv|excel|json]  Export format

**Usage:**
```bash
main export milestones [OPTIONS]
```

**Options:**

- `-f, --format [csv|excel|json]` - Export format
- `-o, --output TEXT` - Output file path (auto-generated if not provided)
- `-s, --status [open|closed]` - Filter by status
- `--due-from TEXT` - Filter milestones due from date (YYYY-MM-DD)
- `--due-to TEXT` - Filter milestones due to date (YYYY-MM-DD)
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap export milestones --help
```

---

## `git-branch`

--checkout / --no-checkout  Checkout the branch after creation

**Usage:**
```bash
main git-branch [OPTIONS] ISSUE_ID
```

**Options:**

- `--checkout / --no-checkout` - Checkout the branch after creation
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap git-branch --help
```

---

## `git-commits`

--since TEXT  Show commits since date (e.g., '1 week ago')

**Usage:**
```bash
main git-commits [OPTIONS] ISSUE_ID
```

**Options:**

- `--since TEXT` - Show commits since date (e.g., '1 week ago')
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap git-commits --help
```

---

## `git-hooks-install`

-h, --hooks [post-commit|pre-push|post-merge|post-checkout]

**Usage:**
```bash
main git-hooks-install [OPTIONS]
```

**Options:**

- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap git-hooks-install --help
```

---

## `git-hooks-uninstall`

--help  Show this message and exit.

**Usage:**
```bash
main git-hooks-uninstall [OPTIONS]
```

**Options:**

- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap git-hooks-uninstall --help
```

---

## `git-link`

--help  Show this message and exit.

**Usage:**
```bash
main git-link [OPTIONS] ISSUE_ID
```

**Options:**

- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap git-link --help
```

---

## `git-status`

--help  Show this message and exit.

**Usage:**
```bash
main git-status [OPTIONS]
```

**Options:**

- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap git-status --help
```

---

## `git-sync`

--help  Show this message and exit.

**Usage:**
```bash
main git-sync [OPTIONS] ISSUE_ID
```

**Options:**

- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap git-sync --help
```

---

## `handoff`

-n, --notes TEXT     Handoff notes for the new assignee

**Usage:**
```bash
main handoff [OPTIONS] ISSUE_ID NEW_ASSIGNEE
```

**Options:**

- `-n, --notes TEXT` - Handoff notes for the new assignee
- `--preserve-progress` - Preserve current progress percentage
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap handoff --help
```

---

## `handoff-context`

--help  Show this message and exit.

**Usage:**
```bash
main handoff-context [OPTIONS] ISSUE_ID
```

**Options:**

- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap handoff-context --help
```

---

## `handoff-list`

-a, --assignee TEXT  Filter by assignee

**Usage:**
```bash
main handoff-list [OPTIONS]
```

**Options:**

- `-a, --assignee TEXT` - Filter by assignee
- `--show-completed` - Include completed handoffs
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap handoff-list --help
```

---

## `init`

-n, --name TEXT  Name of the roadmap directory (default: .roadmap)

**Usage:**
```bash
main init [OPTIONS]
```

**Options:**

- `-n, --name TEXT` - Name of the roadmap directory (default: .roadmap)
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap init
```

```bash
roadmap init --name my-project
```

```bash
roadmap init -n project-roadmap
```

---

## `issue`

block     Mark an issue as blocked.

**Usage:**
```bash
main issue [OPTIONS] COMMAND [ARGS]...
```

**Options:**

- `--help` - Show this message and exit.

**Available Commands:**

- `block` - Mark an issue as blocked.
- `close` - Close an issue by marking it as done.
- `complete` - Complete work on an issue by recording the actual end date.
- `create` - Create a new issue.
- `delete` - Delete an issue permanently.
- `deps` - Show dependency relationships for an issue or the entire project.
- `list` - List all issues with various filtering options.
- `move` - Move an issue to a milestone or to backlog.
- `progress` - Update the progress percentage for an issue (0-100).
- `start` - Start work on an issue by recording the actual start date.
- `unblock` - Unblock an issue by setting it to in-progress status.
- `update` - Update an existing issue.

**Examples:**

```bash
roadmap issue --help
```

---

## `issue block`

--reason TEXT  Reason why the issue is blocked

**Usage:**
```bash
main issue block [OPTIONS] ISSUE_ID
```

**Options:**

- `--reason TEXT` - Reason why the issue is blocked
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap issue block --help
```

---

## `issue close`

--reason TEXT  Reason for closing the issue

**Usage:**
```bash
main issue close [OPTIONS] ISSUE_ID
```

**Options:**

- `--reason TEXT` - Reason for closing the issue
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap issue close --help
```

---

## `issue complete`

--date TEXT  Completion date (YYYY-MM-DD HH:MM, defaults to now)

**Usage:**
```bash
main issue complete [OPTIONS] ISSUE_ID
```

**Options:**

- `--date TEXT` - Completion date (YYYY-MM-DD HH:MM, defaults to now)
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap issue complete --help
```

---

## `issue create`

-p, --priority [critical|high|medium|low]

**Usage:**
```bash
main issue create [OPTIONS] TITLE
```

**Options:**

- `-t, --type [feature|bug|other]` - Issue type
- `-m, --milestone TEXT` - Assign to milestone
- `-a, --assignee TEXT` - Assign to team member
- `-l, --labels TEXT` - Add labels
- `-e, --estimate FLOAT` - Estimated time to complete (in hours)
- `--depends-on TEXT` - Issue IDs this depends on
- `--blocks TEXT` - Issue IDs this blocks
- `--git-branch` - Create a Git branch for this issue
- `--checkout / --no-checkout` - Checkout the branch after creation (with
- `` - --git-branch)
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap issue create 'Fix authentication bug'
```

```bash
roadmap issue create 'Add user dashboard' --priority high --type feature
```

```bash
roadmap issue create 'Database optimization' -p critical -m 'v1.0' -a john
```

---

## `issue delete`

--yes   Confirm the action without prompting.

**Usage:**
```bash
main issue delete [OPTIONS] ISSUE_ID
```

**Options:**

- `--yes` - Confirm the action without prompting.
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap issue delete --help
```

---

## `issue deps`

--show-all  Show all dependency relationships in the project

**Usage:**
```bash
main issue deps [OPTIONS] [ISSUE_ID]
```

**Options:**

- `--show-all` - Show all dependency relationships in the project
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap issue deps --help
```

---

## `issue list`

-m, --milestone TEXT            Filter by milestone

**Usage:**
```bash
main issue list [OPTIONS]
```

**Options:**

- `-m, --milestone TEXT` - Filter by milestone
- `--backlog` - Show only backlog issues (no milestone)
- `--unassigned` - Show only unassigned issues (alias for
- `` - --backlog)
- `--open` - Show only open issues (not done)
- `--blocked` - Show only blocked issues
- `--next-milestone` - Show issues for the next upcoming milestone
- `-a, --assignee TEXT` - Filter by assignee
- `--my-issues` - Show only issues assigned to me Filter by status Filter by priority
- `--my-issues` - Show only issues assigned to me Filter by status Filter by priority
- `--my-issues` - Show only issues assigned to me Filter by status Filter by priority
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap issue list --help
```

---

## `issue move`

--help  Show this message and exit.

**Usage:**
```bash
main issue move [OPTIONS] ISSUE_ID [MILESTONE_NAME]
```

**Options:**

- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap issue move --help
```

---

## `issue progress`

--help  Show this message and exit.

**Usage:**
```bash
main issue progress [OPTIONS] ISSUE_ID PERCENTAGE
```

**Options:**

- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap issue progress --help
```

---

## `issue start`

--date TEXT  Start date (YYYY-MM-DD HH:MM, defaults to now)

**Usage:**
```bash
main issue start [OPTIONS] ISSUE_ID
```

**Options:**

- `--date TEXT` - Start date (YYYY-MM-DD HH:MM, defaults to now)
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap issue start --help
```

---

## `issue unblock`

--reason TEXT  Reason for unblocking

**Usage:**
```bash
main issue unblock [OPTIONS] ISSUE_ID
```

**Options:**

- `--reason TEXT` - Reason for unblocking
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap issue unblock --help
```

---

## `issue update`

-s, --status [todo|in-progress|blocked|review|done]

**Usage:**
```bash
main issue update [OPTIONS] ISSUE_ID
```

**Options:**

- `-m, --milestone TEXT` - Update milestone
- `-a, --assignee TEXT` - Update assignee
- `-e, --estimate FLOAT` - Update estimated time (in hours)
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap issue update --help
```

---

## `milestone`

assign  Assign an issue to a milestone.

**Usage:**
```bash
main milestone [OPTIONS] COMMAND [ARGS]...
```

**Options:**

- `--help` - Show this message and exit.

**Available Commands:**

- `assign` - Assign an issue to a milestone.
- `create` - Create a new milestone.
- `delete` - Delete a milestone permanently and unassign all issues from it.
- `list` - List all milestones.
- `update` - Update milestone properties.

**Examples:**

```bash
roadmap milestone --help
```

---

## `milestone assign`

--help  Show this message and exit.

**Usage:**
```bash
main milestone assign [OPTIONS] ISSUE_ID MILESTONE_NAME
```

**Options:**

- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap milestone assign --help
```

---

## `milestone create`

-d, --description TEXT  Milestone description

**Usage:**
```bash
main milestone create [OPTIONS] NAME
```

**Options:**

- `-d, --description TEXT` - Milestone description
- `--due-date TEXT` - Due date for milestone (YYYY-MM-DD format)
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap milestone create --help
```

---

## `milestone delete`

--yes   Confirm the action without prompting.

**Usage:**
```bash
main milestone delete [OPTIONS] MILESTONE_NAME
```

**Options:**

- `--yes` - Confirm the action without prompting.
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap milestone delete --help
```

---

## `milestone list`

--help  Show this message and exit.

**Usage:**
```bash
main milestone list [OPTIONS]
```

**Options:**

- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap milestone list --help
```

---

## `milestone update`

-d, --description TEXT  Update milestone description

**Usage:**
```bash
main milestone update [OPTIONS] MILESTONE_NAME
```

**Options:**

- `-d, --description TEXT` - Update milestone description
- `--due-date TEXT` - Update due date (YYYY-MM-DD format, or 'clear' to remove)
- `--status [open|closed]` - Update milestone status
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap milestone update --help
```

---

## `notifications`

-a, --assignee TEXT  Show notifications for specific assignee (defaults to

**Usage:**
```bash
main notifications [OPTIONS]
```

**Options:**

- `-a, --assignee TEXT` - Show notifications for specific assignee (defaults to you)
- `-s, --since TEXT` - Show notifications since date (YYYY-MM-DD, defaults to today)
- `--mark-read` - Mark all notifications as read
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap notifications --help
```

---

## `predict`

deadline      🔬 EXPERIMENTAL: Forecast project completion with scenario...

**Usage:**
```bash
main predict [OPTIONS] COMMAND [ARGS]...
```

**Options:**

- `--help` - Show this message and exit.

**Available Commands:**

- `deadline` - 🔬 EXPERIMENTAL: Forecast project completion with scenario...
- `estimate` - 🔬 EXPERIMENTAL: Estimate completion time for issues using...
- `intelligence` - 🔬 EXPERIMENTAL: Generate comprehensive predictive...
- `risks` - 🔬 EXPERIMENTAL: Assess potential project risks and...

**Examples:**

```bash
roadmap predict --help
```

---

## `predict deadline`

-t, --target TEXT     Target completion date (YYYY-MM-DD)

**Usage:**
```bash
main predict deadline [OPTIONS]
```

**Options:**

- `-t, --target TEXT` - Target completion date (YYYY-MM-DD)
- `-m, --milestone TEXT` - Focus on specific milestone issues
- `-s, --save TEXT` - Save forecast to file
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap predict deadline --help
```

---

## `predict estimate`

-d, --developer TEXT  Developer to assign (affects estimation)

**Usage:**
```bash
main predict estimate [OPTIONS] [ISSUE_IDS]...
```

**Options:**

- `-d, --developer TEXT` - Developer to assign (affects estimation)
- `--all` - Estimate all active issues
- `-s, --save TEXT` - Save estimates to file with given name
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap predict estimate --help
```

---

## `predict intelligence`

-t, --target TEXT  Target completion date (YYYY-MM-DD)

**Usage:**
```bash
main predict intelligence [OPTIONS]
```

**Options:**

- `-t, --target TEXT` - Target completion date (YYYY-MM-DD)
- `-s, --save TEXT` - Save intelligence report to file
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap predict intelligence --help
```

---

## `predict risks`

-d, --days INTEGER           Risk assessment period (default: 30)

**Usage:**
```bash
main predict risks [OPTIONS]
```

**Options:**

- `-d, --days INTEGER` - Risk assessment period (default: 30)
- `--level [all|high|critical]` - Filter by risk level
- `-s, --save TEXT` - Save risk assessment to file
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap predict risks --help
```

---

## `report`

assignee  Generate detailed report for a specific assignee or all assignees.

**Usage:**
```bash
main report [OPTIONS] COMMAND [ARGS]...
```

**Options:**

- `--help` - Show this message and exit.

**Available Commands:**

- `assignee` - Generate detailed report for a specific assignee or all assignees.
- `summary` - Generate a comprehensive summary report with analytics.

**Examples:**

```bash
roadmap report --help
```

---

## `report assignee`

-s, --status [todo|in-progress|blocked|review|done]

**Usage:**
```bash
main report assignee [OPTIONS] [ASSIGNEE]
```

**Options:**

- `-t, --type [feature|bug|other]` - Filter by issue type (can be used multiple times) Filter by priority (can be used multiple times)
- `-t, --type [feature|bug|other]` - Filter by issue type (can be used multiple times) Filter by priority (can be used multiple times)
- `-m, --milestone TEXT` - Filter by milestone Output format
- `-m, --milestone TEXT` - Filter by milestone Output format
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap report assignee --help
```

---

## `report summary`

-t, --type [feature|bug|other]  Filter by issue type (can be used multiple

**Usage:**
```bash
main report summary [OPTIONS]
```

**Options:**

- `-t, --type [feature|bug|other]` - Filter by issue type (can be used multiple times)
- `-m, --milestone TEXT` - Filter by milestone
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap report summary --help
```

---

## `smart-assign`

--consider-skills        Consider team member skills (experimental)

**Usage:**
```bash
main smart-assign [OPTIONS] ISSUE_ID
```

**Options:**

- `--consider-skills` - Consider team member skills (experimental)
- `--consider-availability` - Consider current workload
- `--suggest-only` - Only suggest, don't assign
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap smart-assign --help
```

---

## `status`

--help  Show this message and exit.

**Usage:**
```bash
main status [OPTIONS]
```

**Options:**

- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap status --help
```

---

## `sync`

bidirectional  Perform intelligent bidirectional synchronization between...

**Usage:**
```bash
main sync [OPTIONS] COMMAND [ARGS]...
```

**Options:**

- `--help` - Show this message and exit.

**Available Commands:**

- `bidirectional` - Perform intelligent bidirectional synchronization between...
- `delete-token` - Delete stored GitHub token from credential manager.
- `pull` - Pull changes from GitHub.
- `push` - Push local changes to GitHub.
- `setup` - Set up GitHub integration and repository labels.
- `status` - Show GitHub integration status and credential information.
- `test` - Test GitHub connection and authentication.

**Examples:**

```bash
roadmap sync --help
```

---

## `sync bidirectional`

--issues                        Sync issues only

**Usage:**
```bash
main sync bidirectional [OPTIONS]
```

**Options:**

- `--issues` - Sync issues only
- `--milestones` - Sync milestones only Conflict resolution strategy (default: newer_wins)
- `--milestones` - Sync milestones only Conflict resolution strategy (default: newer_wins)
- `--dry-run` - Show what would be synced without making changes
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap sync bidirectional --help
```

---

## `sync delete-token`

--help  Show this message and exit.

**Usage:**
```bash
main sync delete-token [OPTIONS]
```

**Options:**

- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap sync delete-token --help
```

---

## `sync pull`

--issues              Pull issues only

**Usage:**
```bash
main sync pull [OPTIONS]
```

**Options:**

- `--issues` - Pull issues only
- `--milestones` - Pull milestones only
- `--high-performance` - Use high-performance sync for large operations
- `--batch-size INTEGER` - Batch size for high-performance sync (default: 50)
- `--workers INTEGER` - Number of worker threads for high-performance sync (default: 8)
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap sync pull --help
```

---

## `sync push`

--issues      Push issues only

**Usage:**
```bash
main sync push [OPTIONS]
```

**Options:**

- `--issues` - Push issues only
- `--milestones` - Push milestones only
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap sync push --help
```

---

## `sync setup`

--token TEXT  GitHub token for authentication

**Usage:**
```bash
main sync setup [OPTIONS]
```

**Options:**

- `--token TEXT` - GitHub token for authentication
- `--repo TEXT` - GitHub repository (owner/repo)
- `--insecure` - Store token in config file (NOT RECOMMENDED - use environment variable instead)
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap sync setup --help
```

---

## `sync status`

--help  Show this message and exit.

**Usage:**
```bash
main sync status [OPTIONS]
```

**Options:**

- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap sync status --help
```

---

## `sync test`

--help  Show this message and exit.

**Usage:**
```bash
main sync test [OPTIONS]
```

**Options:**

- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap sync test --help
```

---

## `team`

assignments  Show issue assignments for all team members.

**Usage:**
```bash
main team [OPTIONS] COMMAND [ARGS]...
```

**Options:**

- `--help` - Show this message and exit.

**Available Commands:**

- `assignments` - Show issue assignments for all team members.
- `members` - List all team members from the GitHub repository.
- `workload` - Show workload summary for all team members.

**Examples:**

```bash
roadmap team --help
```

---

## `team assignments`

--help  Show this message and exit.

**Usage:**
```bash
main team assignments [OPTIONS]
```

**Options:**

- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap team assignments --help
```

---

## `team members`

--help  Show this message and exit.

**Usage:**
```bash
main team members [OPTIONS]
```

**Options:**

- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap team members --help
```

---

## `team workload`

--help  Show this message and exit.

**Usage:**
```bash
main team workload [OPTIONS]
```

**Options:**

- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap team workload --help
```

---

## `timeline`

critical-path  Show the critical path through the project dependencies.

**Usage:**
```bash
main timeline [OPTIONS] COMMAND [ARGS]...
```

**Options:**

- `--help` - Show this message and exit.

**Available Commands:**

- `critical-path` - Show the critical path through the project dependencies.
- `show` - Show project timeline with dependencies and estimated...

**Examples:**

```bash
roadmap timeline --help
```

---

## `timeline critical-path`

-m, --milestone TEXT  Filter by milestone

**Usage:**
```bash
main timeline critical-path [OPTIONS]
```

**Options:**

- `-m, --milestone TEXT` - Filter by milestone
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap timeline critical-path --help
```

---

## `timeline show`

-a, --assignee TEXT        Filter by assignee

**Usage:**
```bash
main timeline show [OPTIONS]
```

**Options:**

- `-a, --assignee TEXT` - Filter by assignee
- `-m, --milestone TEXT` - Filter by milestone
- `-f, --format [text|gantt]` - Output format
- `-d, --days INTEGER` - Number of days to show in timeline (default: 30)
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap timeline show --help
```

---

## `workflow-automation-disable`

--help  Show this message and exit.

**Usage:**
```bash
main workflow-automation-disable [OPTIONS]
```

**Options:**

- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap workflow-automation-disable --help
```

---

## `workflow-automation-setup`

-f, --features [git-hooks|status-automation|progress-tracking]

**Usage:**
```bash
main workflow-automation-setup [OPTIONS]
```

**Options:**

- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap workflow-automation-setup --help
```

---

## `workflow-sync-all`

--dry-run  Show what would be synced without making changes

**Usage:**
```bash
main workflow-sync-all [OPTIONS]
```

**Options:**

- `--dry-run` - Show what would be synced without making changes
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap workflow-sync-all --help
```

---

## `workload-analysis`

-a, --assignee TEXT  Analyze workload for specific assignee

**Usage:**
```bash
main workload-analysis [OPTIONS]
```

**Options:**

- `-a, --assignee TEXT` - Analyze workload for specific assignee
- `--include-estimates` - Include time estimates in analysis
- `--suggest-rebalance` - Suggest workload rebalancing
- `--help` - Show this message and exit.

**Examples:**

```bash
roadmap workload-analysis --help
```

---
