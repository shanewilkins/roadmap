"""Tests for project view command."""

import pytest

from roadmap.adapters.cli.projects.view import (
    _extract_description_and_objectives,
)
from tests.unit.common.formatters.test_ansi_utilities import clean_cli_output


class TestExtractDescriptionAndObjectives:
    """Test description and objectives extraction from project content."""

    def test_extract_from_empty_content(self):
        """Test extracting from empty content."""
        description, objectives = _extract_description_and_objectives(None)
        assert description is None
        assert objectives is None

    def test_extract_from_empty_string(self):
        """Test extracting from empty string."""
        description, objectives = _extract_description_and_objectives("")
        assert description is None
        assert objectives is None

    def test_extract_description_only(self):
        """Test extracting description when no objectives section."""
        content = "This is a description\nWith multiple lines\nNo objectives here"
        description, objectives = _extract_description_and_objectives(content)
        assert description is not None
        assert "This is a description" in description
        assert "With multiple lines" in description
        assert objectives is None

    def test_extract_objectives_only(self):
        """Test extracting objectives section."""
        content = "## Objectives\n- Goal 1\n- Goal 2\n- Goal 3"
        description, objectives = _extract_description_and_objectives(content)
        assert objectives is not None
        assert "- Goal 1" in objectives
        assert "- Goal 2" in objectives
        assert "- Goal 3" in objectives

    def test_extract_both_description_and_objectives(self):
        """Test extracting both description and objectives."""
        content = """Project description line 1
Project description line 2

## Objectives
- Objective 1
- Objective 2
- Objective 3"""
        description, objectives = _extract_description_and_objectives(content)
        assert description is not None
        assert "Project description" in description
        assert objectives is not None
        assert "Objective" in objectives

    def test_extract_with_lowercase_objectives_header(self):
        """Test extraction with lowercase objectives header."""
        content = """Description text

## objectives
- Goal 1
- Goal 2"""
        description, objectives = _extract_description_and_objectives(content)
        assert description is not None
        assert objectives is not None
        assert "Goal 1" in objectives

    def test_extract_with_mixed_case_objectives_header(self):
        """Test extraction with mixed case objectives header."""
        content = """Description

## OBJECTIVES
- Target 1"""
        description, objectives = _extract_description_and_objectives(content)
        assert description is not None
        assert objectives is not None

    def test_extract_stops_at_next_header(self):
        """Test that objectives section stops at next ## header."""
        content = """Description

## Objectives
- Goal 1
- Goal 2

## Next Section
Other content"""
        description, objectives = _extract_description_and_objectives(content)
        assert objectives is not None
        assert "Goal 1" in objectives
        assert "Goal 2" in objectives
        # Next section should not be in objectives
        assert "Next Section" not in objectives

    def test_extract_multiple_headers(self):
        """Test extraction with multiple headers."""
        content = """# Title

Description content

## Objectives
- Objective 1

## Other Section
Other content"""
        description, objectives = _extract_description_and_objectives(content)
        assert description is not None
        assert objectives is not None

    def test_extract_objectives_with_nested_bullets(self):
        """Test objectives with nested bullet points."""
        content = """## Objectives
- Main goal 1
  - Sub goal 1a
  - Sub goal 1b
- Main goal 2"""
        description, objectives = _extract_description_and_objectives(content)
        assert objectives is not None
        assert "Main goal 1" in objectives
        assert "Sub goal 1a" in objectives

    def test_extract_whitespace_only_returns_none(self):
        """Test that whitespace-only content returns None."""
        description, objectives = _extract_description_and_objectives("   \n  \n   ")
        assert description is None
        assert objectives is None

    def test_extract_description_with_code_blocks(self):
        """Test extraction with code blocks in description."""
        content = """This is a description

```python
def hello():
    pass
```

More description"""
        description, objectives = _extract_description_and_objectives(content)
        assert description is not None
        assert "This is a description" in description

    def test_extract_objectives_with_code_blocks(self):
        """Test extraction with code blocks in objectives."""
        content = """## Objectives
- Implement feature X
  ```
  code here
  ```
- Test feature Y"""
        description, objectives = _extract_description_and_objectives(content)
        assert objectives is not None
        assert "Implement feature" in objectives

    @pytest.mark.parametrize(
        "delimiter", ["## Objectives", "## objectives", "## OBJECTIVES"]
    )
    def test_extract_various_header_formats(self, delimiter):
        """Test extraction with various header formats."""
        content = f"Description\n\n{delimiter}\n- Goal"
        description, objectives = _extract_description_and_objectives(content)
        assert description is not None
        assert objectives is not None

    def test_extract_long_description(self):
        """Test extraction with very long description."""
        long_text = "\n".join([f"Line {i}" for i in range(100)])
        content = f"{long_text}\n\n## Objectives\n- Goal"
        description, objectives = _extract_description_and_objectives(content)
        assert description is not None
        assert len(description) > 100
        assert objectives is not None

    def test_extract_special_characters_in_content(self):
        """Test extraction with special characters."""
        content = """Description with special chars: @#$%^&*()

## Objectives
- Goal with emoji 🎯
- Target [important]"""
        description, objectives = _extract_description_and_objectives(content)
        assert description is not None
        assert objectives is not None

    def test_extract_objectives_immediately_after_header(self):
        """Test objectives that start immediately after header."""
        content = """Description text

## Objectives
- First goal without blank line
- Second goal"""
        description, objectives = _extract_description_and_objectives(content)
        assert objectives is not None
        assert "First goal" in objectives

    def test_extract_only_objectives_header_no_content(self):
        """Test when objectives header exists but has no content."""
        content = """Description

## Objectives
"""
        description, objectives = _extract_description_and_objectives(content)
        assert description is not None
        # Empty objectives should return None
        assert objectives is None or objectives.strip() == ""

    def test_extract_description_with_list_items(self):
        """Test description containing list items before objectives."""
        content = """Features:
- Feature 1
- Feature 2

## Objectives
- Objective 1"""
        description, objectives = _extract_description_and_objectives(content)
        assert description is not None
        assert "Feature 1" in description
        assert "Feature 2" in description
        assert objectives is not None

    def test_extract_preserves_newlines_in_description(self):
        """Test that newlines are preserved in extracted description."""
        content = """Line 1
Line 2
Line 3

## Objectives
- Goal"""
        description, objectives = _extract_description_and_objectives(content)
        assert description is not None
        assert "Line 1" in description
        assert "Line 2" in description
        assert "Line 3" in description

    def test_extract_preserves_newlines_in_objectives(self):
        """Test that newlines are preserved in extracted objectives."""
        content = """## Objectives
- Goal 1
- Goal 2
- Goal 3"""
        description, objectives = _extract_description_and_objectives(content)
        assert objectives is not None
        assert "Goal 1" in objectives
        assert "Goal 2" in objectives
        assert "Goal 3" in objectives

    def test_extract_with_inline_markdown_formatting(self):
        """Test extraction with inline markdown formatting."""
        content = """This is **bold** and *italic* text

## Objectives
- Goal with `code` formatting
- Another **bold** goal"""
        description, objectives = _extract_description_and_objectives(content)
        assert description is not None
        assert "bold" in description
        assert objectives is not None


