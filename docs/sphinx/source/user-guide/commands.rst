================================================================================
Command Reference
================================================================================

Complete reference for all Roadmap CLI commands.

Getting Command Help
====================

Every command has built-in help:

.. code-block:: bash

    roadmap --help                    # Show all commands
    roadmap project --help            # Show project subcommands
    roadmap issue create --help       # Show specific command options

Core Commands
=============

Initialization
--------------

.. code-block:: bash

    roadmap init [PROJECT-NAME]

Initialize a new roadmap in the current directory. Creates the ``.roadmap/``
directory structure with configuration and data storage.

Options:

- ``--github-token TEXT`` - GitHub API token for integration
- ``--data-format`` - Format for data storage (json/yaml)

Status & Health
---------------

.. code-block:: bash

    roadmap status                    # Overall roadmap status
    roadmap health                    # System health check
    roadmap today                     # Your daily agenda

Project Management
==================

List Projects
-------------

.. code-block:: bash

    roadmap project list

Show all projects with summary statistics.

Options:

- ``--sort`` - Sort by (name, created, updated)
- ``--filter TEXT`` - Filter by name (case-insensitive)

Create Project
--------------

.. code-block:: bash

    roadmap project create "Project Name"

Create a new top-level project.

Options:

- ``--description TEXT`` - Project description
- ``--owner TEXT`` - Project owner/team

Example:

.. code-block:: bash

    roadmap project create "Q1 2025 Planning" \
        --owner "Product Team" \
        --description "Q1 quarterly planning and execution"

View Project
------------

.. code-block:: bash

    roadmap project view "Project Name"

Display detailed project information including milestones and issues.

Update Project
--------------

.. code-block:: bash

    roadmap project update "Project Name" \
        --description "New description"

Archive/Restore Project
------------------------

.. code-block:: bash

    roadmap project archive "Project Name"     # Archive
    roadmap project restore "Project Name"     # Restore from archive

Milestone Management
====================

List Milestones
---------------

.. code-block:: bash

    roadmap milestone list

Show all milestones across all projects.

Options:

- ``--project TEXT`` - Filter by project name
- ``--status`` - Filter by status (open/closed)
- ``--sort`` - Sort by (name, date, progress)

Create Milestone
----------------

.. code-block:: bash

    roadmap milestone create "v1.0 Release" \
        --project "Q1 2025 Planning" \
        --date "2025-03-31"

Create a time-based deliverable milestone.

Options:

- ``--project TEXT`` - Project this belongs to (required)
- ``--date`` - Due date (YYYY-MM-DD)
- ``--description TEXT`` - Detailed description
- ``--owner TEXT`` - Responsible owner/team

View Milestone
--------------

.. code-block:: bash

    roadmap milestone view "v1.0 Release"

Show milestone details including:

- Progress percentage
- Issue breakdown by status
- Timeline and deadlines
- Dependencies

Update Milestone
----------------

.. code-block:: bash

    roadmap milestone update "v1.0 Release" \
        --date "2025-04-15" \
        --description "Updated timeline"

Close Milestone
---------------

.. code-block:: bash

    roadmap milestone close "v1.0 Release"

Mark milestone as complete. Issues can still be archived or moved.

Kanban View
-----------

.. code-block:: bash

    roadmap milestone kanban "v1.0 Release"

Display all issues in a milestone in kanban board format:

.. code-block:: text

    Todo          In Progress        Done
    ├─ Feature A  ├─ Bug fix X       ├─ Feature Z
    └─ Feature B  └─ Feature Y       └─ Doc update

Issue Management
================

List Issues
-----------

.. code-block:: bash

    roadmap issue list                             # All issues
    roadmap issue list --milestone "v1.0 Release"  # For a milestone
    roadmap issue list --status in_progress        # By status

Options:

- ``--milestone TEXT`` - Filter by milestone
- ``--status`` - Filter (todo/in_progress/done/closed)
- ``--priority`` - Filter (low/medium/high)
- ``--assignee TEXT`` - Filter by assignee
- ``--sort`` - Sort by (created, updated, priority, due)
- ``--overdue`` - Show only overdue issues

