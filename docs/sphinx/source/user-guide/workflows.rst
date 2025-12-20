================================================================================
Common Workflows
================================================================================

Step-by-step guides for common project management tasks.

Planning a Release
==================

Releasing software requires coordination. Here's how to manage a release
with Roadmap CLI.

**Setup Phase (30 minutes)**

1. Create a release project:

   .. code-block:: bash

       roadmap project create "v2.0 Release" \
           --owner "Product Team" \
           --description "v2.0 production release"

2. Create milestones for each phase:

   .. code-block:: bash

       roadmap milestone create "v2.0 Alpha" \
           --project "v2.0 Release" \
           --date "2025-02-01"

       roadmap milestone create "v2.0 Beta" \
           --project "v2.0 Release" \
           --date "2025-03-01"

       roadmap milestone create "v2.0 GA" \
           --project "v2.0 Release" \
           --date "2025-04-01"

3. Define release tasks:

   .. code-block:: bash

       # Alpha phase tasks
       roadmap issue create "Feature A implementation" \
           --milestone "v2.0 Alpha" --priority high --estimate 5d
       roadmap issue create "Feature B implementation" \
           --milestone "v2.0 Alpha" --priority high --estimate 5d

       # Beta phase tasks
       roadmap issue create "QA and testing" \
           --milestone "v2.0 Beta" --priority high --estimate 3d
       roadmap issue create "Performance optimization" \
           --milestone "v2.0 Beta" --priority medium --estimate 2d

       # GA tasks
       roadmap issue create "Release notes" \
           --milestone "v2.0 GA" --priority high --estimate 1d
       roadmap issue create "Deploy to production" \
           --milestone "v2.0 GA" --priority high --estimate 1d

**Execution Phase (Ongoing)**

Track daily progress:

.. code-block:: bash

    # Daily standup
    roadmap today

    # Check overall progress
    roadmap status

    # View alpha phase details
    roadmap milestone view "v2.0 Alpha"

    # See what's blocking progress
    roadmap issue list --milestone "v2.0 Alpha" --status todo --priority high

Start working on tasks:

.. code-block:: bash

    # Pick a task and start it
    roadmap issue start <issue-id> --branch "feature/implement-auth"

    # Update progress
    roadmap issue update <issue-id> --status in_progress --progress 50

Complete milestones:

.. code-block:: bash

    # When alpha testing is complete
    roadmap milestone close "v2.0 Alpha"

**Monitoring & Reporting**

View milestone progress:

.. code-block:: bash

    roadmap milestone kanban "v2.0 Alpha"    # Kanban view
    roadmap milestone view "v2.0 Alpha"      # Detailed stats

Export for stakeholders:

.. code-block:: bash

    roadmap data export --format csv > v2.0-status.csv

Managing Sprints
================

Agile teams use sprints for time-boxed development.

**Sprint Setup (1 hour)**

1. Create a sprint project:

   .. code-block:: bash

       roadmap project create "2025 Sprints"

2. Create sprint milestones (2-week sprints):

   .. code-block:: bash

       # Sprint 1
       roadmap milestone create "Sprint 1 (Jan 6-17)" \
           --project "2025 Sprints" \
           --date "2025-01-17" \
           --description "First 2-week sprint"

       # Sprint 2
       roadmap milestone create "Sprint 2 (Jan 20-31)" \
           --project "2025 Sprints" \
           --date "2025-01-31"

3. Add backlog items to sprint:

   .. code-block:: bash

       roadmap issue create "API optimization" \
           --milestone "Sprint 1 (Jan 6-17)" \
           --priority high --estimate 2d

       roadmap issue create "UI improvements" \
           --milestone "Sprint 1 (Jan 6-17)" \
           --priority medium --estimate 3d

       roadmap issue create "Database migration" \
           --milestone "Sprint 1 (Jan 6-17)" \
           --priority high --estimate 4d

**Daily Standups**

Start each day with:

.. code-block:: bash

    roadmap today                    # Your tasks for today
    roadmap status                   # Overall team status

**Sprint Reviews**

At sprint end, review progress:

.. code-block:: bash

    # See what got done
    roadmap milestone view "Sprint 1 (Jan 6-17)"

    # Archive completed sprint
    roadmap milestone close "Sprint 1 (Jan 6-17)"

    # Start next sprint
    roadmap milestone kanban "Sprint 2 (Jan 20-31)"

Feature Development
===================

Managing individual feature development across team.

**Feature Lifecycle**

.. code-block:: bash

    # Create feature issue
    roadmap issue create "Dark mode support" \
        --milestone "v2.1" \
        --priority medium \
        --estimate 3d \
        --description "Add dark mode theme to UI"

    # Start feature (creates git branch)
    roadmap issue start <issue-id> --branch "feature/dark-mode"

    # Work on feature in git
    git checkout feature/dark-mode
    # ... make changes ...
    git push origin feature/dark-mode

    # Update progress in roadmap
    roadmap issue update <issue-id> --progress 50

    # Mark ready for review
    roadmap issue update <issue-id> --status in_progress

    # After code review and testing
    roadmap issue done <issue-id>

    # Feature goes to next release
    roadmap issue update <issue-id> --milestone "v2.1"

