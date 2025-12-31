"""Unit tests for common decorators."""

from roadmap.common.decorators import service_operation


class MockService:
    """Mock service for testing decorators."""

    @service_operation(log_level="info")
    def success_method(self):
        return "success"

    @service_operation(default_return=None, log_level="warning")
    def exception_method(self):
        raise ValueError("Test error")

    @service_operation(default_return={"status": "error"}, log_level="error")
    def custom_return_method(self):
        raise RuntimeError("Test error")

    @service_operation(default_return=None, include_traceback=True, log_level="error")
    def traceback_method(self):
        raise ValueError("Test error")

    @service_operation(log_success=True, log_level="info")
    def log_success_method(self):
        return "success"

    @service_operation(log_level="info")
    def args_method(self, a, b):
        return a + b

    @service_operation(log_level="info")
    def kwargs_method(self, a=1, b=2):
        return a + b


class TestServiceOperationDecorator:
    """Test service operation decorator."""

    def test_service_operation_success(self):
        """Test service operation decorator on success."""
        service = MockService()
        result = service.success_method()

        assert result == "success"

    def test_service_operation_with_exception(self):
        """Test service operation decorator with exception."""
        service = MockService()
        result = service.exception_method()

        # When default_return is None, decorator returns {}
        assert result == {} or result is None

    def test_service_operation_with_default_return(self):
        """Test service operation with custom default return."""
        service = MockService()
        result = service.custom_return_method()

        assert result == {"status": "error"}

    def test_service_operation_with_traceback(self):
        """Test service operation with traceback logging."""
        service = MockService()
        result = service.traceback_method()

        # When default_return is None, decorator returns {}
        assert result == {} or result is None

    def test_service_operation_log_success(self):
        """Test service operation with success logging."""
        service = MockService()
        result = service.log_success_method()

        assert result == "success"

    def test_service_operation_with_args(self):
        """Test service operation with function arguments."""
        service = MockService()
        result = service.args_method(1, 2)

        assert result == 3

    def test_service_operation_with_kwargs(self):
        """Test service operation with keyword arguments."""
        service = MockService()
        result = service.kwargs_method(a=5, b=10)

        assert result == 15
