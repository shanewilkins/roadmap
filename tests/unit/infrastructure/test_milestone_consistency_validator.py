"""Tests for milestone consistency validator."""

from unittest.mock import MagicMock, patch

import pytest

from roadmap.infrastructure.milestone_consistency_validator import (
    MilestoneConsistencyValidator,
)


class TestMilestoneConsistencyValidator:
    """Test MilestoneConsistencyValidator."""

    @pytest.fixture
    def validator(self, tmp_path):
        """Create validator with temporary directory."""
        milestones_dir = tmp_path / "milestones"
        milestones_dir.mkdir()
        return MilestoneConsistencyValidator(milestones_dir)

    def test_init(self, tmp_path):
        """Test initialization."""
        milestones_dir = tmp_path / "milestones"
        milestones_dir.mkdir()
        validator = MilestoneConsistencyValidator(milestones_dir)
        assert validator.milestones_dir == milestones_dir

    def test_validate_empty_directory(self, validator):
        """Test validation on empty directory."""
        inconsistencies = validator.validate()
        assert inconsistencies == []

    def test_validate_no_markdown_files(self, validator):
        """Test validation when directory has no markdown files."""
        # Create some non-markdown files
        (validator.milestones_dir / "file.txt").write_text("content")
        (validator.milestones_dir / "file.json").write_text("{}")
        inconsistencies = validator.validate()
        assert inconsistencies == []

    def test_validate_consistent_milestone(self, validator):
        """Test validation with consistent milestone."""
        with patch(
            "roadmap.infrastructure.milestone_consistency_validator.MilestoneParser.parse_milestone_file"
        ) as mock_parse:
            mock_milestone = MagicMock()
            mock_milestone.filename = "Q1-2024.md"
            mock_milestone.name = "Q1 2024"
            mock_parse.return_value = mock_milestone

            # Create file
            milestone_file = validator.milestones_dir / "Q1-2024.md"
            milestone_file.write_text("# Milestone")

            inconsistencies = validator.validate()
            assert inconsistencies == []

    def test_validate_inconsistent_filename(self, validator):
        """Test validation with mismatched filename."""
        with patch(
            "roadmap.infrastructure.milestone_consistency_validator.MilestoneParser.parse_milestone_file"
        ) as mock_parse:
            mock_milestone = MagicMock()
            mock_milestone.filename = "Q1-2024.md"  # Expected
            mock_milestone.name = "Q1 2024"
            mock_parse.return_value = mock_milestone

            # Create file with different name
            milestone_file = validator.milestones_dir / "q1-2024.md"
            milestone_file.write_text("# Milestone")

            inconsistencies = validator.validate()
            assert len(inconsistencies) == 1
            assert inconsistencies[0]["type"] == "filename_mismatch"
            assert inconsistencies[0]["file"] == "q1-2024.md"
            assert inconsistencies[0]["expected_filename"] == "Q1-2024.md"
            assert inconsistencies[0]["name"] == "Q1 2024"

    def test_validate_parse_error(self, validator):
        """Test validation when parsing fails."""
        with patch(
            "roadmap.infrastructure.milestone_consistency_validator.MilestoneParser.parse_milestone_file"
        ) as mock_parse:
            mock_parse.side_effect = ValueError("Invalid format")

            # Create file
            milestone_file = validator.milestones_dir / "invalid.md"
            milestone_file.write_text("Invalid content")

            inconsistencies = validator.validate()
            assert len(inconsistencies) == 1
            assert inconsistencies[0]["type"] == "parse_error"
            assert inconsistencies[0]["file"] == "invalid.md"
            assert inconsistencies[0]["name"] == "PARSE_ERROR"
            assert "Invalid format" in inconsistencies[0]["error"]

    def test_validate_multiple_files_mixed(self, validator):
        """Test validation with multiple files, some consistent and some not."""
        with patch(
            "roadmap.infrastructure.milestone_consistency_validator.MilestoneParser.parse_milestone_file"
        ) as mock_parse:

            def parse_side_effect(file_path):
                if file_path.name == "Q1-2024.md":
                    m = MagicMock()
                    m.filename = "Q1-2024.md"
                    m.name = "Q1 2024"
                    return m
                elif file_path.name == "q2-2024.md":
                    m = MagicMock()
                    m.filename = "Q2-2024.md"  # Mismatch
                    m.name = "Q2 2024"
                    return m
                else:
                    raise ValueError("Parse error")

            mock_parse.side_effect = parse_side_effect

            # Create files
            (validator.milestones_dir / "Q1-2024.md").write_text("# Q1")
            (validator.milestones_dir / "q2-2024.md").write_text("# Q2")
            (validator.milestones_dir / "invalid.md").write_text("# Invalid")

            inconsistencies = validator.validate()
            assert len(inconsistencies) == 2

            # Check for filename mismatch
            mismatch = [i for i in inconsistencies if i["type"] == "filename_mismatch"]
            assert len(mismatch) == 1
            assert mismatch[0]["file"] == "q2-2024.md"

            # Check for parse error
            errors = [i for i in inconsistencies if i["type"] == "parse_error"]
            assert len(errors) == 1
            assert errors[0]["file"] == "invalid.md"

    def test_validate_nested_directories(self, validator):
        """Test validation with nested directory structure."""
        with patch(
            "roadmap.infrastructure.milestone_consistency_validator.MilestoneParser.parse_milestone_file"
        ) as mock_parse:
            mock_milestone = MagicMock()
            mock_milestone.filename = "2024.md"
            mock_milestone.name = "Year 2024"
            mock_parse.return_value = mock_milestone

            # Create nested structure
            nested = validator.milestones_dir / "year" / "quarters"
            nested.mkdir(parents=True)
            nested_file = nested / "2024.md"
            nested_file.write_text("# 2024")

            inconsistencies = validator.validate()
            assert inconsistencies == []

    def test_validate_handles_exception_gracefully(self, validator):
        """Test that unexpected exceptions are handled."""
        with patch(
            "roadmap.infrastructure.milestone_consistency_validator.MilestoneParser.parse_milestone_file"
        ) as mock_parse:
            mock_parse.side_effect = Exception("Unexpected error")

            # Create file
            milestone_file = validator.milestones_dir / "test.md"
            milestone_file.write_text("content")

            inconsistencies = validator.validate()
            assert len(inconsistencies) == 1
            assert inconsistencies[0]["type"] == "parse_error"
            assert "Unexpected error" in inconsistencies[0]["error"]
