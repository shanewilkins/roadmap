"""
Application Layer - Use Cases & Orchestration

This layer coordinates between domain logic and infrastructure.
Contains services that implement specific use cases and features.

Structure:
- services/: Business logic orchestrators
  - issue_service.py: Issue operations
  - milestone_service.py: Milestone operations
  - project_service.py: Project operations
- visualization/: Data visualization & formatting
  - timeline.py: Timeline visualization
  - progress.py: Progress/burndown charts
  - burndown.py: Burndown analysis
  - renderers/: Output formatting (ASCII, JSON, HTML)
- core.py: Main orchestrator (RoadmapCore)

Guidelines:
- Services depend on domain + infrastructure
- Services handle business workflows
- Services should be <400 lines each
- Visualization modules handle output generation
"""

from .core import RoadmapCore

__all__ = ["RoadmapCore"]
