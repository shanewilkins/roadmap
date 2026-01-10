import click

from roadmap.common.console import get_console
from roadmap.core.services.sync_report import SyncReport


def present_analysis(report: SyncReport, verbose: bool = False) -> None:
    console = get_console()
    console.print("\n[bold cyan]🔎 Sync Analysis (preview)[/bold cyan]")
    if verbose:
        report.display_verbose()
    else:
        report.display_brief()


def confirm_apply(default: bool = True) -> bool:
    """Ask the user to confirm applying changes.

    Returns True if user confirms, False otherwise.
    """
    prompt = "Apply these changes now?"
    return click.confirm(prompt, default=default)
