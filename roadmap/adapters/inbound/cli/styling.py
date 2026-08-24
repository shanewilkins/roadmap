"""CLI styling constants.

Shared color schemes and styling for CLI output.
"""

# Status colors for terminal display
STATUS_COLORS = {
    "todo": "blue",
    "in-progress": "yellow",
    "blocked": "red",
    "review": "magenta",
    "closed": "green",
}

# Priority colors for terminal display
PRIORITY_COLORS = {
    "critical": "bold red",
    "high": "red",
    "medium": "yellow",
    "low": "green",
}
