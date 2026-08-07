"""Shared Click option definitions for CLI commands."""

import click


def verbose_option(f):
    """Add --verbose / -v flag to a command."""
    return click.option(
        "--verbose",
        "-v",
        is_flag=True,
        help="Show detailed debug information and all health check logs",
    )(f)


def format_option(f):
    """Add --format / -f option to a command."""
    return click.option(
        "--format",
        "-f",
        type=click.Choice(["plain", "json"], case_sensitive=False),
        default="plain",
        help="Output format (default: plain text)",
    )(f)


def details_option(f):
    """Add --details flag to a command."""
    return click.option(
        "--details",
        is_flag=True,
        help="Show detailed recommendations and fix commands for each check",
    )(f)


def health_check_options(f):
    """Add all health check options (--verbose, --details, --format) to a command."""
    return verbose_option(details_option(format_option(f)))
