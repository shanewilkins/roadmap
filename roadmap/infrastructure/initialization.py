"""Roadmap initialization and setup management.

Handles creation of new roadmap projects, directory structures,
configuration files, and git integration setup.
"""

import sqlite3
from pathlib import Path
from typing import Optional

from roadmap.common.security import (
    create_secure_directory,
    create_secure_file,
)


class InitializationManager:
    """Manages roadmap initialization, configuration, and setup."""

    def __init__(self, root_path: Path, roadmap_dir_name: str = ".roadmap"):
        """Initialize the manager with paths.

        Args:
            root_path: Root directory of the project
            roadmap_dir_name: Name of the roadmap directory (default: .roadmap)
        """
        self.root_path = root_path
        self.roadmap_dir_name = roadmap_dir_name
        self.roadmap_dir = self.root_path / roadmap_dir_name
        self.issues_dir = self.roadmap_dir / "issues"
        self.milestones_dir = self.roadmap_dir / "milestones"
        self.projects_dir = self.roadmap_dir / "projects"
        self.templates_dir = self.roadmap_dir / "templates"
        self.artifacts_dir = self.roadmap_dir / "artifacts"
        self.config_file = self.roadmap_dir / "config.yaml"
        self.db_dir = self.roadmap_dir / "db"

    def is_initialized(self) -> bool:
        """Check if roadmap is already initialized."""
        return self.roadmap_dir.exists() and self.config_file.exists()

    @classmethod
    def find_existing_roadmap(
        cls, root_path: Path | None = None, roadmap_dir_name: str = ".roadmap"
    ) -> Optional["InitializationManager"]:
        """Find an existing roadmap directory in the current path.

        Searches for roadmap directory and returns a manager instance if found,
        or None if no roadmap is detected.

        Args:
            root_path: Root path to search from (defaults to current directory)
            roadmap_dir_name: Name of the roadmap directory to search for

        Returns:
            InitializationManager if roadmap found, None otherwise
        """
        search_path = root_path or Path.cwd()

        # Common roadmap directory names to search for
        possible_names = [roadmap_dir_name]

        # Also check for any directory containing the expected structure
        try:
            for item in search_path.iterdir():
                if item.is_dir() and item.name not in possible_names:
                    possible_names.append(item.name)
        except (OSError, PermissionError):
            pass

        # Check each possible directory
        for dir_name in possible_names:
            try:
                potential_manager = cls(
                    root_path=search_path, roadmap_dir_name=dir_name
                )
                if potential_manager.is_initialized():
                    return potential_manager
            except (OSError, PermissionError, sqlite3.OperationalError):
                # Skip directories that can't be accessed
                continue

        return None

    def initialize(self) -> None:
        """Initialize a new roadmap in the current directory.

        Raises:
            ValueError: If roadmap is already initialized
        """
        if self.is_initialized():
            raise ValueError("Roadmap already initialized in this directory")

        # Create directory structure with secure permissions
        create_secure_directory(self.roadmap_dir, 0o755)
        create_secure_directory(self.issues_dir, 0o755)
        create_secure_directory(self.milestones_dir, 0o755)
        create_secure_directory(self.projects_dir, 0o755)
        create_secure_directory(self.templates_dir, 0o755)
        create_secure_directory(self.artifacts_dir, 0o755)

        # Update .gitignore to exclude roadmap local data
        self._update_gitignore()

        # Create templates
        self._create_default_templates()

        # Create default config file
        self._create_default_config()

    def _create_default_templates(self) -> None:
        """Create default templates for issues, milestones, and projects."""
        # Issue template
        issue_template = """---
id: "{{ issue_id }}"
title: "{{ title }}"
priority: "medium"
status: "todo"
milestone: ""
labels: []
github_issue: null
created: "{{ created_date }}"
updated: "{{ updated_date }}"
assignee: ""
---

# {{ title }}

## Description

Brief description of the issue or feature request.

## Acceptance Criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Technical Notes

Any technical details, considerations, or implementation notes.

## Related Issues

- Links to related issues
- Dependencies

## Additional Context

Any additional context, screenshots, or examples."""

        with create_secure_file(self.templates_dir / "issue.md", "w", 0o644) as f:
            f.write(issue_template)

        # Milestone template
        milestone_template = """---
name: "{{ milestone_name }}"
description: "{{ description }}"
due_date: "{{ due_date }}"
status: "open"
github_milestone: null
created: "{{ created_date }}"
updated: "{{ updated_date }}"
---

# {{ milestone_name }}

## Description

{{ description }}

## Goals

- [ ] Goal 1
- [ ] Goal 2
- [ ] Goal 3

## Success Criteria

Define what success looks like for this milestone.

## Notes

Any additional notes or considerations for this milestone."""

        with create_secure_file(self.templates_dir / "milestone.md", "w", 0o644) as f:
            f.write(milestone_template)

        # Project template
        project_template = """---
id: "{{ project_id }}"
name: "{{ project_name }}"
description: "{{ project_description }}"
status: "planning"
priority: "medium"
owner: "{{ project_owner }}"
start_date: "{{ start_date }}"
target_end_date: "{{ target_end_date }}"
actual_end_date: null
created: "{{ created_date }}"
updated: "{{ updated_date }}"
milestones:
  - "{{ milestone_1 }}"
  - "{{ milestone_2 }}"
estimated_hours: {{ estimated_hours }}
actual_hours: null
---

# {{ project_name }}

## Project Overview

{{ project_description }}

**Project Owner:** {{ project_owner }}
**Status:** {{ status }}
**Timeline:** {{ start_date }} → {{ target_end_date }}

## Objectives

- [ ] Objective 1
- [ ] Objective 2
- [ ] Objective 3

## Milestones & Timeline

{% for milestone in milestones %}
- **{{ milestone }}** - [Link to milestone](../milestones/{{ milestone }}.md)
{% endfor %}

## Timeline Tracking

- **Start Date:** {{ start_date }}
- **Target End Date:** {{ target_end_date }}
- **Actual End Date:** {{ actual_end_date }}
- **Estimated Hours:** {{ estimated_hours }}
- **Actual Hours:** {{ actual_hours }}

## Notes

Project notes and additional context.

---
*Last updated: {{ updated_date }}*"""

        with create_secure_file(self.templates_dir / "project.md", "w", 0o644) as f:
            f.write(project_template)

    def _create_default_config(self) -> None:
        """Create default configuration file."""
        import yaml

        config_data = {
            "project_name": "My Roadmap",
            "github": None,
            "defaults": {
                "priority": "medium",
                "issue_type": "other",
            },
            "features": {
                "github_integration": False,
                "git_sync": False,
            },
        }

        with create_secure_file(self.config_file, "w", 0o644) as f:
            yaml.dump(config_data, f, default_flow_style=False)

    def _update_gitignore(self) -> None:
        """Update .gitignore to exclude roadmap local data from version control."""
        gitignore_path = self.root_path / ".gitignore"

        # Define patterns to ignore
        roadmap_patterns = [
            f"{self.roadmap_dir_name}/artifacts/",
            f"{self.roadmap_dir_name}/backups/",
            f"{self.roadmap_dir_name}/logs/",
            f"{self.roadmap_dir_name}/*.tmp",
            f"{self.roadmap_dir_name}/*.lock",
        ]
        gitignore_comment = (
            "# Roadmap local data (generated exports, backups, logs, temp files)"
        )

        # Read existing .gitignore if it exists
        existing_lines = []
        if gitignore_path.exists():
            existing_lines = gitignore_path.read_text().splitlines()

        # Check which patterns are already present
        missing_patterns = []
        for pattern in roadmap_patterns:
            if not any(line.strip() == pattern for line in existing_lines):
                missing_patterns.append(pattern)

        if missing_patterns:
            # Add missing patterns
            if existing_lines and not existing_lines[-1].strip() == "":
                existing_lines.append("")

            existing_lines.append(gitignore_comment)
            existing_lines.extend(missing_patterns)

            # Write updated .gitignore
            gitignore_path.write_text("\n".join(existing_lines) + "\n")
