"""Tests for SyncKeyNormalizer module (Tier 2 coverage)."""

from unittest.mock import MagicMock, patch

from roadmap.core.services.sync.sync_key_normalizer import (
    _apply_remote_normalization,
    _build_remote_id_mapping,
    normalize_remote_keys,
)


class TestBuildRemoteIdMapping:
    """Test suite for _build_remote_id_mapping function."""

    def test_build_mapping_from_db_only(self):
        """Test building mapping from database only."""
        local = {}
        backend = MagicMock()
        backend.get_backend_name.return_value = "github"

        remote_link_repo = MagicMock()
        remote_link_repo.get_all_links_for_backend.return_value = {
            "uuid-1": "123",
            "uuid-2": "456",
        }

        mapping, db_used = _build_remote_id_mapping(local, backend, remote_link_repo)

        assert mapping == {"123": "uuid-1", "456": "uuid-2"}
        assert db_used is True

    def test_build_mapping_from_yaml_fallback(self):
        """Test building mapping from YAML when DB is empty."""
        local_issue_1 = MagicMock()
        local_issue_1.remote_ids = {"github": "789"}

        local = {
            "uuid-3": local_issue_1,
        }
        backend = MagicMock()
        backend.get_backend_name.return_value = "github"

        remote_link_repo = MagicMock()
        remote_link_repo.get_all_links_for_backend.return_value = {}

        mapping, db_used = _build_remote_id_mapping(local, backend, remote_link_repo)

        assert mapping == {"789": "uuid-3"}
        assert db_used is True

    def test_build_mapping_db_with_yaml_supplement(self):
        """Test building mapping from DB with YAML supplement."""
        local_issue_1 = MagicMock()
        local_issue_1.remote_ids = {"github": "999"}

        local = {
            "uuid-3": local_issue_1,
            "uuid-4": MagicMock(remote_ids={"github": "1000"}),
        }
        backend = MagicMock()
        backend.get_backend_name.return_value = "github"

        remote_link_repo = MagicMock()
        remote_link_repo.get_all_links_for_backend.return_value = {
            "uuid-1": "123",
        }

        mapping, db_used = _build_remote_id_mapping(local, backend, remote_link_repo)

        assert "123" in mapping
        assert mapping["123"] == "uuid-1"
        assert db_used is True

    def test_build_mapping_no_repo(self):
        """Test building mapping with no remote_link_repo."""
        local_issue = MagicMock()
        local_issue.remote_ids = {"github": "555"}

        local = {"uuid-5": local_issue}
        backend = MagicMock()
        backend.get_backend_name.return_value = "github"

        mapping, db_used = _build_remote_id_mapping(local, backend, None)

        assert mapping == {"555": "uuid-5"}
        assert db_used is False

    def test_build_mapping_no_remote_ids(self):
        """Test building mapping when local issue has no remote_ids."""
        local_issue = MagicMock()
        local_issue.remote_ids = None

        local = {"uuid-6": local_issue}
        backend = MagicMock()
        backend.get_backend_name.return_value = "github"

        remote_link_repo = None

        mapping, db_used = _build_remote_id_mapping(local, backend, remote_link_repo)

        assert mapping == {}
        assert db_used is False

    @patch("roadmap.core.services.sync.sync_key_normalizer.logger")
    def test_build_mapping_logs_db_load(self, mock_logger):
        """Test logging when DB links are loaded."""
        local = {}
        backend = MagicMock()
        backend.get_backend_name.return_value = "gitlab"

        remote_link_repo = MagicMock()
        remote_link_repo.get_all_links_for_backend.return_value = {
            "uuid-1": "100",
            "uuid-2": "200",
        }

        _build_remote_id_mapping(local, backend, remote_link_repo, logger=mock_logger)

        assert mock_logger.debug.called


class TestApplyRemoteNormalization:
    """Test suite for _apply_remote_normalization function."""

    def test_apply_normalization_matched_keys(self):
        """Test normalizing with matched remote keys."""
        remote = {
            "123": {"title": "Issue 1"},
            "456": {"title": "Issue 2"},
        }
        mapping = {"123": "uuid-1", "456": "uuid-2"}

        normalized, unmatched = _apply_remote_normalization(remote, mapping, "github")

        assert normalized == {
            "uuid-1": {"title": "Issue 1"},
            "uuid-2": {"title": "Issue 2"},
        }
        assert unmatched == 0

    def test_apply_normalization_unmatched_keys(self):
        """Test normalizing with unmatched remote keys."""
        remote = {
            "123": {"title": "Issue 1"},
            "999": {"title": "Unmatched"},
        }
        mapping = {"123": "uuid-1"}

        normalized, unmatched = _apply_remote_normalization(remote, mapping, "github")

        assert normalized["uuid-1"] == {"title": "Issue 1"}
        assert "_remote_999" in normalized
        assert unmatched == 1

    def test_apply_normalization_all_unmatched(self):
        """Test normalizing when all keys are unmatched."""
        remote = {
            "999": {"title": "Unmatched 1"},
            "888": {"title": "Unmatched 2"},
        }
        mapping = {}

        normalized, unmatched = _apply_remote_normalization(remote, mapping, "github")

        assert "_remote_999" in normalized
        assert "_remote_888" in normalized
        assert unmatched == 2

    def test_apply_normalization_empty_remote(self):
        """Test normalizing empty remote dict."""
        remote = {}
        mapping = {"123": "uuid-1"}

        normalized, unmatched = _apply_remote_normalization(remote, mapping, "github")

        assert normalized == {}
        assert unmatched == 0

    def test_apply_normalization_string_key_conversion(self):
        """Test that keys are converted to strings."""
        remote = {
            "123": {"title": "Issue"},
            "456": {"title": "Another"},
        }
        mapping = {"123": "uuid-1"}

        normalized, unmatched = _apply_remote_normalization(remote, mapping, "github")

        assert "uuid-1" in normalized
        assert unmatched == 1

    @patch("roadmap.core.services.sync.sync_key_normalizer.logger")
    def test_apply_normalization_logs_normalized(self, mock_logger):
        """Test logging when keys are normalized."""
        remote = {"123": {"title": "Issue"}}
        mapping = {"123": "uuid-1"}

        _apply_remote_normalization(remote, mapping, "github", logger=mock_logger)

        assert mock_logger.debug.called


