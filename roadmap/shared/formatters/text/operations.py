"""CLI operation feedback formatting."""


def format_operation_success(
    emoji: str,
    action: str,
    entity_title: str | None = None,
    entity_id: str | None = None,
    reason: str | None = None,
    extra_details: dict[str, str] | None = None,
) -> list[str]:
    """
    Format a successful operation message with consistent styling.

    Returns a list of formatted lines for console output.

    Args:
        emoji: Emoji to display (e.g., "✅", "🚫", "📊")
        action: Action verb (e.g., "Blocked", "Closed", "Updated")
        entity_title: Title/name of the entity affected (e.g., issue title)
        entity_id: ID of the entity (displayed separately as cyan)
        reason: Optional reason for the operation
        extra_details: Optional dict of additional details to display

    Returns:
        List of formatted output lines
    """
    lines = []

    # Main success line: emoji + action + title
    if entity_title:
        lines.append(f"{emoji} {action} issue: {entity_title}")
    else:
        lines.append(f"{emoji} {action}")

    # Entity ID line (if provided)
    if entity_id:
        lines.append(f"   ID: {entity_id}")

    # Reason line (if provided)
    if reason:
        lines.append(f"   Reason: {reason}")

    # Extra details (if provided)
    if extra_details:
        for key, value in extra_details.items():
            lines.append(f"   {key}: {value}")

    return lines


def format_operation_failure(
    action: str,
    entity_id: str | None = None,
    error: str | None = None,
    suggestion: str | None = None,
) -> list[str]:
    """
    Format a failed operation message with consistent styling.

    Returns a list of formatted lines for console output.

    Args:
        action: Action that failed (e.g., "block", "close", "update")
        entity_id: ID of the entity that failed (optional)
        error: Error message/reason for failure
        suggestion: Suggested recovery action

    Returns:
        List of formatted output lines
    """
    lines = []

    # Main failure line
    if entity_id:
        lines.append(f"❌ Failed to {action} issue: {entity_id}")
    else:
        lines.append(f"❌ Failed to {action}")

    # Error details (if provided)
    if error:
        lines.append(f"   Error: {error}")

    # Suggestion (if provided)
    if suggestion:
        lines.append(f"   💡 {suggestion}")

    return lines


def format_entity_details(
    entity_id: str,
    entity_title: str | None = None,
    entity_type: str = "item",
    status: str | None = None,
    details: dict[str, str] | None = None,
) -> list[str]:
    """
    Format entity details for consistent display across commands.

    Args:
        entity_id: ID of the entity
        entity_title: Title/name of the entity
        entity_type: Type of entity (e.g., "issue", "milestone")
        status: Current status of entity
        details: Additional details dict

    Returns:
        List of formatted output lines
    """
    lines = []

    # ID and title
    if entity_title:
        lines.append(f"📋 {entity_type.title()}: {entity_title}")
    lines.append(f"   ID: {entity_id}")

    # Status
    if status:
        lines.append(f"   Status: {status}")

    # Additional details
    if details:
        for key, value in details.items():
            lines.append(f"   {key}: {value}")

    return lines


def format_list_items(
    items: list[dict[str, str]],
    show_count: int | None = None,
    more_suffix: str = "... and {count} more",
) -> list[str]:
    """
    Format a list of items consistently.

    Args:
        items: List of dicts with 'id' and 'title' keys minimum
        show_count: Maximum items to show (None = show all)
        more_suffix: Format string for "... and X more" suffix

    Returns:
        List of formatted output lines
    """
    lines = []

    # Determine how many to show
    items_to_show = items
    remaining = 0
    if show_count and len(items) > show_count:
        items_to_show = items[:show_count]
        remaining = len(items) - show_count

    # Format each item
    for item in items_to_show:
        item_id = item.get("id", "")[:8]  # Show first 8 chars of ID
        title = item.get("title", "")
        lines.append(f"   • {item_id} - {title}")

    # Add "... and X more" if truncated
    if remaining > 0:
        lines.append(more_suffix.format(count=remaining))

    return lines


# Console wrapper functions for CLI commands that need to print and potentially exit
def print_operation_success(
    console,
    emoji: str,
    action: str,
    entity_title: str | None = None,
    entity_id: str | None = None,
    reason: str | None = None,
    extra_details: dict[str, str] | None = None,
) -> None:
    """Print a successful operation message to console."""
    lines = format_operation_success(
        emoji, action, entity_title, entity_id, reason, extra_details
    )
    for line in lines:
        console.print(line)


def print_operation_failure(
    console,
    action: str,
    entity_id: str | None = None,
    error: str | None = None,
    suggestion: str | None = None,
) -> None:
    """Print a failed operation message to console."""
    lines = format_operation_failure(action, entity_id, error, suggestion)
    for line in lines:
        console.print(line)
