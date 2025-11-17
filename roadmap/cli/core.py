"""
Core CLI commands: init and status.
These are the fundamental commands needed to get started with Roadmap.
"""

import getpass
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

import click
import yaml
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table
from rich.text import Text

from roadmap.cli.utils import get_console
from roadmap.core import RoadmapCore
from roadmap.models import Status

console = get_console()
# Import GitHub client and credential manager at module level so they can be patched in tests
try:
    from roadmap.credentials import CredentialManager
    from roadmap.github_client import GitHubClient
except Exception:
    GitHubClient = None
    CredentialManager = None


@click.command()
@click.option(
    "--name",
    "-n",
    default=".roadmap",
    help="Name of the roadmap directory (default: .roadmap)",
)
@click.option(
    "--project-name",
    help="Name of the main project (auto-detected if not provided)",
)
@click.option(
    "--description",
    help="Project description",
)
@click.option(
    "--github-repo",
    help="GitHub repository in owner/repo format",
)
@click.option(
    "--skip-github",
    is_flag=True,
    help="Skip GitHub integration setup",
)
@click.option(
    "--skip-project",
    is_flag=True,
    help="Skip automatic project creation",
)
@click.option(
    "--interactive/--non-interactive",
    default=True,
    help="Run in interactive mode with prompts (default: interactive)",
)
@click.option(
    "--template",
    type=click.Choice(["basic", "software", "research", "team"]),
    default="basic",
    help="Use project template",
)
@click.option(
    "--template-path",
    type=click.Path(exists=False),
    help="Path to a custom project template file (markdown).",
)
@click.option(
    "--github-token",
    help="Provide a GitHub personal access token to configure integration non-interactively",
)
@click.option(
    "--dry-run", is_flag=True, help="Show what would be created without making changes"
)
@click.option(
    "--yes", "-y", is_flag=True, help="Automatic yes to prompts (assume defaults)"
)
@click.option(
    "--force", is_flag=True, help="Force re-initialization when roadmap already exists"
)
@click.pass_context
def init(
    ctx: click.Context,
    name: str,
    project_name: str | None,
    description: str | None,
    github_repo: str | None,
    skip_github: bool,
    skip_project: bool,
    interactive: bool,
    dry_run: bool,
    yes: bool,
    force: bool,
    template: str,
    template_path: str | None,
    github_token: str | None,
) -> None:
    """Initialize a new roadmap with automatic project setup and credential flow.

    Examples:
        roadmap init                              # Interactive setup with auto-detection
        roadmap init --project-name "My Project" # Specify project name
        roadmap init --skip-github               # Skip GitHub integration
        roadmap init --github-repo owner/repo    # Specify GitHub repository
        roadmap init --template software         # Use software project template
    """

    # Create a new core instance with the custom directory name
    custom_core = RoadmapCore(roadmap_dir_name=name)

    # Global init lock path prevents concurrent inits
    lock_path = Path.cwd() / ".roadmap_init.lock"

    if lock_path.exists():
        console.print(
            "❌ Initialization already in progress (lockfile present). Try again later.",
            style="bold red",
        )
        return

    if custom_core.is_initialized():
        if not force:
            console.print(
                f"❌ Roadmap already initialized in {name}/ directory", style="bold red"
            )
            console.print(
                "Tip: use --force to reinitialize or --dry-run to preview.",
                style="yellow",
            )
            return
        else:
            if dry_run:
                console.print(
                    f"🟡 Dry run: would remove existing {name}/ and reinitialize",
                    style="yellow",
                )
                return
            # Proceed to remove existing and reinitialize
            console.print(
                f"⚠️  --force specified: removing existing {name}/", style="yellow"
            )
            import shutil

            try:
                if custom_core.roadmap_dir.exists():
                    shutil.rmtree(custom_core.roadmap_dir)
            except Exception as e:
                console.print(
                    f"❌ Failed to remove existing roadmap: {e}", style="bold red"
                )
                return

    # Enhanced initialization flow
    console.print("🚀 Roadmap CLI Initialization", style="bold cyan")
    console.print()

    # If dry-run, show planned steps and exit before making changes
    if dry_run:
        console.print(
            "ℹ️  Dry run mode enabled - no changes will be made.", style="yellow"
        )
        console.print(
            f"Planned actions:\n - Create roadmap directory: {name}/\n - Create default templates and config\n - Create main project (unless --skip-project)\n - Optionally configure GitHub (unless --skip-github)"
        )
        return

    try:
        # Create a lock file to indicate init in progress
        try:
            lock_path.write_text(
                f"pid:{os.getpid()}\nstarted:{datetime.now().isoformat()}\n"
            )
        except Exception:
            # If lock cannot be created, continue but warn
            console.print(
                "⚠️  Could not create init lockfile; proceeding with care",
                style="yellow",
            )

        # Prepare an init manifest to record created paths for potential rollback
        manifest = {"created": []}

        # Step 1: Context Detection
        detected_info = _detect_project_context()
        console.print("🔍 Detected Context:", style="bold blue")
        if detected_info.get("git_repo"):
            console.print(f"  Git repository: {detected_info['git_repo']}")
        else:
            console.print("  Git repository: Not detected", style="dim")
            if interactive:
                console.print(
                    "    💡 Consider running 'git init' to enable advanced features",
                    style="yellow",
                )
        if detected_info.get("project_name"):
            console.print(f"  Project name: {detected_info['project_name']}")
        console.print(f"  Directory: {Path.cwd()}")
        console.print()

        # Step 2: Basic roadmap initialization
        with console.status(
            f"🗂️  Creating roadmap structure in {name}/...", spinner="dots"
        ):
            custom_core.initialize()
        # Record common created items (we'll check existence before writing)
        try:
            if custom_core.roadmap_dir.exists():
                manifest["created"].append(str(custom_core.roadmap_dir))
            if custom_core.projects_dir.exists():
                manifest["created"].append(str(custom_core.projects_dir))
            if custom_core.templates_dir.exists():
                manifest["created"].append(str(custom_core.templates_dir))
            if custom_core.config_file.exists():
                manifest["created"].append(str(custom_core.config_file))
            # Write manifest inside .roadmap for easy reference
            try:
                (custom_core.roadmap_dir / ".init_manifest.json").write_text(
                    json.dumps(manifest)
                )
            except Exception:
                # Best-effort
                pass
        except Exception:
            pass

        # Update the context to use the custom core
        ctx.obj["core"] = custom_core

        # Step 3: Project creation (unless skipped)
        project_info = None
        if not skip_project:
            with console.status("📋 Creating main project...", spinner="dots"):
                project_info = _setup_main_project(
                    custom_core,
                    project_name,
                    description,
                    detected_info,
                    interactive,
                    template,
                    yes,
                    template_path,
                )
            # append project file to manifest if present
            try:
                if project_info and "filename" in project_info:
                    manifest_file = (
                        custom_core.roadmap_dir / "projects" / project_info["filename"]
                    )
                    if manifest_file.exists():
                        manifest.setdefault("created", []).append(str(manifest_file))
                        try:
                            (
                                custom_core.roadmap_dir / ".init_manifest.json"
                            ).write_text(json.dumps(manifest))
                        except Exception:
                            pass
            except Exception:
                pass
            console.print(
                f"✅ Created main project: {project_info['name']} (ID: {project_info['id'][:8]})"
            )

        # Step 4: GitHub integration (unless skipped)
        github_configured = False
        repo_name = github_repo or detected_info.get("git_repo")
        if not skip_github and repo_name:
            with console.status("🔗 Configuring GitHub integration...", spinner="dots"):
                github_configured = _setup_github_integration(
                    custom_core,
                    repo_name,
                    interactive,
                    yes,
                    token=github_token,
                )

        # Step 5: Success summary and next steps
        # Post-init validation: ensure created files and permissions look correct
        validation_ok = _post_init_validate(custom_core, name, project_info)
        if not validation_ok:
            console.print(
                "⚠️  Initialization completed with warnings; see above.", style="yellow"
            )

        _show_success_summary(name, github_configured, project_info, detected_info)

    except Exception as e:
        console.print(f"❌ Failed to initialize roadmap: {e}", style="bold red")
        # Attempt targeted rollback using manifest if present
        try:
            manifest_file = custom_core.roadmap_dir / ".init_manifest.json"
            if manifest_file.exists():
                try:
                    data = json.loads(manifest_file.read_text())
                    import shutil

                    for p in data.get("created", []):
                        try:
                            ppath = Path(p)
                            if ppath.is_file():
                                ppath.unlink()
                            elif ppath.is_dir():
                                shutil.rmtree(ppath)
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass
        # Fallback: remove the whole roadmap dir if it exists
        if custom_core.roadmap_dir.exists():
            import shutil

            shutil.rmtree(custom_core.roadmap_dir)
        # Do not re-raise the exception — surface a friendly message and exit
        return
    finally:
        # Remove init lock if present
        try:
            if lock_path.exists():
                lock_path.unlink()
        except Exception:
            pass


