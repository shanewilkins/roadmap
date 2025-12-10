"""Project table formatting and display."""

from roadmap.common.output_models import ColumnDef, ColumnType, TableData


class ProjectTableFormatter:
    """Formats projects for display and structured output."""

    @staticmethod
    def projects_to_table_data(
        projects: list, title: str = "Projects", description: str = ""
    ) -> TableData:
        """Convert Project list to TableData for structured output.

        Args:
            projects: List of project metadata dictionaries or Project objects.
            title: Optional table title.
            description: Optional filter description.

        Returns:
            TableData object ready for rendering in any format.
        """
        columns = [
            ColumnDef(
                name="id",
                display_name="ID",
                type=ColumnType.STRING,
                width=10,
                display_style="cyan",
                sortable=True,
                filterable=True,
            ),
            ColumnDef(
                name="name",
                display_name="Name",
                type=ColumnType.STRING,
                width=25,
                display_style="white",
                sortable=True,
                filterable=True,
            ),
            ColumnDef(
                name="status",
                display_name="Status",
                type=ColumnType.ENUM,
                width=12,
                display_style="magenta",
                enum_values=["planning", "active", "on-hold", "completed", "cancelled"],
                sortable=True,
                filterable=True,
            ),
            ColumnDef(
                name="priority",
                display_name="Priority",
                type=ColumnType.ENUM,
                width=10,
                display_style="yellow",
                enum_values=["critical", "high", "medium", "low"],
                sortable=True,
                filterable=True,
            ),
            ColumnDef(
                name="owner",
                display_name="Owner",
                type=ColumnType.STRING,
                width=15,
                display_style="green",
                sortable=True,
                filterable=True,
            ),
        ]

        rows = []
        for project in projects:
            # Handle both dict and object formats
            if isinstance(project, dict):
                project_id = project.get("id", "unknown")[:8]
                project_name = project.get("name", "Unnamed")
                project_status = project.get("status", "unknown")
                project_priority = project.get("priority", "medium")
                project_owner = project.get("owner", "Unassigned")
            else:
                # Handle Project object
                project_id = getattr(project, "id", "unknown")[:8]
                project_name = getattr(project, "name", "Unnamed")
                project_status = getattr(project, "status", "unknown")
                if hasattr(project_status, "value"):
                    project_status = project_status.value
                project_priority = getattr(project, "priority", "medium")
                if hasattr(project_priority, "value"):
                    project_priority = project_priority.value
                project_owner = getattr(project, "owner", "Unassigned")

            rows.append(
                [
                    project_id,
                    project_name,
                    project_status,
                    project_priority,
                    project_owner,
                ]
            )

        return TableData(
            columns=columns,
            rows=rows,
            title=title,
            description=description,
            total_count=len(projects),
            returned_count=len(projects),
        )
