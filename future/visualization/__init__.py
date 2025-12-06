"""Visualization package - Data visualization and formatting.

The visualization package provides chart and dashboard generation:
- ChartGenerator: Generate individual charts (status, burndown, velocity, etc.)
- DashboardGenerator: Generate comprehensive dashboards

Usage:
from roadmap.application.visualization import ChartGenerator, DashboardGenerator
chart_gen = ChartGenerator(artifacts_dir)
chart_gen.generate_status_distribution_chart(issues)
"""

from .charts import ChartGenerator, DashboardGenerator, VisualizationError

__all__ = ["ChartGenerator", "DashboardGenerator", "VisualizationError"]
