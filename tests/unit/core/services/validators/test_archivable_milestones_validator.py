"""Tests for archivable milestones validator."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from roadmap.core.services.validator_base import HealthStatus
from roadmap.core.services.validators.archivable_milestones_validator import (
    ArchivableMilestonesValidator,
)
from tests.unit.domain.test_data_factory_generation import TestDataFactory


class TestArchivableMilestonesValidator:
    """Test ArchivableMilestonesValidator."""

    @pytest.fixture
    def mock_core(self, mock_core_initialized):
        """Create mock core with milestone service.

        Uses centralized mock_core_initialized and adds service-specific setup.
        """
        mock_core_initialized.milestone_service = TestDataFactory.create_mock_core(
            is_initialized=True
        )
        return mock_core_initialized

    def test_scan_for_archivable_milestones_empty_list(self, mock_core):
        """Test scan with no milestones."""
        mock_core.milestone_service.list_milestones.return_value = []
        result = ArchivableMilestonesValidator.scan_for_archivable_milestones(mock_core)
        assert result == []

    def test_scan_for_archivable_milestones_open_milestones(self, mock_core):
        """Test scan ignores open milestones."""
        milestone = MagicMock()
        milestone.status.value = "open"
        milestone.closed_at = None
        mock_core.milestone_service.list_milestones.return_value = [milestone]

        result = ArchivableMilestonesValidator.scan_for_archivable_milestones(mock_core)
        assert result == []

    def test_scan_for_archivable_milestones_recently_closed(self, mock_core):
        """Test scan ignores recently closed milestones."""
        now = datetime.now(UTC)
        recently_closed = now - timedelta(days=5)

        milestone = MagicMock()
        milestone.status.value = "closed"
        milestone.closed_at = recently_closed
        milestone.name = "Q1 2024"
        mock_core.milestone_service.list_milestones.return_value = [milestone]

        result = ArchivableMilestonesValidator.scan_for_archivable_milestones(
            mock_core, threshold_days=14
        )
        assert result == []

    def test_scan_for_archivable_milestones_old_closed(self, mock_core):
        """Test scan finds old closed milestones."""
        now = datetime.now(UTC)
        old_closed = now - timedelta(days=30)

        milestone = MagicMock()
        milestone.status.value = "closed"
        milestone.closed_at = old_closed
        milestone.name = "Q1 2024"
        mock_core.milestone_service.list_milestones.return_value = [milestone]

        result = ArchivableMilestonesValidator.scan_for_archivable_milestones(
            mock_core, threshold_days=14
        )
        assert len(result) == 1
        assert result[0]["name"] == "Q1 2024"
        assert result[0]["status"] == "closed"
        assert result[0]["days_since_close"] == 30

    def test_scan_for_archivable_milestones_custom_threshold(self, mock_core):
        """Test scan respects custom threshold."""
        now = datetime.now(UTC)
        old_closed = now - timedelta(days=20)

        milestone = MagicMock()
        milestone.status.value = "closed"
        milestone.closed_at = old_closed
        milestone.name = "Q2 2024"
        mock_core.milestone_service.list_milestones.return_value = [milestone]

        # Should not be included with 30 day threshold
        result = ArchivableMilestonesValidator.scan_for_archivable_milestones(
            mock_core, threshold_days=30
        )
        assert len(result) == 0

        # Should be included with 14 day threshold
        result = ArchivableMilestonesValidator.scan_for_archivable_milestones(
            mock_core, threshold_days=14
        )
        assert len(result) == 1

    def test_scan_for_archivable_milestones_exception_handling(self, mock_core):
        """Test scan handles exceptions gracefully."""
        mock_core.milestone_service.list_milestones.side_effect = Exception("DB Error")

        result = ArchivableMilestonesValidator.scan_for_archivable_milestones(mock_core)
        assert result == []

    def test_scan_for_archivable_milestones_multiple(self, mock_core):
        """Test scan finds multiple archivable milestones."""
        now = datetime.now(UTC)

        milestones = []
        for i, days_ago in enumerate([20, 30, 5, 40], 1):
            milestone = MagicMock()
            milestone.status.value = "closed"
            milestone.closed_at = now - timedelta(days=days_ago)
            milestone.name = f"Q{i} 2024"
            milestones.append(milestone)

        mock_core.milestone_service.list_milestones.return_value = milestones

        result = ArchivableMilestonesValidator.scan_for_archivable_milestones(
            mock_core, threshold_days=14
        )
        assert len(result) == 3  # All except the 5 day old one

    def test_check_archivable_milestones_no_milestones(self, mock_core):
        """Test check when no archivable milestones found."""
        with patch(
            "roadmap.core.services.validators.archivable_milestones_validator.ArchivableMilestonesValidator.scan_for_archivable_milestones",
            return_value=[],
        ):
            status, message = ArchivableMilestonesValidator.check_archivable_milestones(
                mock_core
            )
            assert status == HealthStatus.HEALTHY
            assert "No milestones to archive" in message

    def test_check_archivable_milestones_found(self, mock_core):
        """Test check when archivable milestones are found."""
        archivable = [
            {
                "name": "Q1 2024",
                "status": "closed",
                "closed_date": "2024-01-01T00:00:00",
                "days_since_close": 30,
            },
            {
                "name": "Q2 2024",
                "status": "closed",
                "closed_date": "2024-04-01T00:00:00",
                "days_since_close": 20,
            },
        ]
        with patch(
            "roadmap.core.services.validators.archivable_milestones_validator.ArchivableMilestonesValidator.scan_for_archivable_milestones",
            return_value=archivable,
        ):
            status, message = ArchivableMilestonesValidator.check_archivable_milestones(
                mock_core
            )
            assert status == HealthStatus.DEGRADED
            assert "2 milestone(s)" in message
            assert "archiv" in message.lower()

    def test_check_archivable_milestones_exception(self, mock_core):
        """Test check handles exceptions gracefully."""
        with patch(
            "roadmap.core.services.validators.archivable_milestones_validator.ArchivableMilestonesValidator.scan_for_archivable_milestones",
            side_effect=Exception("Error"),
        ):
            status, message = ArchivableMilestonesValidator.check_archivable_milestones(
                mock_core
            )
            assert status == HealthStatus.HEALTHY
            assert "Could not check" in message
