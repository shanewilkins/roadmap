================================================================================
Managing Projects
================================================================================

Projects are top-level planning documents for organizing your roadmap work.

What is a Project?
==================

A project is a container for related milestones and issues. Think of it as
a high-level planning document for a specific effort:

- **Q1 2025 Planning** - Quarterly planning document
- **v2.0 Release** - Major version release planning
- **2025 Sprints** - Sprint management container
- **Mobile App** - Product or platform initiative

Projects help organize work by:

- Team or department
- Product or service
- Time period (quarter, year)
- Release cycle

Creating a Project
==================

Create a new project:

.. code-block:: bash

    roadmap project create "Q1 2025 Planning" \
        --description "Q1 quarterly planning and execution" \
        --owner "Product Team"

The project is now ready to add milestones and issues.

Project Hierarchy
=================

Roadmap uses a three-level hierarchy:

.. code-block:: text

    Project (High-level planning)
    └── Milestone (Time-based deliverable)
        └── Issue (Individual work item)

Example:

.. code-block:: text

    Q1 2025 Planning
    ├── v2.0 Release (due 2025-03-31)
    │   ├── Feature A
    │   ├── Feature B
    │   └── Testing
    └── v2.1 Planning (due 2025-04-15)
        ├── Enhancement X
        └── Bug fixes

Listing Projects
================

View all projects:

.. code-block:: bash

    roadmap project list

Viewing Project Details
=======================

View a specific project:

.. code-block:: bash

    roadmap project view "Q1 2025 Planning"

Updating a Project
==================

Update project information:

.. code-block:: bash

    roadmap project update "Q1 2025 Planning" \
        --description "Updated Q1 plan with new features"

Archiving Projects
===================

Archive completed projects:

.. code-block:: bash

    roadmap project archive "Q4 2024 Planning"

Best Practices
==============

- Use clear, descriptive names
- Assign clear ownership
- Archive completed projects regularly
- Keep one project per quarter or initiative

Navigation
==========

- :doc:`milestones` - Manage milestones within projects
- :doc:`issues` - Manage work items
- :doc:`commands` - Full command reference
- :doc:`workflows` - Real-world workflow examples