Create Issue
------------

.. code-block:: bash

    roadmap issue create "Implement user authentication" \
        --milestone "v1.0 Release" \
        --priority high \
        --estimate 3d \
        --description "Add JWT-based authentication"

Create a new work item/issue.

Options:

- ``--milestone TEXT`` - Assign to milestone
- ``--priority`` - low/medium/high
- ``--estimate`` - Time estimate (e.g., 3d, 4h, 2w)
- ``--description TEXT`` - Issue description
- ``--assignee TEXT`` - Assign to person/team
- ``--due-date`` - Due date (YYYY-MM-DD)

View Issue
----------

.. code-block:: bash

    roadmap issue view <issue-id>

Show complete issue details including history and comments.

Start Issue
-----------

.. code-block:: bash

    roadmap issue start <issue-id>

Mark issue as in progress. Optionally create a git branch:

.. code-block:: bash

    roadmap issue start <issue-id> --branch "feature/auth"

Update Issue
------------

.. code-block:: bash

    roadmap issue update <issue-id> \
        --status in_progress \
        --progress 50

Update issue fields:

- ``--title TEXT`` - New title
- ``--description TEXT`` - New description
- ``--status`` - New status
- ``--priority`` - New priority
- ``--estimate`` - New time estimate
- ``--progress`` - Progress percentage (0-100)
- ``--assignee TEXT`` - New assignee

Mark Issue Complete
--------------------

.. code-block:: bash

    roadmap issue done <issue-id>

Mark issue as completed.

Archive Issue
-------------

.. code-block:: bash

    roadmap issue archive <issue-id>

Archive completed or cancelled issues.

Comments
========

Add Comment
-----------

.. code-block:: bash

    roadmap comment add <issue-id> "Comment text here"

Add comment to an issue or milestone.

View Comments
-------------

.. code-block:: bash

    roadmap comment list <issue-id>

Show all comments on an issue.

GitHub Integration
==================

Sync with GitHub
----------------

.. code-block:: bash

    roadmap git sync

Synchronize roadmap with GitHub issues. Requires GitHub token in config.

Git Workflow
-----------

.. code-block:: bash

    roadmap git log                   # Show sync history
    roadmap git status                # Check sync status

Data & Reporting
================

Export Data
-----------

.. code-block:: bash

    roadmap data export --format json > roadmap.json
    roadmap data export --format csv > roadmap.csv

Export roadmap to various formats:

- ``json`` - Complete structured data
- ``csv`` - Tabular format
- ``markdown`` - Markdown report

Health Check
============

.. code-block:: bash

    roadmap health

Run diagnostics:

- File system integrity
- Configuration validation
- Git integration status
- Data consistency

Cleanup
=======

.. code-block:: bash

    roadmap cleanup

Comprehensive maintenance:

- Remove orphaned files
- Rebuild indexes
- Repair corrupted data
- Archive old items

Tips & Tricks
=============

**Batch Operations**

Create multiple issues quickly:

.. code-block:: bash

    for i in {1..5}; do
      roadmap issue create "Task $i" --milestone "Sprint 1"
    done

**Filter & List**

Combine filters:

.. code-block:: bash

    roadmap issue list --milestone "v1.0" --status todo --priority high

**Bulk Updates**

Update multiple issues (with xargs):

.. code-block:: bash

    roadmap issue list --status todo | xargs -I {} \
      roadmap issue update {} --status in_progress

**Shell Aliases**

Create shortcuts:

.. code-block:: bash

    alias roadmap-todo='roadmap issue list --status todo'
    alias roadmap-today='roadmap today'

See Also
========

- :doc:`projects` - Project management guide
- :doc:`milestones` - Milestone workflows
- :doc:`issues` - Issue management guide
- :doc:`workflows` - Step-by-step workflow tutorials
