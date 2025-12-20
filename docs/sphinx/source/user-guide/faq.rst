================================================================================
Frequently Asked Questions (FAQ)
================================================================================

Common questions and answers about Roadmap CLI.

Installation & Setup
====================

**Q: How do I install Roadmap CLI?**

A: See :doc:`../getting-started/installation` for detailed OS-specific instructions.

.. code-block:: bash

    pip install roadmap-cli

**Q: Do I need Python installed?**

A: Yes, Python 3.10 or higher. Check with:

.. code-block:: bash

    python3 --version

**Q: Can I use Docker instead?**

A: Yes! See :doc:`../getting-started/installation` for Docker instructions.

**Q: How do I update to the latest version?**

A: Update with:

.. code-block:: bash

    pip install --upgrade roadmap-cli

**Q: Where does Roadmap store my data?**

A: By default, in `~/.roadmap/` directory. You can configure this in your config file.

Getting Started
===============

**Q: How do I create my first project?**

A: Quick start guide is here: :doc:`../getting-started/quickstart`

.. code-block:: bash

    roadmap project create "My First Project"

**Q: What's the difference between Projects, Milestones, and Issues?**

A:

- **Project** - High-level container (e.g., "Q1 2025 Planning")
- **Milestone** - Time-based deliverable (e.g., "v1.0 Release" on March 31)
- **Issue** - Discrete unit of work (e.g., "Add user authentication")

**Q: Can I organize projects into folders?**

A: You can use naming conventions like:

.. code-block:: bash

    roadmap project create "Frontend - Login Page"
    roadmap project create "Frontend - Dashboard"
    roadmap project create "Backend - API v2"

Then use ``roadmap project list`` to see the hierarchy.

**Q: How many items can I have?**

A: No practical limits. Roadmap is designed to handle thousands of projects, milestones, and issues.

Usage & Commands
================

**Q: How do I list all my projects?**

A: Use:

.. code-block:: bash

    roadmap project list

Add filters:

.. code-block:: bash

    roadmap project list --archived  # Show archived only
    roadmap project list --open      # Show open only

**Q: How do I see what I'm working on right now?**

A: View items in progress:

.. code-block:: bash

    roadmap issue list --status in-progress

**Q: Can I assign issues to team members?**

A: Yes! Use:

.. code-block:: bash

    roadmap issue assign "Issue Title" --to "@username"

**Q: How do I track progress?**

A: Use Kanban boards:

.. code-block:: bash

    roadmap project kanban "Project Name"
    roadmap milestone kanban "Milestone Name"

**Q: Can I export my data?**

A: Yes, export to JSON:

.. code-block:: bash

    roadmap project export "Project Name" --format json

**Q: How do I find issues by priority?**

A: Filter by priority:

.. code-block:: bash

    roadmap issue list --priority high
    roadmap issue list --priority critical

**Q: Can I see all blocked issues?**

A: Use the progress command:

.. code-block:: bash

    roadmap issue progress "Project Name"

This shows blocking relationships.

Configuration
==============

**Q: Where is my configuration file?**

A: Located at `~/.roadmap/config.yaml` or `$ROADMAP_CONFIG_PATH` if set.

**Q: How do I enable GitHub sync?**

A: See :doc:`../getting-started/configuration` for GitHub setup instructions.

In brief:

.. code-block:: yaml

    github:
        enabled: true
        token: YOUR_GITHUB_TOKEN
        org: YOUR_ORG

**Q: Can I use environment variables for configuration?**

A: Yes! See :doc:`../getting-started/configuration` for available environment variables.

**Q: How do I change my data directory?**

A: Set the `data_dir` in config.yaml or use environment variable:

.. code-block:: bash

    export ROADMAP_DATA_DIR=/path/to/my/data
    roadmap project list

**Q: Can I work with multiple configurations?**

A: Yes, set different config paths:

.. code-block:: bash

    export ROADMAP_CONFIG_PATH=/path/to/config1.yaml
    roadmap project list

    export ROADMAP_CONFIG_PATH=/path/to/config2.yaml
    roadmap project list

GitHub Integration
==================

**Q: How do I sync with GitHub?**

A: Use:

.. code-block:: bash

    roadmap sync

When enabled, Roadmap can:

- Push milestones to GitHub
- Sync issues with GitHub issues
- Link to GitHub PRs

See :doc:`../getting-started/configuration` for setup.

**Q: Do I need a GitHub token?**

A: Yes, for GitHub integration. See :doc:`../getting-started/configuration` for how to create one.

**Q: Will Roadmap overwrite my GitHub issues?**

A: No. Sync is bi-directional and non-destructive. Conflicts are handled carefully.

**Q: Can I use Roadmap with GitHub Enterprise?**

A: Yes, configure the GitHub URL in your config.yaml.

Troubleshooting
===============

**Q: I'm getting "Permission denied" errors**

A: Ensure you have permissions for your data directory:

.. code-block:: bash

    chmod 700 ~/.roadmap
    chmod 600 ~/.roadmap/config.yaml

**Q: Commands aren't found**

A: Check installation:

.. code-block:: bash

    pip list | grep roadmap-cli
    which roadmap

Reinstall if needed:

.. code-block:: bash

    pip uninstall roadmap-cli
    pip install roadmap-cli

**Q: My changes aren't showing up**

A: Try refreshing GitHub sync:

.. code-block:: bash

    roadmap sync

**Q: How do I clear my data?**

A: To reset everything:

.. code-block:: bash

    rm -rf ~/.roadmap/data/

To completely remove Roadmap:

.. code-block:: bash

    pip uninstall roadmap-cli
    rm -rf ~/.roadmap/

Advanced Topics
===============

**Q: Can I script Roadmap commands?**

A: Yes! Roadmap works great in shell scripts:

.. code-block:: bash

    #!/bin/bash
    roadmap project create "Q2 Planning"
    roadmap milestone create "v1.1" --project "Q2 Planning" --date "2025-06-30"
    roadmap issue create "Feature X" --milestone "v1.1" --priority high

**Q: Can I use Roadmap in CI/CD pipelines?**

A: Yes! You can:

- Track release versions
- Update issue status on deployment
- Sync with GitHub automatically

Set `ROADMAP_CONFIG_PATH` in your CI environment.

**Q: How do I back up my data?**

A: Back up your data directory:

.. code-block:: bash

    tar -czf roadmap-backup.tar.gz ~/.roadmap/

**Q: Can I use Roadmap offline?**

A: Yes! All data is stored locally. GitHub sync requires internet, but core functionality works offline.

**Q: Is there a web UI?**

A: Not yet. Roadmap is CLI-based. See the demo project for examples.

More Help
=========

- :doc:`../getting-started/index` - Getting started
- :doc:`../user-guide/index` - User guide
- :doc:`commands` - Command reference
- :doc:`workflows` - Real workflow examples

See Also
========

- :doc:`troubleshooting` - Troubleshooting guide
- :doc:`../architecture/overview` - Architecture overview