@click.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show the current status of the roadmap."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        console.print("📊 Roadmap Status", style="bold blue")

        # Get all issues and milestones from database
        issues = core.db.get_all_issues()
        milestones = core.db.get_all_milestones()

        # Convert database results to compatible format
        issues = [
            type(
                "Issue",
                (),
                {
                    "id": issue["id"],
                    "title": issue["title"],
                    "status": issue["status"],
                    "assignee": issue.get("assignee"),
                    "milestone": issue.get("milestone_name", issue.get("milestone_id")),
                },
            )()
            for issue in issues
        ]

        milestones = [
            type(
                "Milestone",
                (),
                {
                    "name": ms["name"],
                    "title": ms["title"],
                },
            )()
            for ms in milestones
        ]

        if not issues and not milestones:
            console.print("\n📝 No issues or milestones found.", style="yellow")
            console.print("Get started with:")
            console.print("  roadmap issue create 'My first issue'")
            console.print("  roadmap milestone create 'My first milestone'")
            return

        # Show milestone progress
        if milestones:
            console.print("\n🎯 Milestones:", style="bold cyan")
            for ms in milestones:
                progress = core.db.get_milestone_progress(ms.title)
                console.print(f"\n  {ms.title}")

                if progress["total"] > 0:
                    with Progress(
                        TextColumn("[progress.description]{task.description}"),
                        BarColumn(),
                        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                        console=console,
                        transient=True,
                    ) as progress_bar:
                        progress_bar.add_task(
                            f"    Progress ({progress['completed']}/{progress['total']})",
                            total=progress["total"],
                            completed=progress["completed"],
                        )
                else:
                    console.print("    No issues assigned", style="dim")

        # Show issues by status
        console.print("\n📋 Issues by Status:", style="bold cyan")
        status_counts = core.db.get_issues_by_status()

        if status_counts:
            status_table = Table(show_header=False, box=None)
            status_table.add_column("Status", style="white", width=15)
            status_table.add_column("Count", style="cyan", width=10)

            for status in Status:
                count = status_counts.get(status, 0)
                status_style = {
                    Status.TODO: "white",
                    Status.IN_PROGRESS: "yellow",
                    Status.BLOCKED: "red",
                    Status.REVIEW: "blue",
                    Status.DONE: "green",
                }.get(status, "white")

                status_table.add_row(
                    Text(f"  {status.value}", style=status_style), str(count)
                )

            console.print(status_table)
        else:
            console.print("  No issues found", style="dim")

    except Exception as e:
        console.print(f"❌ Failed to show status: {e}", style="bold red")


