"""Tests for error classification system."""

from roadmap.core.services.sync.error_classification import (
    ErrorCategory,
    ErrorClassifier,
)


class TestErrorClassifier:
    """Test error classification and aggregation."""

    def test_classify_foreign_key_error(self):
        """Test FK constraint errors are classified correctly."""
        classifier = ErrorClassifier()

        error = classifier.classify_error(
            error_message="FOREIGN KEY constraint failed",
            error_type="IntegrityError",
            entity_type="Issue",
            entity_id="abc-123",
        )

        assert error.category == ErrorCategory.FOREIGN_KEY_CONSTRAINT
        assert error.entity_type == "Issue"
        assert error.entity_id == "abc-123"
        assert error.suggested_fix is not None
        assert "database" in error.suggested_fix.lower()

    def test_classify_milestone_not_found(self):
        """Test milestone missing errors are classified correctly."""
        classifier = ErrorClassifier()

        error = classifier.classify_error(
            error_message="Milestone not found: v1.0.0",
            error_type="ValueError",
            entity_type="Issue",
        )

        assert error.category == ErrorCategory.MILESTONE_NOT_FOUND
        assert error.suggested_fix is not None
        assert "milestone" in error.suggested_fix.lower()

    def test_classify_rate_limit_error(self):
        """Test API rate limit errors are classified correctly."""
        classifier = ErrorClassifier()

        error = classifier.classify_error(
            error_message="API rate limit exceeded (429)",
            error_type="HTTPError",
            entity_type="Issue",
        )

        assert error.category == ErrorCategory.API_RATE_LIMIT
        assert error.is_recoverable  # Rate limits are recoverable
        assert error.suggested_fix is not None
        assert "wait" in error.suggested_fix.lower()

    def test_classify_permission_denied(self):
        """Test permission errors are non-recoverable."""
        classifier = ErrorClassifier()

        error = classifier.classify_error(
            error_message="Permission denied (403 Forbidden)",
            error_type="HTTPError",
            entity_type="Issue",
        )

        assert error.category == ErrorCategory.PERMISSION_DENIED
        assert not error.is_recoverable
        assert error.suggested_fix is not None
        assert (
            "token" in error.suggested_fix.lower()
            or "permission" in error.suggested_fix.lower()
        )

    def test_classify_resource_deleted(self):
        """Test deleted resource errors."""
        classifier = ErrorClassifier()

        error = classifier.classify_error(
            error_message="Resource was deleted",
            error_type="ValueError",
            entity_type="Issue",
        )

        assert error.category == ErrorCategory.RESOURCE_DELETED
        assert error.is_recoverable
        assert error.suggested_fix is not None
        assert "deleted" in error.suggested_fix.lower()

    def test_error_aggregation(self):
        """Test that errors are aggregated by category."""
        classifier = ErrorClassifier()

        # Add multiple FK errors
        for i in range(5):
            classifier.classify_error(
                error_message="FOREIGN KEY constraint failed",
                error_type="IntegrityError",
                entity_type="Issue",
                entity_id=f"issue-{i}",
            )

        # Add milestone errors
        for i in range(3):
            classifier.classify_error(
                error_message="Milestone not found",
                error_type="ValueError",
                entity_type="Issue",
                entity_id=f"issue-ms-{i}",
            )

        summary = classifier.get_summary()

        # Should have 2 categories
        assert len(summary) == 2

        # FK errors should be first (more common)
        assert summary[0].category == ErrorCategory.FOREIGN_KEY_CONSTRAINT
        assert summary[0].count == 5

        # Milestone errors second
        assert summary[1].category == ErrorCategory.MILESTONE_NOT_FOUND
        assert summary[1].count == 3

    def test_get_total_errors(self):
        """Test total error count."""
        classifier = ErrorClassifier()

        classifier.classify_error(
            error_message="Error 1",
            error_type="ValueError",
            entity_type="Issue",
        )
        classifier.classify_error(
            error_message="Error 2",
            error_type="ValueError",
            entity_type="Milestone",
        )

        assert classifier.get_total_errors() == 2

    def test_sample_messages_limited(self):
        """Test that sample messages are limited."""
        classifier = ErrorClassifier()

        # Add 10 unique error messages
        for i in range(10):
            classifier.classify_error(
                error_message=f"Unique error message {i}",
                error_type="ValueError",
                entity_type="Issue",
            )

        summary = classifier.get_summary(max_samples=3)

        # Should only have 3 sample messages
        assert len(summary[0].sample_messages) == 3

    def test_clear_errors(self):
        """Test clearing collected errors."""
        classifier = ErrorClassifier()

        classifier.classify_error(
            error_message="Error",
            error_type="ValueError",
            entity_type="Issue",
        )

        assert classifier.get_total_errors() == 1

        classifier.clear()

        assert classifier.get_total_errors() == 0
        assert len(classifier.get_summary()) == 0

    def test_network_error_classification(self):
        """Test network-related errors."""
        classifier = ErrorClassifier()

        error = classifier.classify_error(
            error_message="Connection refused",
            error_type="ConnectionError",
            entity_type="Issue",
        )

        assert error.category == ErrorCategory.NETWORK_ERROR
        assert error.suggested_fix is not None
        assert (
            "connection" in error.suggested_fix.lower()
            or "network" in error.suggested_fix.lower()
        )

    def test_unknown_error_classification(self):
        """Test that unrecognized errors default to unknown."""
        classifier = ErrorClassifier()

        error = classifier.classify_error(
            error_message="Something completely unexpected happened",
            error_type="WeirdError",
            entity_type="Issue",
        )

        assert error.category == ErrorCategory.UNKNOWN_ERROR
        assert error.suggested_fix is not None
        assert (
            "verbose" in error.suggested_fix.lower()
            or "bug" in error.suggested_fix.lower()
        )