Bug Triage & Fixing
===================

Manage bug reports and fixes.

**Bug Entry**

.. code-block:: bash

    roadmap issue create "Login fails with special characters" \
        --priority high \
        --milestone "v2.0 Beta" \
        --description "Users with @#$ in password get authentication error"

**Priority Assessment**

Assign priorities based on impact:

.. code-block:: bash

    # Critical bug - immediate fix
    roadmap issue update <issue-id> --priority high --milestone "v2.0 Beta"

    # Medium bug - fix in next milestone
    roadmap issue update <issue-id> --priority medium --milestone "v2.1"

    # Low priority - backlog
    roadmap issue update <issue-id> --priority low --milestone "Backlog"

**Bug Fixing Workflow**

.. code-block:: bash

    # Pick up bug
    roadmap issue start <bug-id> --branch "fix/login-special-chars"

    # Implement fix
    git checkout fix/login-special-chars
    # ... make changes ...
    git commit -m "Fix login with special characters"

    # Mark as done
    roadmap issue done <bug-id>

Backlog Management
==================

Maintain and prioritize a backlog of future work.

**Create Backlog**

.. code-block:: bash

    roadmap milestone create "Backlog" \
        --project "Product" \
        --description "Future features and enhancements"

**Add to Backlog**

.. code-block:: bash

    roadmap issue create "Implement webhooks" \
        --milestone "Backlog" \
        --priority medium \
        --estimate 5d

**Prioritize & Move**

.. code-block:: bash

    # When ready to work on
    roadmap issue update <issue-id> --milestone "Sprint 3"

**Refine Backlog**

Monthly backlog refinement:

.. code-block:: bash

    # See all backlog items
    roadmap issue list --milestone "Backlog"

    # Re-prioritize
    roadmap issue update <id1> --priority high
    roadmap issue update <id2> --priority low

Team Coordination
=================

Assigning work to team members.

**Assign Issues**

.. code-block:: bash

    roadmap issue create "Database optimization" \
        --milestone "v2.1" \
        --assignee "alice" \
        --priority high \
        --estimate 3d

**View Team Assignments**

.. code-block:: bash

    # All of Alice's tasks
    roadmap issue list --assignee alice

    # High priority across team
    roadmap issue list --priority high

**Update Assignments**

.. code-block:: bash

    # Reassign
    roadmap issue update <issue-id> --assignee bob

    # Clear assignment
    roadmap issue update <issue-id> --assignee ""

Dependency Management
====================

Handle issue dependencies and blocking.

**Create Dependencies**

When creating issues:

.. code-block:: bash

    # Feature B depends on Feature A
    roadmap issue create "Feature B" \
        --milestone "v2.0" \
        --priority high

**Track Blocking Issues**

Update issue that's blocking:

.. code-block:: bash

    # Mark as blocking others
    roadmap issue update <issue-id> --blocks issue-2,issue-3

**Resolve Dependencies**

.. code-block:: bash

    # Complete Feature A first
    roadmap issue done <feature-a-id>

    # Now can start Feature B
    roadmap issue start <feature-b-id>

Performance Tracking
====================

Monitor team and project performance over time.

**Baseline**

Generate performance data:

.. code-block:: bash

    # Create performance baseline
    bash scripts/baseline_profiler.py

**Track Progress Metrics**

Over time, track:

.. code-block:: bash

    # Generate reports
    roadmap data export --format json > roadmap-snapshot-$(date +%Y-%m-%d).json

    # Analyze trends
    # Compare velocity across sprints
    # Monitor issue completion rates

**Health Reporting**

Regular health checks:

.. code-block:: bash

    roadmap health                   # System health
    roadmap status                   # Overall progress
    roadmap milestone view "Sprint X" # Sprint metrics

Tips for Success
================

1. **Keep titles clear** - Should understand issue in 10 words
2. **Use priorities** - Focus on high-impact work first
3. **Estimate realistically** - Include testing and review time
4. **Update status regularly** - Daily if possible
5. **Close completed milestones** - Keep active list manageable
6. **Archive old items** - Clean up annually
7. **Use descriptions** - Add context for future reference
8. **Assign clearly** - One person, one issue usually best
9. **Review weekly** - Sprint reviews catch issues early
10. **Communicate** - Sync with team on changes

See Also
========

- :doc:`commands` - Full command reference
- :doc:`projects` - Project management details
- :doc:`milestones` - Milestone guide
- :doc:`issues` - Issue management
- :doc:`../getting-started/quickstart` - 5-minute intro