class TestNormalizeRemoteKeys:
    """Test suite for normalize_remote_keys function."""

    def test_normalize_remote_keys_no_backend(self):
        """Test when backend is None."""
        local = {"uuid-1": {}}
        remote = {"123": {}}

        result_local, result_remote = normalize_remote_keys(local, remote, backend=None)

        assert result_local is local
        assert result_remote is remote

    def test_normalize_remote_keys_full_flow(self):
        """Test full normalization flow."""
        local_issue = MagicMock()
        local_issue.remote_ids = {"github": "123"}
        local = {"uuid-1": local_issue}

        remote = {
            "123": {"title": "Issue 1"},
            "456": {"title": "Issue 2"},
        }

        backend = MagicMock()
        backend.get_backend_name.return_value = "github"
        backend.remote_link_repo = None

        result_local, result_remote = normalize_remote_keys(
            local, remote, backend=backend
        )

        assert result_local is local
        assert "uuid-1" in result_remote
        assert "_remote_456" in result_remote

    def test_normalize_remote_keys_with_repo(self):
        """Test normalization with remote_link_repo."""
        local = {}
        remote = {
            "123": {"title": "Issue 1"},
            "456": {"title": "Issue 2"},
        }

        backend = MagicMock()
        backend.get_backend_name.return_value = "github"
        remote_link_repo = MagicMock()
        remote_link_repo.get_all_links_for_backend.return_value = {
            "uuid-1": "123",
            "uuid-2": "456",
        }
        backend.remote_link_repo = remote_link_repo

        result_local, result_remote = normalize_remote_keys(
            local, remote, backend=backend
        )

        assert result_local is not None  # Local normalization occurred
        assert "uuid-1" in result_remote
        assert "uuid-2" in result_remote

    def test_normalize_remote_keys_preserves_local(self):
        """Test that local dict is not modified."""
        local = {"uuid-1": MagicMock(remote_ids={})}
        remote = {"123": {}}

        backend = MagicMock()
        backend.get_backend_name.return_value = "github"
        backend.remote_link_repo = None

        result_local, _ = normalize_remote_keys(local, remote, backend=backend)

        assert result_local is local

    @patch("roadmap.core.services.sync.sync_key_normalizer.logger")
    def test_normalize_remote_keys_logs_summary(self, mock_logger):
        """Test logging of normalization summary."""
        local = {}
        remote = {"123": {}, "456": {}}

        backend = MagicMock()
        backend.get_backend_name.return_value = "github"
        backend.remote_link_repo = None

        normalize_remote_keys(local, remote, backend=backend, logger=mock_logger)

        assert mock_logger.info.called


class TestNormalizationIntegration:
    """Integration tests for normalization functions."""

    def test_mixed_matched_and_new_issues(self):
        """Test normalizing mix of matched and new issues."""
        local_issue = MagicMock()
        local_issue.remote_ids = {"github": "100"}
        local = {
            "local-uuid-1": local_issue,
            "local-uuid-2": MagicMock(remote_ids={"github": "101"}),
        }

        remote = {
            "100": {"title": "Existing 1"},
            "101": {"title": "Existing 2"},
            "200": {"title": "New Issue"},
            "201": {"title": "Another New"},
        }

        backend = MagicMock()
        backend.get_backend_name.return_value = "github"
        backend.remote_link_repo = None

        _, normalized_remote = normalize_remote_keys(local, remote, backend=backend)

        assert "local-uuid-1" in normalized_remote
        assert "local-uuid-2" in normalized_remote
        assert "_remote_200" in normalized_remote
        assert "_remote_201" in normalized_remote

    def test_normalization_with_different_backends(self):
        """Test that backend name affects mapping."""
        local = {}
        remote = {"api-id-1": {}}

        backend = MagicMock()
        backend.get_backend_name.return_value = "gitlab"
        backend.remote_link_repo = None

        _, normalized_remote = normalize_remote_keys(local, remote, backend=backend)

        assert "_remote_api-id-1" in normalized_remote

    def test_normalization_empty_dicts(self):
        """Test normalization with empty dicts."""
        backend = MagicMock()
        backend.get_backend_name.return_value = "github"
        backend.remote_link_repo = None

        result_local, result_remote = normalize_remote_keys({}, {}, backend=backend)

        assert result_local == {}
        assert result_remote == {}

    def test_normalization_complex_remote_ids(self):
        """Test normalization with complex remote ID values."""
        local_issue = MagicMock()
        local_issue.remote_ids = {
            "github": "org/repo#123",
            "gitlab": "proj/issue#456",
        }
        local = {"uuid-complex": local_issue}

        remote = {
            "org/repo#123": {"title": "GitHub Issue"},
        }

        backend = MagicMock()
        backend.get_backend_name.return_value = "github"
        backend.remote_link_repo = None

        _, normalized_remote = normalize_remote_keys(local, remote, backend=backend)

        assert "uuid-complex" in normalized_remote
