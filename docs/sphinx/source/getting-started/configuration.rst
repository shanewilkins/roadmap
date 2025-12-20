================================================================================
Configuration
================================================================================

Configuring Roadmap CLI for your workflow.

.. note::

   This is a stub. Complete implementation coming in v.0.7.0.

Configuration File
==================

Roadmap CLI reads configuration from ``.roadmap/config.yaml``:

.. code-block:: yaml

    # Example configuration
    project_root: .
    data_format: json

Environment Variables
======================

You can also configure Roadmap via environment variables:

- ``ROADMAP_PROJECT_ROOT`` - Project root directory
- ``ROADMAP_DATA_FORMAT`` - Data format (json, yaml)

See the full :doc:`../user-guide/commands` for all options.