class TestViewProjectCommand:
    """Test view_project CLI command."""

    def test_view_project_help(self, cli_runner):
        """Test view project command help."""
        from roadmap.adapters.cli import main

        result = cli_runner.invoke(main, ["project", "view", "--help"])
        assert result.exit_code == 0

    def test_view_project_not_initialized(self, cli_runner):
        """Test view project command when roadmap not initialized."""
        from roadmap.adapters.cli import main

        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["project", "view", "test-project"])
            assert result.exit_code != 0

    def test_view_nonexistent_project(self, cli_runner):
        """Test viewing a project that doesn't exist."""
        from roadmap.adapters.cli import main

        with cli_runner.isolated_filesystem():
            cli_runner.invoke(main, ["init", "-y", "--skip-github", "--skip-project"])
            result = cli_runner.invoke(main, ["project", "view", "nonexistent"])
            assert result.exit_code != 0
            assert "not found" in clean_cli_output(result.output).lower()

    def test_view_created_project(self, cli_runner):
        """Test viewing a successfully created project."""
        from roadmap.adapters.cli import main

        with cli_runner.isolated_filesystem():
            init_result = cli_runner.invoke(
                main, ["init", "-y", "--skip-github", "--skip-project"]
            )
            assert init_result.exit_code == 0

            # Create a project
            create_result = cli_runner.invoke(
                main, ["project", "create", "--title", "test-project"]
            )
            assert create_result.exit_code == 0

            # View the project
            view_result = cli_runner.invoke(main, ["project", "view", "test-project"])
            assert view_result.exit_code == 0
            assert "test-project" in clean_cli_output(view_result.output)
