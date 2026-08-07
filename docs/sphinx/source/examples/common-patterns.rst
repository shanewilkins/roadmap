================================================================================
Common Patterns
================================================================================

Examples of common use patterns for Roadmap CLI.

.. note::

   This is a stub. Complete implementation coming in v.0.7.0.

Creating a Release Plan
=======================

Example of planning a release:

.. code-block:: bash

    # Create a project for the release
    roadmap project create "v1.0 Release"

    # Add milestones for phases
    roadmap milestone create --project "v1.0 Release" \
        "v1.0-alpha" --date "2025-01-15"
    roadmap milestone create --project "v1.0 Release" \
        "v1.0-beta" --date "2025-02-01"

    # Add features and fixes
    roadmap issue create "Feature: Authentication" \
        --milestone "v1.0-alpha"

Sprint Planning
===============

Using Roadmap CLI for sprint management.

[Example coming in v.0.7.0]

GitHub Synchronization
======================

Syncing with GitHub issues.

[Example coming in v.0.7.0]

Generating Reports
==================

Creating status reports and metrics.

[Example coming in v.0.7.0]

See Also
========

- :doc:`../user-guide/workflows` - Workflow documentation
- :doc:`../user-guide/commands` - Command reference
- :doc:`demo-project` - Full demo project
