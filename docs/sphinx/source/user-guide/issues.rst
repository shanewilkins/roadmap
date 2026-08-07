================================================================================
Managing Issues
================================================================================

Issues represent discrete units of work, bugs, or feature requests.

What is an Issue?
=================

An issue is a unit of work with:

- **Title** - What needs to be done
- **Description** - Context and details
- **Status** - Current state (open, in-progress, done, blocked)
- **Priority** - How urgent (low, medium, high, critical)
- **Assignee** - Who's working on it
- **Labels** - Categorization (bug, feature, documentation, etc.)

Types of Issues
===============

**Bugs** - Something broken or not working correctly

.. code-block:: bash

    roadmap issue create "Fix login timeout on slow networks" \
        --project "Production" \
        --milestone "v1.0" \
        --label "bug,urgent"

**Features** - New functionality

.. code-block:: bash

    roadmap issue create "Add dark mode toggle" \
        --project "UI Improvements" \
        --milestone "v1.1" \
        --label "feature"

**Documentation** - Docs that need writing

.. code-block:: bash

    roadmap issue create "Document API endpoints" \
        --project "Documentation" \
        --label "documentation"

**Tech Debt** - Code improvements

.. code-block:: bash

    roadmap issue create "Refactor authentication module" \
        --project "Infrastructure" \
        --label "tech-debt"

Creating Issues
===============

Basic creation:

.. code-block:: bash

    roadmap issue create "Add user export to CSV"

With full details:

.. code-block:: bash

    roadmap issue create "Add user export to CSV" \
        --project "Features" \
        --milestone "Q2" \
        --assignee "@john" \
        --priority "high" \
        --label "feature,export"

Issue Lifecycle
===============

1. **Create** - Issue created, status = Open
2. **Assign** - Assign to team member
3. **Start** - Begin work, status = In-Progress
4. **Develop** - Do the work
5. **Test** - Verify it works
6. **Done** - Mark complete, status = Done

Starting Work on an Issue
==========================

When you begin work:

.. code-block:: bash

    roadmap issue start "Add user export to CSV"

This updates the issue status and timestamp.

Blocking and Dependencies
==========================

Block issues on other issues:

.. code-block:: bash

    roadmap issue block "Feature X" --on "Fix in authentication module"

Unblock when dependencies are done:

.. code-block:: bash

    roadmap issue unblock "Feature X"

Marking Issues Done
===================

When work is complete:

.. code-block:: bash

    roadmap issue done "Add user export to CSV"

This closes the issue and updates progress.

Issue Status Tracking
====================

List issues by status:

.. code-block:: bash

    # All open issues
    roadmap issue list --status open

    # Issues in progress
    roadmap issue list --status in-progress

    # Completed issues this month
    roadmap issue list --status done --created "2025-01-01:2025-01-31"

Filter by project or milestone:

.. code-block:: bash

    # Issues in a specific project
    roadmap issue list --project "Q1 2025"

    # Issues in a specific milestone
    roadmap issue list --milestone "v1.0"

    # High priority bugs
    roadmap issue list --priority "high" --label "bug"

Issue Dependencies and Blocking
===============================

Track what blocks what:

.. code-block:: bash

    # Show blocking relationships
    roadmap issue view "Feature X"

    # Block an issue
    roadmap issue block "Feature B" --on "Feature A"

    # Unblock when ready
    roadmap issue unblock "Feature B"

Assigning Work
==============

Assign to team members:

.. code-block:: bash

    roadmap issue assign "Add CSV export" --to "@jane"

Update assignment:

.. code-block:: bash

    roadmap issue update "Add CSV export" --assignee "@sarah"

Working with Labels
===================

Organize with labels:

.. code-block:: bash

    # Create issue with multiple labels
    roadmap issue create "Performance investigation" \
        --label "performance,investigation,backend"

    # Find by label
    roadmap issue list --label "performance"

    # Find by multiple labels
    roadmap issue list --label "bug,regression"

Best Practices
==============

1. **Be specific** - Clear titles and descriptions
2. **Use labels** - Categorize consistently
3. **Assign promptly** - Who's responsible?
4. **Update status** - Keep status current
5. **Close when done** - Mark complete promptly
6. **Link related work** - Use blocking for dependencies
7. **Review regularly** - Monitor progress

Example Workflow
================

Creating and tracking a feature:

.. code-block:: bash

    # Create the feature issue
    roadmap issue create "Implement OAuth login" \
        --project "Authentication" \
        --milestone "v1.0" \
        --priority "high" \
        --label "feature,security"

    # Assign to developer
    roadmap issue assign "Implement OAuth login" --to "@alice"

    # Developer starts work
    roadmap issue start "Implement OAuth login"

    # Track progress with Kanban view
    roadmap project kanban "Authentication"

    # Developer completes and marks done
    roadmap issue done "Implement OAuth login"

    # Verify closure
    roadmap issue view "Implement OAuth login"

GitHub Integration
==================

Issues can be synced with GitHub issues.

See :doc:`../user-guide/github` for details.

Navigation
==========

- :doc:`projects` - Learn about projects
- :doc:`milestones` - Learn about milestones
- :doc:`commands` - Full command reference
