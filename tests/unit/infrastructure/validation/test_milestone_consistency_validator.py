"""Tests for milestone consistency validator."""

from unittest.mock import MagicMock, patch

import pytest

from roadmap.infrastructure.validation.milestone_consistency_validator import (
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
            "roadmap.infrastructure.validation_gateway.ValidationGateway.parse_milestone_for_validation"
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
            "roadmap.infrastructure.validation_gateway.ValidationGateway.parse_milestone_for_validation"
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
            "roadmap.infrastructure.validation_gateway.ValidationGateway.parse_milestone_for_validation"
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
            "roadmap.infrastructure.validation_gateway.ValidationGateway.parse_milestone_for_validation"
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
            "roadmap.infrastructure.validation_gateway.ValidationGateway.parse_milestone_for_validation"
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
            "roadmap.infrastructure.validation_gateway.ValidationGateway.parse_milestone_for_validation"
        ) as mock_parse:
            mock_parse.side_effect = Exception("Unexpected error")

            # Create file
            milestone_file = validator.milestones_dir / "test.md"
            milestone_file.write_text("content")

            inconsistencies = validator.validate()
            assert len(inconsistencies) == 1
            assert inconsistencies[0]["type"] == "parse_error"
            assert "Unexpected error" in inconsistencies[0]["error"]

    def test_validate_inconsistent_single_milestone(self, validator):
        """Test validation detects single inconsistent milestone."""
        with patch(
            "roadmap.infrastructure.validation_gateway.ValidationGateway.parse_milestone_for_validation"
        ) as mock_parse:
            mock_milestone = MagicMock()
            mock_milestone.filename = "Q1-2024.md"
            mock_milestone.name = "Q1 2024"
            mock_parse.return_value = mock_milestone

            # Create file with wrong name
            milestone_file = validator.milestones_dir / "wrong-name.md"
            milestone_file.write_text("# Q1 2024")

            inconsistencies = validator.validate()
            assert len(inconsistencies) == 1
            assert inconsistencies[0]["type"] == "filename_mismatch"
            assert inconsistencies[0]["file"] == "wrong-name.md"
            assert inconsistencies[0]["expected_filename"] == "Q1-2024.md"
            assert inconsistencies[0]["name"] == "Q1 2024"

    def test_validate_multiple_inconsistent_milestones(self, validator):
        """Test validation detects multiple inconsistent milestones."""
        with patch(
            "roadmap.infrastructure.validation_gateway.ValidationGateway.parse_milestone_for_validation"
        ) as mock_parse:
            mock1 = MagicMock()
            mock1.filename = "Q1-2024.md"
            mock1.name = "Q1 2024"

            mock2 = MagicMock()
            mock2.filename = "Q2-2024.md"
            mock2.name = "Q2 2024"

            mock_parse.side_effect = [mock1, mock2]

            file1 = validator.milestones_dir / "bad1.md"
            file1.write_text("# Q1 2024")
            file2 = validator.milestones_dir / "bad2.md"
            file2.write_text("# Q2 2024")

            inconsistencies = validator.validate()
            assert len(inconsistencies) == 2

    def test_validate_mixed_consistent_and_inconsistent(self, validator):
        """Test validation with mix of consistent and inconsistent files."""
        with patch(
            "roadmap.infrastructure.validation_gateway.ValidationGateway.parse_milestone_for_validation"
        ) as mock_parse:
            mock1 = MagicMock()
            mock1.filename = "Q1-2024.md"
            mock1.name = "Q1 2024"

            mock2 = MagicMock()
            mock2.filename = "Q2-2024.md"
            mock2.name = "Q2 2024"

            mock_parse.side_effect = [mock1, mock2]

            # Consistent file (alphabetically first: bad.md comes before Q1)
            file1 = validator.milestones_dir / "Q1-2024.md"
            file1.write_text("# Q1 2024")
            # Inconsistent file
            file2 = validator.milestones_dir / "wrong.md"
            file2.write_text("# Q2 2024")

            inconsistencies = validator.validate()
            assert len(inconsistencies) == 1
            assert inconsistencies[0]["file"] == "wrong.md"

    def test_fix_empty_directory(self, validator):
        """Test fix on empty directory returns empty results."""
        results = validator.fix()
        assert results["renamed"] == []
        assert results["errors"] == []

    def test_fix_consistent_files_unchanged(self, validator):
        """Test fix doesn't modify consistent files."""
        with patch(
            "roadmap.infrastructure.validation_gateway.ValidationGateway.parse_milestone_for_validation"
        ) as mock_parse:
            mock_milestone = MagicMock()
            mock_milestone.filename = "Q1-2024.md"
            mock_milestone.name = "Q1 2024"
            mock_parse.return_value = mock_milestone

            milestone_file = validator.milestones_dir / "Q1-2024.md"
            milestone_file.write_text("# Q1 2024")

            results = validator.fix()
            assert results["renamed"] == []
            assert results["errors"] == []
            # File should still exist
            assert milestone_file.exists()

    def test_fix_single_inconsistent_file(self, validator):
        """Test fix renames single inconsistent file."""
        with patch(
            "roadmap.infrastructure.validation_gateway.ValidationGateway.parse_milestone_for_validation"
        ) as mock_parse:
            mock_milestone = MagicMock()
            mock_milestone.filename = "Q1-2024.md"
            mock_milestone.name = "Q1 2024"
            mock_parse.return_value = mock_milestone

            old_file = validator.milestones_dir / "wrong.md"
            old_file.write_text("# Q1 2024")

            results = validator.fix()
            assert len(results["renamed"]) == 1
            assert "wrong.md" in results["renamed"][0]
            assert "Q1-2024.md" in results["renamed"][0]
            assert results["errors"] == []

            # Old file should not exist, new should
            assert not old_file.exists()
            assert (validator.milestones_dir / "Q1-2024.md").exists()

    def test_fix_target_file_exists_error(self, validator):
        """Test fix handles case when target file already exists."""
        with patch(
            "roadmap.infrastructure.validation_gateway.ValidationGateway.parse_milestone_for_validation"
        ) as mock_parse:
            mock_milestone = MagicMock()
            mock_milestone.filename = "Q1-2024.md"
            mock_milestone.name = "Q1 2024"
            mock_parse.return_value = mock_milestone

            old_file = validator.milestones_dir / "wrong.md"
            old_file.write_text("wrong content")
            existing_file = validator.milestones_dir / "Q1-2024.md"
            existing_file.write_text("existing content")

            results = validator.fix()
            assert results["renamed"] == []
            assert len(results["errors"]) == 1
            assert "target exists" in results["errors"][0]

            # Both files should still exist
            assert old_file.exists()
            assert existing_file.exists()

    def test_fix_multiple_files(self, validator):
        """Test fix handles multiple files."""
        with patch(
            "roadmap.infrastructure.validation_gateway.ValidationGateway.parse_milestone_for_validation"
        ) as mock_parse:
            mock1 = MagicMock()
            mock1.filename = "Q1-2024.md"
            mock1.name = "Q1 2024"

            mock2 = MagicMock()
            mock2.filename = "Q2-2024.md"
            mock2.name = "Q2 2024"

            mock_parse.side_effect = [mock1, mock2]

            file1 = validator.milestones_dir / "bad1.md"
            file1.write_text("# Q1 2024")
            file2 = validator.milestones_dir / "bad2.md"
            file2.write_text("# Q2 2024")

            results = validator.fix()
            assert len(results["renamed"]) == 2
            assert results["errors"] == []

            # Check files were renamed
            assert (validator.milestones_dir / "Q1-2024.md").exists()
            assert (validator.milestones_dir / "Q2-2024.md").exists()
            assert not file1.exists()
            assert not file2.exists()

    def test_fix_parse_error_skipped(self, validator):
        """Test fix skips files with parse errors."""
        with patch(
            "roadmap.infrastructure.validation_gateway.ValidationGateway.parse_milestone_for_validation"
        ) as mock_parse:
            mock_parse.side_effect = Exception("Parse failed")

            milestone_file = validator.milestones_dir / "bad.md"
            milestone_file.write_text("invalid")

            results = validator.fix()
            assert results["renamed"] == []
            assert len(results["errors"]) == 1
            assert "parse_error" in results["errors"][0]

    def test_fix_permission_error(self, validator):
        """Test fix handles permission errors during rename."""
        with patch(
            "roadmap.infrastructure.validation_gateway.ValidationGateway.parse_milestone_for_validation"
        ) as mock_parse:
            mock_milestone = MagicMock()
            mock_milestone.filename = "Q1-2024.md"
            mock_milestone.name = "Q1 2024"
            mock_parse.return_value = mock_milestone

            file = validator.milestones_dir / "wrong.md"
            file.write_text("content")

            # Mock Path.rename to raise OSError
            with patch("pathlib.Path.rename", side_effect=OSError("Permission denied")):
                results = validator.fix()

            assert results["renamed"] == []
            assert len(results["errors"]) == 1
            assert "Failed to rename" in results["errors"][0]

    def test_validate_with_all_fields_in_error(self, validator):
        """Test validation error includes all required fields."""
        with patch(
            "roadmap.infrastructure.validation_gateway.ValidationGateway.parse_milestone_for_validation"
        ) as mock_parse:
            mock_parse.side_effect = Exception("test error")

            file = validator.milestones_dir / "test.md"
            file.write_text("content")

            inconsistencies = validator.validate()
            error = inconsistencies[0]

            assert "file" in error
            assert "name" in error
            assert "expected_filename" in error
            assert "type" in error
            assert "error" in error
            assert error["name"] == "PARSE_ERROR"
            assert error["expected_filename"] == "N/A"

    def test_fix_returns_correct_structure(self, validator):
        """Test fix always returns dict with renamed and errors keys."""
        results = validator.fix()
        assert isinstance(results, dict)
        assert "renamed" in results
        assert "errors" in results
        assert isinstance(results["renamed"], list)
        assert isinstance(results["errors"], list)

    def test_validate_preserves_file_details(self, validator):
        """Test validate includes proper file details in results."""
        with patch(
            "roadmap.infrastructure.validation_gateway.ValidationGateway.parse_milestone_for_validation"
        ) as mock_parse:
            mock_milestone = MagicMock()
            mock_milestone.filename = "expected.md"
            mock_milestone.name = "Milestone Name"
            mock_parse.return_value = mock_milestone

            file = validator.milestones_dir / "actual.md"
            file.write_text("# Milestone Name")

            inconsistencies = validator.validate()
            result = inconsistencies[0]

            assert result["file"] == "actual.md"
            assert result["name"] == "Milestone Name"
            assert result["expected_filename"] == "expected.md"
            assert result["type"] == "filename_mismatch"

    def test_fix_preserves_file_content_on_rename(self, validator):
        """Test fix preserves file content when renaming."""
        with patch(
            "roadmap.infrastructure.validation_gateway.ValidationGateway.parse_milestone_for_validation"
        ) as mock_parse:
            mock_milestone = MagicMock()
            mock_milestone.filename = "Q1-2024.md"
            mock_milestone.name = "Q1 2024"
            mock_parse.return_value = mock_milestone

            original_content = "# Q1 2024\nSome milestone content"
            file = validator.milestones_dir / "wrong.md"
            file.write_text(original_content)

            validator.fix()

            renamed_file = validator.milestones_dir / "Q1-2024.md"
            assert renamed_file.read_text() == original_content
