================================================================================
Quickstart Guide (5 Minutes)
================================================================================

Get up and running with Roadmap CLI in just 5 minutes.

What is Roadmap CLI?
====================

Roadmap CLI is an enterprise-grade command-line tool for managing project
roadmaps with GitHub integration, data visualization, and advanced analytics.

Think of it as a structured way to plan projects using:

- **Projects** - High-level planning documents (e.g., "Q1 2025 Planning")
- **Milestones** - Time-based deliverables (e.g., "v1.0 Release")
- **Issues** - Individual work items (e.g., "Implement authentication")

Your First 5 Minutes
====================

**1. Initialize a new roadmap (1 minute)**

.. code-block:: bash

    roadmap init my-project

This creates a ``.roadmap/`` directory with your project structure.

**2. Create a project (1 minute)**

.. code-block:: bash

    roadmap project create "Q1 2025 Planning"

**3. Create a milestone (1 minute)**

.. code-block:: bash

    roadmap milestone create "v1.0 Release" \
        --project "Q1 2025 Planning" \
        --date "2025-03-31"

**4. Add an issue (1 minute)**

.. code-block:: bash

    roadmap issue create "Implement user authentication" \
        --milestone "v1.0 Release" \
        --priority high \
        --estimate 3d

**5. Check your progress (1 minute)**

.. code-block:: bash

    roadmap status

You should see something like:

.. code-block:: text

    📊 Roadmap Status

    🎯 Milestones:

      v1.0 Release
        1 issues assigned

    📋 Issues by Status:
       todo           1

That's it! You've created your first roadmap.

Next Steps
==========

**View Details**

.. code-block:: bash

    # See all projects
    roadmap project list

    # View milestone details
    roadmap milestone view "v1.0 Release"

    # View an issue
    roadmap issue list

**Update Status**

As you work, track progress:

.. code-block:: bash

    # Mark issue as started
    roadmap issue start <issue-id>

    # Mark issue as done
    roadmap issue done <issue-id>

**Check Daily Agenda**

See what you should focus on today:

.. code-block:: bash

    roadmap today

**Get Help**

Every command has built-in help:

.. code-block:: bash

    roadmap --help                          # Overall help
    roadmap project --help                  # Project commands
    roadmap issue create --help             # Specific command help

Common Workflows
================

**Planning a Sprint**

.. code-block:: bash

    # Create sprint milestone
    roadmap milestone create "Sprint 1" \
        --project "Q1 2025 Planning" \
        --date "2025-01-17"

    # Add features
    roadmap issue create "Feature: Dashboard" \
        --milestone "Sprint 1" \
        --estimate 5d

    # Track progress daily
    roadmap status

**Managing a Release**

.. code-block:: bash

    # Create release milestone
    roadmap milestone create "v2.0" \
        --project "Q1 2025 Planning" \
        --date "2025-03-31"

    # Add all planned work
    roadmap issue create "Alpha testing" --milestone "v2.0"
    roadmap issue create "Beta release" --milestone "v2.0"
    roadmap issue create "Documentation" --milestone "v2.0"

    # Monitor progress
    roadmap milestone view "v2.0"

**GitHub Integration** (Optional)

Connect to GitHub for syncing:

.. code-block:: bash

    # Initialize with GitHub
    roadmap init my-project --github-token <your-token>

    # Sync with GitHub
    roadmap git sync

See :doc:`../user-guide/workflows` for detailed workflow guides.

Configuration
==============

Most users can start with defaults, but you can customize via:

.. code-block:: bash

    # See current configuration
    cat .roadmap/config.yaml

See :doc:`configuration` for all options.

Troubleshooting
===============

**"roadmap: command not found"**

Make sure you installed it:

.. code-block:: bash

    pip install roadmap-cli

**"Permission denied"**

Try with Python module:

.. code-block:: bash

    python -m roadmap --version

**Issues not showing**

Check the project name matches exactly:

.. code-block:: bash

    roadmap project list          # See exact names
    roadmap issue list --project "Your Project Name"

**Need more help?**

See the full documentation:

- :doc:`../user-guide/commands` - Complete command reference
- :doc:`../user-guide/workflows` - Detailed workflow guides
- :doc:`../troubleshooting` - Common issues and solutions

You're Ready!
=============

You now understand the basics. Explore more:

- Create multiple projects
- Add many issues to track
- Use GitHub integration for team collaboration
- Automate with scripts

Happy planning! 🎉
