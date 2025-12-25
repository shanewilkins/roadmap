"""Tests for data integrity validator service."""

from unittest.mock import MagicMock, patch

import pytest

from roadmap.core.services.base_validator import HealthStatus
from roadmap.core.services.data_integrity_validator_service import (
    DataIntegrityValidatorService,
)
from tests.unit.domain.test_data_factory import TestDataFactory


class TestDataIntegrityValidatorService:
    """Test DataIntegrityValidatorService class."""

    @pytest.fixture
    def service(self):
        """Create a service instance."""
        return DataIntegrityValidatorService()

    @pytest.fixture
    def mock_core(self):
        """Create a mock core object."""
        core = TestDataFactory.create_mock_core(is_initialized=True)
        return core

    def test_service_init(self, service):
        """Test service initialization."""
        assert service is not None

    @patch(
        "roadmap.core.services.data_integrity_validator_service.DuplicateIssuesValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.FolderStructureValidator"
    )
    @patch("roadmap.core.services.data_integrity_validator_service.BackupValidator")
    @patch(
        "roadmap.core.services.data_integrity_validator_service.ArchivableIssuesValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.ArchivableMilestonesValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.DataIntegrityValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.OrphanedIssuesValidator"
    )
    def test_run_all_data_integrity_checks_success(
        self,
        mock_orphaned,
        mock_data_integrity,
        mock_archivable_milestones,
        mock_archivable_issues,
        mock_backup,
        mock_folder,
        mock_duplicate,
        service,
        mock_core,
    ):
        """Test running all data integrity checks successfully."""
        # Setup mock return values
        mock_duplicate.perform_check.return_value = (HealthStatus.HEALTHY, "OK")
        mock_folder.perform_check.return_value = (HealthStatus.HEALTHY, "OK")
        mock_backup.check_old_backups.return_value = (HealthStatus.HEALTHY, "OK")
        mock_archivable_issues.check_archivable_issues.return_value = (
            HealthStatus.HEALTHY,
            "OK",
        )
        mock_archivable_milestones.check_archivable_milestones.return_value = (
            HealthStatus.HEALTHY,
            "OK",
        )
        mock_data_integrity.check_data_integrity.return_value = (
            HealthStatus.HEALTHY,
            "OK",
        )
        mock_orphaned.check_orphaned_issues.return_value = (HealthStatus.HEALTHY, "OK")

        result = service.run_all_data_integrity_checks(mock_core)

        assert "duplicate_issues" in result
        assert "folder_structure" in result
        assert "old_backups" in result
        assert "archivable_issues" in result
        assert "archivable_milestones" in result
        assert "data_integrity" in result
        assert "orphaned_issues" in result

        # Verify return values are tuples with status and message
        for _, value in result.items():
            assert isinstance(value, tuple)
            assert len(value) == 2

    @patch(
        "roadmap.core.services.data_integrity_validator_service.DuplicateIssuesValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.FolderStructureValidator"
    )
    @patch("roadmap.core.services.data_integrity_validator_service.BackupValidator")
    @patch(
        "roadmap.core.services.data_integrity_validator_service.ArchivableIssuesValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.ArchivableMilestonesValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.DataIntegrityValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.OrphanedIssuesValidator"
    )
    def test_run_all_data_integrity_checks_with_unhealthy_status(
        self,
        mock_orphaned,
        mock_data_integrity,
        mock_archivable_milestones,
        mock_archivable_issues,
        mock_backup,
        mock_folder,
        mock_duplicate,
        service,
        mock_core,
    ):
        """Test running checks when some are unhealthy."""
        # Setup mixed health statuses
        mock_duplicate.perform_check.return_value = (
            HealthStatus.UNHEALTHY,
            "Found duplicates",
        )
        mock_folder.perform_check.return_value = (HealthStatus.HEALTHY, "OK")
        mock_backup.check_old_backups.return_value = (
            HealthStatus.DEGRADED,
            "Old backups found",
        )
        mock_archivable_issues.check_archivable_issues.return_value = (
            HealthStatus.HEALTHY,
            "OK",
        )
        mock_archivable_milestones.check_archivable_milestones.return_value = (
            HealthStatus.HEALTHY,
            "OK",
        )
        mock_data_integrity.check_data_integrity.return_value = (
            HealthStatus.HEALTHY,
            "OK",
        )
        mock_orphaned.check_orphaned_issues.return_value = (HealthStatus.HEALTHY, "OK")

        result = service.run_all_data_integrity_checks(mock_core)

        # Check that unhealthy checks are included
        assert result["duplicate_issues"] == (
            HealthStatus.UNHEALTHY,
            "Found duplicates",
        )
        assert result["old_backups"] == (HealthStatus.DEGRADED, "Old backups found")
        assert result["folder_structure"] == (HealthStatus.HEALTHY, "OK")

    @patch(
        "roadmap.core.services.data_integrity_validator_service.DuplicateIssuesValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.FolderStructureValidator"
    )
    @patch("roadmap.core.services.data_integrity_validator_service.BackupValidator")
    @patch(
        "roadmap.core.services.data_integrity_validator_service.ArchivableIssuesValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.ArchivableMilestonesValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.DataIntegrityValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.OrphanedIssuesValidator"
    )
    @patch("roadmap.core.services.data_integrity_validator_service.logger")
    def test_run_all_data_integrity_checks_exception_handling(
        self,
        mock_logger,
        mock_orphaned,
        mock_data_integrity,
        mock_archivable_milestones,
        mock_archivable_issues,
        mock_backup,
        mock_folder,
        mock_duplicate,
        service,
        mock_core,
    ):
        """Test exception handling during checks."""
        # Make one validator raise an exception
        mock_duplicate.perform_check.side_effect = RuntimeError("Validation error")

        result = service.run_all_data_integrity_checks(mock_core)

        # Should have error entry
        assert "error" in result
        assert result["error"][0] == HealthStatus.UNHEALTHY
        assert "Data integrity validation failed" in result["error"][1]

    @patch("roadmap.core.services.data_integrity_validator_service.get_overall_status")
    @patch(
        "roadmap.core.services.data_integrity_validator_service.DuplicateIssuesValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.FolderStructureValidator"
    )
    @patch("roadmap.core.services.data_integrity_validator_service.BackupValidator")
    @patch(
        "roadmap.core.services.data_integrity_validator_service.ArchivableIssuesValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.ArchivableMilestonesValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.DataIntegrityValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.OrphanedIssuesValidator"
    )
    def test_get_overall_status(
        self,
        mock_orphaned,
        mock_data_integrity,
        mock_archivable_milestones,
        mock_archivable_issues,
        mock_backup,
        mock_folder,
        mock_duplicate,
        mock_get_overall,
        service,
    ):
        """Test getting overall status from checks."""
        # Setup mocks
        checks = {
            "duplicate_issues": (HealthStatus.HEALTHY, "OK"),
            "folder_structure": (HealthStatus.HEALTHY, "OK"),
            "old_backups": (HealthStatus.DEGRADED, "Old backups"),
        }
        mock_get_overall.return_value = HealthStatus.DEGRADED

        result = service.get_overall_status(checks)

        assert result == HealthStatus.DEGRADED
        mock_get_overall.assert_called_once_with(checks)

    @patch("roadmap.core.services.data_integrity_validator_service.get_overall_status")
    @patch(
        "roadmap.core.services.data_integrity_validator_service.DuplicateIssuesValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.FolderStructureValidator"
    )
    @patch("roadmap.core.services.data_integrity_validator_service.BackupValidator")
    @patch(
        "roadmap.core.services.data_integrity_validator_service.ArchivableIssuesValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.ArchivableMilestonesValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.DataIntegrityValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.OrphanedIssuesValidator"
    )
    def test_get_overall_status_healthy(
        self,
        mock_orphaned,
        mock_data_integrity,
        mock_archivable_milestones,
        mock_archivable_issues,
        mock_backup,
        mock_folder,
        mock_duplicate,
        mock_get_overall,
        service,
    ):
        """Test getting overall healthy status."""
        checks = {
            "duplicate_issues": (HealthStatus.HEALTHY, "OK"),
            "folder_structure": (HealthStatus.HEALTHY, "OK"),
            "old_backups": (HealthStatus.HEALTHY, "OK"),
        }
        mock_get_overall.return_value = HealthStatus.HEALTHY

        result = service.get_overall_status(checks)

        assert result == HealthStatus.HEALTHY

    @patch("roadmap.core.services.data_integrity_validator_service.get_overall_status")
    @patch(
        "roadmap.core.services.data_integrity_validator_service.DuplicateIssuesValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.FolderStructureValidator"
    )
    @patch("roadmap.core.services.data_integrity_validator_service.BackupValidator")
    @patch(
        "roadmap.core.services.data_integrity_validator_service.ArchivableIssuesValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.ArchivableMilestonesValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.DataIntegrityValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.OrphanedIssuesValidator"
    )
    def test_get_overall_status_unhealthy(
        self,
        mock_orphaned,
        mock_data_integrity,
        mock_archivable_milestones,
        mock_archivable_issues,
        mock_backup,
        mock_folder,
        mock_duplicate,
        mock_get_overall,
        service,
    ):
        """Test getting overall unhealthy status."""
        checks = {
            "duplicate_issues": (HealthStatus.UNHEALTHY, "Found issues"),
            "folder_structure": (HealthStatus.HEALTHY, "OK"),
        }
        mock_get_overall.return_value = HealthStatus.UNHEALTHY

        result = service.get_overall_status(checks)

        assert result == HealthStatus.UNHEALTHY