# Helper functions for init command


def _detect_project_context() -> dict:
    """Detect project context from git repository and directory structure."""
    context = {
        "git_repo": None,
        "project_name": None,
        "git_user": None,
        "has_git": False,
    }

    try:
        # Check if we're in a git repository
        git_check = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        context["has_git"] = git_check.returncode == 0

        if context["has_git"]:
            # Try to get git repository info
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                origin_url = result.stdout.strip()
                # Parse GitHub repository from URL
                if "github.com" in origin_url:
                    # Handle both SSH and HTTPS URLs
                    if origin_url.startswith("git@github.com:"):
                        repo_part = origin_url.replace("git@github.com:", "").replace(
                            ".git", ""
                        )
                    elif "github.com/" in origin_url:
                        repo_part = origin_url.split("github.com/")[1].replace(
                            ".git", ""
                        )
                    else:
                        repo_part = None

                    if repo_part and "/" in repo_part:
                        context["git_repo"] = repo_part
                        context["project_name"] = repo_part.split("/")[1]

            # Get git user info
            try:
                user_result = subprocess.run(
                    ["git", "config", "user.name"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if user_result.returncode == 0:
                    context["git_user"] = user_result.stdout.strip()
            except Exception:
                pass

    except (
        subprocess.TimeoutExpired,
        subprocess.CalledProcessError,
        FileNotFoundError,
    ):
        pass

    # Fallback to directory name if no git repo detected
    if not context["project_name"]:
        context["project_name"] = Path.cwd().name

    # Try to detect from package files
    if not context["project_name"] or context["project_name"] == ".":
        for config_file in ["pyproject.toml", "package.json", "Cargo.toml"]:
            if Path(config_file).exists():
                try:
                    content = Path(config_file).read_text()
                    if config_file == "pyproject.toml":
                        import re

                        match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
                        if match:
                            context["project_name"] = match.group(1)
                            break
                    elif config_file == "package.json":
                        import json

                        data = json.loads(content)
                        if "name" in data:
                            context["project_name"] = data["name"]
                            break
                except Exception:
                    pass

    return context


def _setup_main_project(
    core: RoadmapCore,
    project_name: str | None,
    description: str | None,
    detected_info: dict,
    interactive: bool,
    template: str,
    yes: bool = False,
    template_path: str | None = None,
) -> dict:
    """Set up the main project document."""

    # Determine project name
    if not project_name:
        if interactive and not yes:
            suggested_name = detected_info.get("project_name", Path.cwd().name)
            project_name = click.prompt(
                "Project name", default=suggested_name, show_default=True
            )
        else:
            project_name = detected_info.get("project_name", Path.cwd().name)

    # Ensure project_name is never None
    assert project_name is not None

    # Determine description
    if not description and interactive and not yes:
        default_desc = "A project managed with Roadmap CLI"
        if detected_info.get("git_repo"):
            default_desc = f"Project repository: {detected_info['git_repo']}"
        description = click.prompt(
            "Project description", default=default_desc, show_default=True
        )
    elif not description:
        description = "A project managed with Roadmap CLI"

    # Ensure description is never None
    assert description is not None

    # Create project using core functionality
    console.print("📋 Creating main project...", style="bold blue")

    # Generate project content based on template
    # If a custom template path was provided and is valid, use its contents
    if template_path:
        try:
            tpl_path = Path(template_path)
            if tpl_path.exists() and tpl_path.is_file():
                project_content = tpl_path.read_text()
            else:
                console.print(
                    f"⚠️  Custom template not found at {template_path}; falling back to builtin template",
                    style="yellow",
                )
                project_content = _generate_project_template(
                    project_name, description, template, detected_info
                )
        except Exception as e:
            console.print(
                f"⚠️  Could not read custom template: {e}; using builtin template",
                style="yellow",
            )
            project_content = _generate_project_template(
                project_name, description, template, detected_info
            )
    else:
        project_content = _generate_project_template(
            project_name, description, template, detected_info
        )

    # Save project file
    project_id = core._generate_id()[:8]
    project_filename = f"{project_id}-{core._normalize_filename(project_name)}.md"
    project_file = core.roadmap_dir / "projects" / project_filename

    # Ensure projects directory exists
    (core.roadmap_dir / "projects").mkdir(exist_ok=True)

    project_file.write_text(project_content)

    return {"id": project_id, "name": project_name, "filename": project_filename}


def _generate_project_template(
    project_name: str, description: str, template: str, detected_info: dict
) -> str:
    """Generate project content based on template."""

    current_date = datetime.now().isoformat()
    owner = detected_info.get("git_user", getpass.getuser())

    # Base project content
    content = f"""---
name: {project_name}
description: {description}
owner: {owner}
priority: high
status: active
created: {current_date}
updated: {current_date}
"""

    if detected_info.get("git_repo"):
        content += f"github_repo: {detected_info['git_repo']}\n"

    content += (
        """timeline:
  start_date: """
        + current_date
        + """
  target_end_date: null
tags: []
---

# """
        + project_name
        + """

## Overview

"""
        + description
        + """

## Project Goals

"""
    )

    # Template-specific content
    if template == "software":
        content += """
- [ ] Develop core functionality
- [ ] Implement user interface
- [ ] Write comprehensive tests
- [ ] Deploy to production
- [ ] Document API and usage

## Technical Stack

- **Language**: Python
- **Framework**: TBD
- **Database**: TBD
- **Deployment**: TBD

## Development Phases

### Phase 1: Foundation
- Project setup and architecture
- Core functionality implementation
- Basic testing framework

### Phase 2: Features
- Feature development
- User interface implementation
- Integration testing

### Phase 3: Polish
- Performance optimization
- Documentation
- Production deployment
"""

    elif template == "research":
        content += """
- [ ] Literature review
- [ ] Hypothesis formation
- [ ] Methodology design
- [ ] Data collection
- [ ] Analysis and findings
- [ ] Publication preparation

## Research Questions

1. [Primary research question]
2. [Secondary research questions]

## Methodology

[Research methodology and approach]

## Timeline

- **Phase 1**: Literature review (4 weeks)
- **Phase 2**: Data collection (8 weeks)
- **Phase 3**: Analysis (4 weeks)
- **Phase 4**: Writing (4 weeks)
"""

    elif template == "team":
        content += """
- [ ] Team onboarding
- [ ] Process documentation
- [ ] Workflow optimization
- [ ] Knowledge sharing
- [ ] Regular retrospectives

## Team Structure

- **Project Lead**: [Name]
- **Development Team**: [Names]
- **Stakeholders**: [Names]

## Communication

- **Daily Standups**: [Time/Location]
- **Sprint Planning**: [Schedule]
- **Retrospectives**: [Schedule]

## Processes

### Development Workflow
1. Issue creation and planning
2. Feature branch development
3. Code review process
4. Testing and validation
5. Deployment and monitoring
"""

    else:  # basic template
        content += """
- [ ] Define project scope
- [ ] Create initial roadmap
- [ ] Begin implementation
- [ ] Regular progress reviews
- [ ] Project completion

## Milestones

### Milestone 1: Setup
- Initial project structure
- Team alignment on goals

### Milestone 2: Development
- Core functionality implementation
- Regular progress tracking

### Milestone 3: Completion
- Final deliverables
- Project retrospective
"""

    content += """

## Resources

- [Link to documentation]
- [Link to repository]
- [Link to project tools]

## Notes

[Additional project notes and context]
"""

    return content


def _setup_github_integration(
    core: RoadmapCore,
    github_repo: str,
    interactive: bool,
    yes: bool = False,
    token: str | None = None,
) -> bool:
    """Set up GitHub integration with credential flow."""

    console.print("🔗 GitHub Integration Setup", style="bold blue")

    if interactive and not yes:
        console.print(f"\nRepository: {github_repo}")
        console.print("\nTo sync with GitHub, you'll need a personal access token.")
        console.print("→ Open: https://github.com/settings/tokens")
        console.print(
            "→ Create token with 'repo' scope (or 'public_repo' for public repos)"
        )
        console.print(
            "→ Required permissions: Issues, Pull requests, Repository metadata"
        )
        console.print()

        if not yes and not click.confirm(
            "Do you want to set up GitHub integration now?"
        ):
            console.print(
                "⏭️  Skipping GitHub integration (you can set this up later with 'roadmap sync setup')"
            )
            return False

    try:
        # Use module-level GitHubClient and CredentialManager (patched in tests)
        if CredentialManager is None:
            raise ImportError("CredentialManager not available")
        cred_manager = CredentialManager()
        existing_token = None

        try:
            existing_token = cred_manager.get_token()
            if existing_token and interactive and not yes and not token:
                console.print("🔍 Found existing GitHub credentials")
                if click.confirm("Use existing GitHub credentials?"):
                    console.print("✅ Using existing GitHub credentials")
                else:
                    existing_token = None
        except Exception:
            pass  # No existing credentials

        # Prefer token provided via CLI, then environment, then stored
        env_token = os.environ.get("ROADMAP_GITHUB_TOKEN")
        if token:
            use_token = token
        elif env_token:
            use_token = env_token
            console.print(
                "ℹ️  Using GitHub token from environment variable ROADMAP_GITHUB_TOKEN",
                style="dim",
            )
        elif existing_token:
            use_token = existing_token
        else:
            # Get token from user if interactive
            if interactive and not yes:
                console.print(
                    "To integrate with GitHub you'll need a personal access token with 'repo' scope."
                )
                console.print("→ Create one: https://github.com/settings/tokens")
                use_token = click.prompt("Paste your GitHub token", hide_input=True)
            else:
                console.print(
                    "❌ Non-interactive mode requires providing a token via --github-token or setting ROADMAP_GITHUB_TOKEN, or use --skip-github to skip integration.",
                    style="bold red",
                )
                return False

        # Test the connection with comprehensive validation
        console.print("🔍 Testing GitHub connection...", style="yellow")
        if GitHubClient is None:
            raise ImportError("GitHubClient not available")
        github_client = GitHubClient(use_token)

        # Validate user authentication
        try:
            user_response = github_client._make_request("GET", "/user")
            user_info = user_response.json()
            console.print(f"✅ Authenticated as: {user_info.get('login', 'unknown')}")
        except Exception as e:
            console.print(f"❌ Authentication failed: {e}", style="red")
            if interactive and click.confirm(
                "Continue without GitHub integration? (recommended to skip until token is fixed)"
            ):
                return False
            else:
                raise

        # Validate repository access
        try:
            owner, repo = github_repo.split("/")
            github_client.set_repository(owner, repo)
            repo_info = github_client.test_repository_access()

            repo_name = repo_info.get("full_name", github_repo)
            console.print(f"✅ Repository access: {repo_name}")

            # Check permissions
            permissions = repo_info.get("permissions", {})
            if permissions.get("admin") or permissions.get("push"):
                console.print("✅ Write access: Available")
            elif permissions.get("pull"):
                console.print(
                    "⚠️  Read-only access: Limited sync capabilities", style="yellow"
                )
            else:
                console.print("❌ No repository access detected", style="red")

        except Exception as e:
            console.print(f"⚠️  Repository validation warning: {e}", style="yellow")
            if interactive and not yes:
                if not click.confirm("Continue with GitHub integration anyway?"):
                    return False
            # Continue anyway for non-interactive mode

        # Store credentials securely (only if new token and different)
        if use_token and use_token != existing_token:
            cred_manager.store_token(use_token)
            console.print("🔒 Credentials stored securely")

        # Save GitHub repository configuration
        config_file = core.roadmap_dir / "config.yaml"

        if config_file.exists():
            with open(config_file) as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}

        # Enhanced GitHub configuration
        config["github"] = {
            "repository": github_repo,
            "enabled": True,
            "sync_enabled": True,
            "webhook_secret": None,  # Can be set up later
            "sync_settings": {
                "bidirectional": True,
                "auto_close": True,
                "sync_labels": True,
                "sync_milestones": True,
            },
        }

        # Save configuration
        with open(config_file, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        console.print("⚙️  Configuration saved")

        # Test a basic API call to ensure everything works
        try:
            issues_response = github_client._make_request(
                "GET",
                f"/repos/{github_repo}/issues",
                params={"state": "open", "per_page": 1},
            )
            issues = issues_response.json()
            console.print(f"✅ API test successful ({len(issues)} issue(s) found)")
        except Exception as e:
            console.print(f"⚠️  API test warning: {e}", style="yellow")

        return True

    except ImportError as e:
        console.print(
            f"⚠️  GitHub integration not available: Missing dependencies ({e})",
            style="yellow",
        )
        console.print("Install with: pip install requests keyring", style="dim")
        return False
    except Exception as e:
        console.print(f"❌ GitHub setup failed: {e}", style="red")
        if interactive and click.confirm("Continue without GitHub integration?"):
            return False
        else:
            raise


def _show_success_summary(
    name: str, github_configured: bool, project_info: dict | None, detected_info: dict
) -> None:
    """Show success summary and next steps."""

    console.print()
    console.print("✅ Setup Complete!", style="bold green")
    console.print()

    # Show what was created
    console.print("📁 Created:", style="bold cyan")
    console.print(f"  ✓ Roadmap structure: {name}/")
    console.print("    ├── issues/       (issue tracking)")
    console.print("    ├── milestones/   (milestone management)")
    console.print("    ├── projects/     (project documents)")
    console.print("    ├── templates/    (document templates)")
    console.print("    ├── artifacts/    (generated content)")
    console.print("    └── config.yaml   (configuration)")

    if project_info:
        console.print(
            f"  ✓ Main project: {project_info['name']} (ID: {project_info['id']})"
        )
    if github_configured:
        console.print("  ✓ GitHub integration: Connected and configured")
        console.print("    • Bidirectional sync enabled")
        console.print("    • Automatic issue linking")
        console.print("    • Webhook support ready")
    console.print("  ✓ Security: Secure file permissions and credential storage")

    console.print()
    console.print("🚀 Next Steps:", style="bold yellow")

    if project_info:
        console.print(f"  → roadmap project show {project_info['id'][:8]}")
    console.print('  → roadmap issue create "Your first issue"')
    if github_configured:
        console.print("  → roadmap sync bidirectional        # Sync with GitHub")
        console.print("  → roadmap git setup                 # Configure git hooks")
    console.print("  → roadmap user show-dashboard        # View your dashboard")

    console.print()
    console.print("📚 Learn More:", style="bold cyan")
    console.print("  → roadmap --help                    # All available commands")
    console.print("  → roadmap issue --help               # Issue management")
    if github_configured:
        console.print("  → roadmap sync --help                # GitHub synchronization")
        console.print("  → roadmap git --help                 # Git integration")
    console.print("  → roadmap project --help             # Project management")
    console.print("  → roadmap milestone --help           # Milestone tracking")

    console.print()
    console.print("💡 Pro Tips:", style="bold magenta")
    console.print("  • Use 'roadmap user show-dashboard' for daily task overview")

    if detected_info.get("has_git"):
        console.print(
            "  • Set up git hooks with 'roadmap git setup' for automatic updates"
        )
        if github_configured:
            console.print(
                "  • Try 'roadmap sync bidirectional' to sync existing GitHub issues"
            )
    else:
        console.print("  • Initialize git with 'git init' to enable advanced features:")
        console.print("    - Automatic issue updates from commit messages")
        console.print("    - Git hooks for seamless integration")
        console.print("    - GitHub synchronization capabilities")

    console.print(
        "  • Create templates in .roadmap/templates/ for consistent formatting"
    )


def _post_init_validate(
    core: RoadmapCore, name: str, project_info: dict | None
) -> bool:
    """Validate the init result: config exists, project file created, and permissions look sane.

    Returns True if validation passes, False if there are warnings or errors.
    """
    ok = True
    roadmap_dir = core.roadmap_dir

    # Check config file
    config_file = roadmap_dir / "config.yaml"
    if not config_file.exists():
        console.print(f"⚠️  Missing configuration file: {config_file}", style="yellow")
        ok = False

    # Check projects directory and at least one project file
    projects_dir = roadmap_dir / "projects"
    try:
        has_projects = projects_dir.exists() and any(projects_dir.iterdir())
    except Exception:
        has_projects = False

    if not has_projects:
        console.print(f"⚠️  No project files found in {projects_dir}", style="yellow")
        ok = False

    # Basic permission checks: readable and writable
    try:
        if not os.access(roadmap_dir, os.R_OK | os.W_OK | os.X_OK):
            console.print(
                f"⚠️  Permission issue: cannot read/write/execute {roadmap_dir}",
                style="yellow",
            )
            ok = False
    except Exception:
        # Non-fatal
        pass

    # If a project_info was returned, ensure file exists
    if project_info and "filename" in project_info:
        proj_file = roadmap_dir / "projects" / project_info["filename"]
        if not proj_file.exists():
            console.print(
                f"⚠️  Expected project file missing: {proj_file}", style="yellow"
            )
            ok = False

    return ok
