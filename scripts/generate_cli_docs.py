#!/usr/bin/env python3
"""
Automated CLI Reference Generator

This script generates comprehensive CLI documentation by extracting help information
from Click commands and creating formatted markdown documentation.
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import click
from click.testing import CliRunner

# Add the roadmap module to the path
sys.path.insert(0, str(Path(__file__).parent.parent))


class CLIDocGenerator:
    """Generate comprehensive CLI documentation from Click commands."""

    def __init__(self, cli_app, output_dir: Path):
        self.cli_app = cli_app
        self.output_dir = Path(output_dir)
        self.runner = CliRunner()
        self.commands_data = {}

    def extract_command_info(self, command_path: list[str] = None) -> dict[str, Any]:
        """Extract information from a Click command."""
        if command_path is None:
            command_path = []

        # Get help for the command
        help_result = self.runner.invoke(self.cli_app, command_path + ["--help"])

        if help_result.exit_code != 0:
            return {}

        help_text = help_result.output

        # Parse the help output
        lines = help_text.split("\n")

        info = {
            "path": " ".join(command_path) if command_path else "roadmap",
            "usage": "",
            "description": "",
            "options": [],
            "commands": [],
            "examples": [],
        }

        current_section = None
        current_option = {}

        for line in lines:
            line = line.rstrip()

            if line.startswith("Usage:"):
                info["usage"] = line.replace("Usage: ", "").strip()
            elif line.strip() and not line.startswith(" ") and ":" in line:
                # Section header
                current_section = line.split(":")[0].lower()
                if line.strip().endswith(":") and not line.startswith(" "):
                    desc_start = lines.index(line) + 1
                    # Get description from next non-empty line
                    for i in range(desc_start, len(lines)):
                        if lines[i].strip() and not lines[i].startswith(" "):
                            break
                        if lines[i].strip():
                            info["description"] = lines[i].strip()
                            break
            elif current_section == "options" and line.startswith("  "):
                # Parse option
                if line.strip().startswith("-"):
                    # Save previous option
                    if current_option:
                        info["options"].append(current_option)

                    # Parse new option
                    option_match = re.match(r"^\s+(.*?)\s{2,}(.*)$", line)
                    if option_match:
                        current_option = {
                            "flags": option_match.group(1).strip(),
                            "description": option_match.group(2).strip(),
                        }
                elif current_option and line.strip():
                    # Continue description
                    current_option["description"] += " " + line.strip()
            elif current_section == "commands" and line.startswith("  "):
                # Parse subcommand
                cmd_match = re.match(r"^\s+(\S+)\s{2,}(.*)$", line)
                if cmd_match:
                    info["commands"].append(
                        {
                            "name": cmd_match.group(1),
                            "description": cmd_match.group(2).strip(),
                        }
                    )

        # Add last option
        if current_option:
            info["options"].append(current_option)

        return info

    def discover_commands(self, command_path: list[str] = None) -> list[list[str]]:
        """Discover all available commands recursively."""
        if command_path is None:
            command_path = []

        commands = [command_path.copy()]

        # Get command info
        info = self.extract_command_info(command_path)

        # Recurse into subcommands
        for cmd in info.get("commands", []):
            subcommand_path = command_path + [cmd["name"]]
            commands.extend(self.discover_commands(subcommand_path))

        return commands

    def generate_command_examples(self, command_path: list[str]) -> list[str]:
        """Generate realistic examples for a command based on its options."""
        examples = []
        cmd_str = "roadmap " + " ".join(command_path) if command_path else "roadmap"

        # Common example patterns
        if not command_path:  # Main command
            examples = ["roadmap --help", "roadmap --version", "roadmap status"]
        elif command_path == ["init"]:
            examples = [
                "roadmap init",
                "roadmap init --name my-project",
                "roadmap init -n project-roadmap",
            ]
        elif command_path == ["issue", "create"]:
            examples = [
                "roadmap issue create 'Fix authentication bug'",
                "roadmap issue create 'Add user dashboard' --priority high --type feature",
                "roadmap issue create 'Database optimization' -p critical -m 'v1.0' -a john",
            ]
        elif command_path == ["export", "issues"]:
            examples = [
                "roadmap export issues --format csv",
                "roadmap export issues --format excel --milestone 'v1.0'",
                "roadmap export issues --format json --status done --priority critical",
            ]
        elif command_path == ["analytics"]:
            examples = [
                "roadmap analytics",
                "roadmap analytics --export --format excel",
                "roadmap analytics --period month --export",
            ]
        else:
            # Generic examples
            examples = [f"{cmd_str} --help"]

        return examples

    def generate_markdown_doc(self) -> str:
        """Generate complete markdown documentation."""
        # Discover all commands
        all_commands = self.discover_commands()

        # Extract info for all commands
        for cmd_path in all_commands:
            key = " ".join(cmd_path) if cmd_path else "main"
            self.commands_data[key] = self.extract_command_info(cmd_path)
            self.commands_data[key]["examples"] = self.generate_command_examples(
                cmd_path
            )

        # Generate markdown
        md_content = self._generate_markdown_content()

        return md_content

    def _generate_markdown_content(self) -> str:
        """Generate the actual markdown content."""
        content = []

        # Header
        content.append("# Roadmap CLI Reference")
        content.append("")
        content.append(
            f"*Auto-generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        )
        content.append("")
        content.append(
            "Complete reference for all Roadmap CLI commands with examples, options, and usage patterns."
        )
        content.append("")

        # Table of contents
        content.append("## 📋 Table of Contents")
        content.append("")

        # Generate TOC
        toc_entries = []
        for key in sorted(self.commands_data.keys()):
            if key == "main":
                toc_entries.append("- [Main Command](#main-command)")
            else:
                anchor = key.replace(" ", "-").lower()
                toc_entries.append(f"- [`{key}`](#{anchor})")

        content.extend(toc_entries)
        content.append("")

        # Main command first
        if "main" in self.commands_data:
            content.extend(
                self._format_command_section("main", self.commands_data["main"])
            )

        # Other commands
        for key in sorted(self.commands_data.keys()):
            if key != "main":
                content.extend(
                    self._format_command_section(key, self.commands_data[key])
                )

        return "\n".join(content)

    def _format_command_section(self, key: str, info: dict[str, Any]) -> list[str]:
        """Format a single command section."""
        content = []

        # Command header
        if key == "main":
            content.append("## Main Command")
        else:
            content.append(f"## `{key}`")

        content.append("")

        # Description
        if info.get("description"):
            content.append(info["description"])
            content.append("")

        # Usage
        if info.get("usage"):
            content.append("**Usage:**")
            content.append("```bash")
            content.append(info["usage"])
            content.append("```")
            content.append("")

        # Options
        if info.get("options"):
            content.append("**Options:**")
            content.append("")
            for option in info["options"]:
                content.append(f"- `{option['flags']}` - {option['description']}")
            content.append("")

        # Subcommands
        if info.get("commands"):
            content.append("**Available Commands:**")
            content.append("")
            for cmd in info["commands"]:
                content.append(f"- `{cmd['name']}` - {cmd['description']}")
            content.append("")

        # Examples
        if info.get("examples"):
            content.append("**Examples:**")
            content.append("")
            for example in info["examples"]:
                content.append("```bash")
                content.append(example)
                content.append("```")
                content.append("")

        content.append("---")
        content.append("")

        return content

    def save_documentation(self, filename: str = "CLI_REFERENCE_AUTO.md"):
        """Save the generated documentation to a file."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        markdown_content = self.generate_markdown_doc()

        output_file = self.output_dir / filename
        output_file.write_text(markdown_content)

        return output_file


def main():
    """Generate CLI documentation."""
    # Determine paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    docs_dir = project_root / "docs"

    print("🔄 Generating automated CLI documentation...")

    # Import the CLI app properly
    from roadmap.cli import main as cli_main

    # Generate CLI reference
    generator = CLIDocGenerator(cli_main, docs_dir)
    output_file = generator.save_documentation()

    print(f"✅ Generated CLI reference: {output_file}")

    # Show summary
    print("\n📊 Documentation Summary:")
    print(f"   • Commands documented: {len(generator.commands_data)}")
    print(f"   • Output file: {output_file.name}")
    print(f"   • Size: {output_file.stat().st_size} bytes")


if __name__ == "__main__":
    main()
