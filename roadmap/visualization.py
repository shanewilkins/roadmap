"""Backward compatibility shim for visualization module.

This module has been refactored into the application/visualization package.
All exports are re-exported here for backward compatibility.

Imports from this module will still work but new code should import from:
  from roadmap.application.visualization import ChartGenerator, DashboardGenerator

This shim will be maintained for v1.0 release and removed in v2.0.
"""

# Re-export from new location
from roadmap.application.visualization import (
    ChartGenerator,
    DashboardGenerator,
    VisualizationError,
)

__all__ = ["ChartGenerator", "DashboardGenerator", "VisualizationError"]