class TestDataIntegrityValidatorServiceIntegration:
    """Integration tests for data integrity validator service."""

    @patch(
        "roadmap.core.services.data_integrity_validator_service.DuplicateIssuesValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.FolderStructureValidator"
    )
    @patch("roadmap.core.services.data_integrity_validator_service.BackupValidator")
    @patch(
        "roadmap.core.services.data_integrity_validator_service.ArchivableIssuesValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.ArchivableMilestonesValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.DataIntegrityValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.OrphanedIssuesValidator"
    )
    @patch("roadmap.core.services.data_integrity_validator_service.get_overall_status")
    def test_full_validation_workflow(
        self,
        mock_get_overall,
        mock_orphaned,
        mock_data_integrity,
        mock_archivable_milestones,
        mock_archivable_issues,
        mock_backup,
        mock_folder,
        mock_duplicate,
    ):
        """Test complete validation workflow."""
        service = DataIntegrityValidatorService()
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)

        # Setup validators
        mock_duplicate.perform_check.return_value = (
            HealthStatus.HEALTHY,
            "No duplicates",
        )
        mock_folder.perform_check.return_value = (HealthStatus.HEALTHY, "Folder OK")
        mock_backup.check_old_backups.return_value = (
            HealthStatus.HEALTHY,
            "Backups OK",
        )
        mock_archivable_issues.check_archivable_issues.return_value = (
            HealthStatus.HEALTHY,
            "Issues OK",
        )
        mock_archivable_milestones.check_archivable_milestones.return_value = (
            HealthStatus.HEALTHY,
            "Milestones OK",
        )
        mock_data_integrity.check_data_integrity.return_value = (
            HealthStatus.HEALTHY,
            "Data OK",
        )
        mock_orphaned.check_orphaned_issues.return_value = (
            HealthStatus.HEALTHY,
            "No orphans",
        )
        mock_get_overall.return_value = HealthStatus.HEALTHY

        # Run checks
        checks = service.run_all_data_integrity_checks(mock_core)
        overall_status = service.get_overall_status(checks)

        # Verify all checks ran
        assert len(checks) == 7
        assert all(isinstance(v, tuple) for v in checks.values())
        assert overall_status == HealthStatus.HEALTHY

    @patch(
        "roadmap.core.services.data_integrity_validator_service.DuplicateIssuesValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.FolderStructureValidator"
    )
    @patch("roadmap.core.services.data_integrity_validator_service.BackupValidator")
    @patch(
        "roadmap.core.services.data_integrity_validator_service.ArchivableIssuesValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.ArchivableMilestonesValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.DataIntegrityValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.OrphanedIssuesValidator"
    )
    @patch("roadmap.core.services.data_integrity_validator_service.get_overall_status")
    def test_mixed_validation_results(
        self,
        mock_get_overall,
        mock_orphaned,
        mock_data_integrity,
        mock_archivable_milestones,
        mock_archivable_issues,
        mock_backup,
        mock_folder,
        mock_duplicate,
    ):
        """Test validation with mixed results."""
        service = DataIntegrityValidatorService()
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)

        # Setup mixed results
        mock_duplicate.perform_check.return_value = (
            HealthStatus.UNHEALTHY,
            "3 duplicates found",
        )
        mock_folder.perform_check.return_value = (HealthStatus.HEALTHY, "Folder OK")
        mock_backup.check_old_backups.return_value = (
            HealthStatus.DEGRADED,
            "2 old backups",
        )
        mock_archivable_issues.check_archivable_issues.return_value = (
            HealthStatus.HEALTHY,
            "No archivable issues",
        )
        mock_archivable_milestones.check_archivable_milestones.return_value = (
            HealthStatus.HEALTHY,
            "No archivable milestones",
        )
        mock_data_integrity.check_data_integrity.return_value = (
            HealthStatus.HEALTHY,
            "Data OK",
        )
        mock_orphaned.check_orphaned_issues.return_value = (
            HealthStatus.HEALTHY,
            "No orphans",
        )
        mock_get_overall.return_value = HealthStatus.UNHEALTHY

        # Run checks
        checks = service.run_all_data_integrity_checks(mock_core)
        overall_status = service.get_overall_status(checks)

        # Verify results
        assert checks["duplicate_issues"][0] == HealthStatus.UNHEALTHY
        assert checks["old_backups"][0] == HealthStatus.DEGRADED
        assert overall_status == HealthStatus.UNHEALTHY

    @patch(
        "roadmap.core.services.data_integrity_validator_service.DuplicateIssuesValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.FolderStructureValidator"
    )
    @patch("roadmap.core.services.data_integrity_validator_service.BackupValidator")
    @patch(
        "roadmap.core.services.data_integrity_validator_service.ArchivableIssuesValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.ArchivableMilestonesValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.DataIntegrityValidator"
    )
    @patch(
        "roadmap.core.services.data_integrity_validator_service.OrphanedIssuesValidator"
    )
    def test_service_multiple_validations(
        self,
        mock_orphaned,
        mock_data_integrity,
        mock_archivable_milestones,
        mock_archivable_issues,
        mock_backup,
        mock_folder,
        mock_duplicate,
    ):
        """Test running validations multiple times."""
        service = DataIntegrityValidatorService()
        mock_core1 = MagicMock()
        mock_core2 = MagicMock()

        # Setup mock returns
        mock_duplicate.perform_check.return_value = (HealthStatus.HEALTHY, "OK")
        mock_folder.perform_check.return_value = (HealthStatus.HEALTHY, "OK")
        mock_backup.check_old_backups.return_value = (HealthStatus.HEALTHY, "OK")
        mock_archivable_issues.check_archivable_issues.return_value = (
            HealthStatus.HEALTHY,
            "OK",
        )
        mock_archivable_milestones.check_archivable_milestones.return_value = (
            HealthStatus.HEALTHY,
            "OK",
        )
        mock_data_integrity.check_data_integrity.return_value = (
            HealthStatus.HEALTHY,
            "OK",
        )
        mock_orphaned.check_orphaned_issues.return_value = (HealthStatus.HEALTHY, "OK")

        # Run multiple times
        result1 = service.run_all_data_integrity_checks(mock_core1)
        result2 = service.run_all_data_integrity_checks(mock_core2)

        # Both should have same structure
        assert set(result1.keys()) == set(result2.keys())
        assert len(result1) == 7
        assert len(result2) == 7
