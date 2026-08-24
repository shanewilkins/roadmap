================================================================================
Configuration
================================================================================

Customize Roadmap CLI for your workflow.

Configuration File
==================

Roadmap CLI stores configuration in ``.roadmap/config.yaml``:

.. code-block:: bash

    cat .roadmap/config.yaml

Default Configuration
---------------------

The default configuration includes:

.. code-block:: yaml

    user:
      name: alice
      email: alice@example.test
    paths:
      roadmap_dir: .roadmap
      logs_dir: .roadmap/logs
      db_dir: .roadmap/db
    display:
      table_width: 100
    behavior:
      confirm_destructive: true

Configuration Options
=====================

Data Format
-----------

Controls how roadmap data is stored:

.. code-block:: yaml

    data_format: json    # Options: json, yaml

- ``json`` - Recommended, faster parsing
- ``yaml`` - Human-readable, easier to edit manually

Project Root
------------

Directory where roadmap data is stored:

.. code-block:: yaml

    project_root: .    # Relative or absolute path

All roadmap data lives in ``.roadmap/`` subdirectory of this root.

Provider and Git transport settings
-----------------------------------

Provider credentials, remotes, transport, and synchronization policy are not
Roadmap configuration. Configure remote collaboration through Git and its
native credential helpers. Roadmap core workflows require no network account.

Logging
-------

Control how Roadmap logs information:

.. code-block:: yaml

    logging:
      level: INFO        # Options: DEBUG, INFO, WARNING, ERROR
      format: structured # Options: structured, plain

- ``DEBUG`` - Verbose output, useful for troubleshooting
- ``INFO`` - Normal operation (recommended)
- ``WARNING`` - Only show warnings and errors
- ``ERROR`` - Only show errors

Performance Caching
-------------------

Enable caching for faster operations:

.. code-block:: yaml

    cache:
      enabled: true
      ttl_seconds: 3600

- Cache is automatically cleared on writes
- Reduces file I/O for large projects
- Disable if experiencing issues

Environment Variables
======================

Override configuration using environment variables:

.. code-block:: bash

    export ROADMAP_DATA_FORMAT=json
    export ROADMAP_PROJECT_ROOT=/path/to/project
    export ROADMAP_LOG_LEVEL=DEBUG

Environment variables take precedence over config file.

All Supported Variables
-----------------------

- ``ROADMAP_DATA_FORMAT`` - Data format (json/yaml)
- ``ROADMAP_PROJECT_ROOT`` - Project root directory
- ``ROADMAP_LOG_LEVEL`` - Logging level
- ``ROADMAP_CACHE_ENABLED`` - Enable/disable caching
- ``ROADMAP_CACHE_TTL`` - Cache TTL in seconds

Example Usage
=============

**Using a Different Project Root**

.. code-block:: bash

    export ROADMAP_PROJECT_ROOT=/path/to/my/project
    roadmap status

**Enable Debug Logging**

.. code-block:: bash

    export ROADMAP_LOG_LEVEL=DEBUG
    roadmap issue list

**Disable Caching**

.. code-block:: bash

    export ROADMAP_CACHE_ENABLED=false
    roadmap status

Team Configuration
==================

For team use, you can commit the config file to git:

.. code-block:: bash

    # Include in version control (no secrets)
    git add .roadmap/config.yaml

For personal settings, create a local override:

.. code-block:: yaml

    # .roadmap/config.local.yaml (gitignored)
    github:
      token: your-personal-token

Load it with an environment variable:

.. code-block:: bash

    # Roadmap will merge config.local.yaml with config.yaml
    ROADMAP_CONFIG_LOCAL=true roadmap status

Advanced Configuration
======================

Custom Data Directory
---------------------

Store roadmap data outside the project:

.. code-block:: yaml

    project_root: /var/roadmap-data

Useful for:

- Centralizing multiple projects
- Network shares
- Backup automation

Multi-Project Setup
-------------------

Manage multiple projects with different configs:

.. code-block:: bash

    # Project 1
    export ROADMAP_PROJECT_ROOT=~/projects/frontend
    roadmap status

    # Project 2
    export ROADMAP_PROJECT_ROOT=~/projects/backend
    roadmap status

Custom Logging
--------------

For production deployments:

.. code-block:: yaml

    logging:
      level: WARNING
      format: json
      file: /var/log/roadmap.log

Troubleshooting Configuration
==============================

**Config not being read**

.. code-block:: bash

    # Check where config file is
    ls -la .roadmap/config.yaml

    # Verify format
    python -c "import yaml; yaml.safe_load(open('.roadmap/config.yaml'))"

**Environment variables not working**

.. code-block:: bash

    # Check variable is set
    echo $ROADMAP_PROJECT_ROOT

    # Environment variables must be exported
    export ROADMAP_PROJECT_ROOT=/path/to/project

**Old provider settings**

The experimental 0.1.1 provider keys are ignored by the 0.2 product contract.
Remove Roadmap-specific tokens from local configuration, CI secrets, and
credential stores, and revoke tokens created solely for Roadmap.

See Also
========

- :doc:`quickstart` - Get started in 5 minutes
- :doc:`../user-guide/commands` - Full command reference
- :doc:`../troubleshooting` - Common issues
