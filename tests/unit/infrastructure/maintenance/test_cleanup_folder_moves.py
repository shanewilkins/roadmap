"""Comprehensive unit tests for cleanup command module.

Tests cover cleanup logic including backup deletion, folder structure fixes,
duplicate resolution, and malformed file repair.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from roadmap.infrastructure.maintenance.cleanup import (
    _build_move_list,
    _confirm_folder_moves,
    _perform_folder_moves,
)


class TestBuildMoveList:
    """Test _build_move_list function."""

    @pytest.mark.parametrize(
        "issue_type,expected_count",
        [
            ("empty", 0),
            ("misplaced_only", 2),
            ("orphaned_only", 2),
            ("mixed", 2),
        ],
    )
    def test_build_move_list_variants(self, issue_type, expected_count):
        """Test various move list scenarios with parametrization."""
        issues_dir = Path("/issues")

        if issue_type == "empty":
            issues = {}
        elif issue_type == "misplaced_only":
            issues = {
                "misplaced": [
                    {
                        "issue_id": "issue-1",
                        "current_location": "/issues/v1.0/issue-1.md",
                        "expected_location": "/issues/v2.0/issue-1.md",
                    },
                    {
                        "issue_id": "issue-2",
                        "current_location": "/issues/backlog/issue-2.md",
                        "expected_location": "/issues/v1.0/issue-2.md",
                    },
                ]
            }
        elif issue_type == "orphaned_only":
            issues = {
                "orphaned": [
                    {"issue_id": "issue-3", "location": "/issues/orphan/issue-3.md"},
                    {"issue_id": "issue-4", "location": "/issues/unknown/issue-4.md"},
                ]
            }
        else:  # mixed
            issues = {
                "misplaced": [
                    {
                        "issue_id": "issue-1",
                        "current_location": "/issues/v1.0/issue-1.md",
                        "expected_location": "/issues/v2.0/issue-1.md",
                    }
                ],
                "orphaned": [
                    {"issue_id": "issue-2", "location": "/issues/orphan/issue-2.md"}
                ],
            }

        result = _build_move_list(issues_dir, issues)
        assert len(result) == expected_count

    def test_build_move_list_preserves_issue_ids(self):
        """Test that issue IDs are correctly preserved."""
        issues_dir = Path("/issues")
        issues = {
            "misplaced": [
                {
                    "issue_id": "complex-id-123",
                    "current_location": "/issues/old/complex-id-123.md",
                    "expected_location": "/issues/new/complex-id-123.md",
                }
            ]
        }

        result = _build_move_list(issues_dir, issues)
        assert result[0]["issue_id"] == "complex-id-123"


class TestConfirmFolderMoves:
    """Test _confirm_folder_moves function."""

    @pytest.mark.parametrize(
        "force,mock_return,expected",
        [
            (True, None, True),
            (False, True, True),
            (False, False, False),
        ],
    )
    @patch("roadmap.infrastructure.maintenance.cleanup.click.confirm")
    def test_confirm_folder_moves_variants(
        self, mock_confirm, force, mock_return, expected
    ):
        """Test force flag and user response combinations."""
        if mock_return is not None:
            mock_confirm.return_value = mock_return

        result = _confirm_folder_moves(force=force)
        assert result is expected


class TestPerformFolderMoves:
    """Test _perform_folder_moves function."""

    @pytest.mark.parametrize(
        "num_valid,num_invalid,expected_moved,expected_failed",
        [
            (0, 0, 0, 0),
            (1, 0, 1, 0),
            (3, 0, 3, 0),
            (1, 1, 1, 1),
            (2, 2, 2, 2),
        ],
    )
    def test_perform_folder_moves_variants(
        self, tmp_path, num_valid, num_invalid, expected_moved, expected_failed
    ):
        """Test move counts with various valid/invalid combinations."""
        moves = []

        # Add valid moves
        for i in range(num_valid):
            from_file = tmp_path / "from" / f"valid{i}.md"
            from_file.parent.mkdir(exist_ok=True)
            from_file.write_text(f"content{i}")
            to_file = tmp_path / "to" / f"valid{i}.md"
            moves.append({"from": from_file, "to": to_file, "issue_id": f"issue-{i}"})

        # Add invalid moves (source doesn't exist)
        for i in range(num_invalid):
            from_file = tmp_path / "from" / f"invalid{i}.md"
            to_file = tmp_path / "to" / f"invalid{i}.md"
            moves.append(
                {"from": from_file, "to": to_file, "issue_id": f"issue-{num_valid + i}"}
            )

        moved_count, failed_count = _perform_folder_moves(moves)
        assert moved_count == expected_moved
        assert failed_count == expected_failed

    def test_perform_folder_moves_creates_parent_directories(self, tmp_path):
        """Test that parent directories are created."""
        from_file = tmp_path / "source.md"
        from_file.write_text("test")
        to_file = tmp_path / "deep" / "nested" / "path" / "dest.md"

        moves = [{"from": from_file, "to": to_file, "issue_id": "issue-1"}]

        moved_count, failed_count = _perform_folder_moves(moves)

        assert moved_count == 1
        assert to_file.exists()
        assert to_file.parent.exists()
