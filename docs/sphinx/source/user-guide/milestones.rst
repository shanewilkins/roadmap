================================================================================
Managing Milestones
================================================================================

Milestones are time-based deliverables that organize work into logical phases.

What is a Milestone?
====================

A milestone is a target date with associated work. Examples:

- **v1.0 Release** - Product release date
- **Sprint 1 (Jan 6-17)** - Two-week development sprint
- **Q1 Planning** - Quarter-end deliverable
- **Beta Launch** - Beta release date

Milestones represent points in time where you aim to complete specific work.

Creating Milestones
===================

Create a milestone:

.. code-block:: bash

    roadmap milestone create "v1.0 Release" \
        --project "Q1 2025 Planning" \
        --date "2025-03-31" \
        --description "First production release with core features"

Milestone Status Lifecycle
==========================

Milestones can be:

- **Open** - Active, not yet closed
- **Closed** - Completed
- **Overdue** - Past due date but still open

Closing Milestones
==================

When a milestone is complete:

.. code-block:: bash

    roadmap milestone close "v1.0 Release"

Milestone Progress Tracking
===========================

Monitor milestone progress:

.. code-block:: bash

    # View with progress percentage
    roadmap milestone view "v1.0 Release"

    # Kanban board view
    roadmap milestone kanban "v1.0 Release"

    # List all issues in milestone
    roadmap issue list --milestone "v1.0 Release"

Best Practices
==============

1. Use dates strategically
2. Keep reasonable scope
3. Add descriptions
4. Monitor progress weekly
5. Close when done
6. Archive completed regularly

Navigation
==========

- :doc:`projects` - Organize milestones in projects
- :doc:`issues` - Add work to milestones
- :doc:`workflows` - Real workflow examples
- :doc:`commands` - Full command reference
