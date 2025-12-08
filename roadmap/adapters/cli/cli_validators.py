"""CLI validation helpers - shared across all command modules.

This module provides reusable validation functions for common CLI patterns:
- Date parsing (YYYY-MM-DD format)
- Priority/Status enum conversion  
- Archive/Restore argument validation
- Archive existence checks

Consolidates duplicated validation logic across issue, milestone, and project commands.
"""

from datetime import datetime
from pathlib import Path

from roadmap.common.console import get_console

console = get_console()


# ===== Date Validation =====


def parse_date(date_str: str, field_name: str = "date") -> datetime | None:
    """Parse date string in YYYY-MM-DD format.
    
    Args:
        date_str: Date string to parse (YYYY-MM-DD)
        field_name: Name of field for error message
        
    Returns:
        datetime object if valid, None if invalid
    """
    if not date_str:
        return None
        
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        console.print(
            f"❌ Invalid {field_name} format. Use YYYY-MM-DD (e.g., 2025-12-31)",
            style="bold red",
        )
        return None


def parse_iso_date(date_string: str) -> str | None:
    """Parse date string and return ISO format.
    
    Args:
        date_string: Date string to parse (YYYY-MM-DD)
        
    Returns:
        ISO format string if valid, None if invalid
    """
    if not date_string:
        return None
        
    try:
        return datetime.strptime(date_string, "%Y-%m-%d").isoformat()
    except ValueError:
        console.print(
            "❌ Invalid date format. Use YYYY-MM-DD",
            style="bold red",
        )
        return None


# ===== Priority/Status Validation =====


def validate_priority(priority_str: str, domain_module=None):
    """Validate and convert priority string to Priority enum.
    
    Args:
        priority_str: Priority string (critical, high, medium, low)
        domain_module: Optional domain module for custom Priority class
        
    Returns:
        Priority enum if valid, None if invalid
    """
    if domain_module is None:
        from roadmap.core.domain import Priority
    else:
        Priority = domain_module.Priority
        
    try:
        return Priority(priority_str.upper())
    except ValueError:
        console.print(
            f"❌ Invalid priority: {priority_str}. Use: critical, high, medium, low",
            style="bold red",
        )
        return None


def validate_project_status(status_str: str):
    """Validate and convert project status string to ProjectStatus enum.
    
    Args:
        status_str: Status string (planning, active, on-hold, completed, cancelled)
        
    Returns:
        ProjectStatus enum if valid, None if invalid
    """
    from roadmap.core.domain.project import ProjectStatus
    
    status_map = {
        "planning": ProjectStatus.PLANNING,
        "active": ProjectStatus.ACTIVE,
        "on-hold": ProjectStatus.ON_HOLD,
        "completed": ProjectStatus.COMPLETED,
        "cancelled": ProjectStatus.CANCELLED,
    }
    
    if status_str not in status_map:
        console.print(
            f"❌ Invalid status: {status_str}. Use: planning, active, on-hold, completed, cancelled",
            style="bold red",
        )
        return None
    
    return status_map[status_str]


def validate_milestone_status(status_str: str):
    """Validate and convert milestone status string to MilestoneStatus enum.
    
    Args:
        status_str: Status string (open, closed)
        
    Returns:
        MilestoneStatus enum if valid, None if invalid
    """
    from roadmap.core.domain import MilestoneStatus
    
    try:
        return MilestoneStatus(status_str)
    except ValueError:
        console.print(
            f"❌ Invalid milestone status: {status_str}. Use: open, closed",
            style="bold red",
        )
        return None


# ===== Archive/Restore Validation =====


def validate_archive_arguments(entity_id: str | None, all_flag: bool, entity_type: str = "item") -> bool:
    """Validate archive command arguments.
    
    Args:
        entity_id: Specific entity ID to archive
        all_flag: Flag for archiving all eligible entities
        entity_type: Type of entity (issue, milestone, project) for error messages
        
    Returns:
        True if arguments are valid, False otherwise
    """
    if not entity_id and not all_flag:
        console.print(
            f"❌ Error: Specify a {entity_type} ID or use --all",
            style="bold red",
        )
        return False
    
    if entity_id and all_flag:
        console.print(
            f"❌ Error: Cannot specify {entity_type} ID with --all",
            style="bold red",
        )
        return False
    
    return True


def validate_restore_arguments(entity_id: str | None, all_flag: bool, entity_type: str = "item") -> bool:
    """Validate restore command arguments.
    
    Args:
        entity_id: Specific entity ID to restore
        all_flag: Flag for restoring all archived entities
        entity_type: Type of entity (issue, milestone, project) for error messages
        
    Returns:
        True if arguments are valid, False otherwise
    """
    if not entity_id and not all_flag:
        console.print(
            f"❌ Error: Specify a {entity_type} ID or use --all",
            style="bold red",
        )
        return False
    
    if entity_id and all_flag:
        console.print(
            f"❌ Error: Cannot specify {entity_type} ID with --all",
            style="bold red",
        )
        return False
    
    return True


def check_archive_exists(archive_dir: Path, entity_type: str = "items") -> bool:
    """Check if archive directory exists.
    
    Args:
        archive_dir: Path to archive directory
        entity_type: Type of entity (issues, milestones, projects) for messages
        
    Returns:
        True if archive exists and has content, False otherwise
    """
    if not archive_dir.exists():
        console.print(f"📋 No archived {entity_type} found.", style="yellow")
        return False
    
    return True
