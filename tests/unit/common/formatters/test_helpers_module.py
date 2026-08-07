"""Unit tests for lazy formatter helper exports."""

import pytest

from roadmap.common.formatters import helpers


@pytest.mark.parametrize(
    "name",
    ["OutputFormatHandler", "format_output"],
)
def test_getattr_lazy_exports_supported_symbols(name):
    """Known symbols should be lazily loaded from cli_helpers."""
    value = getattr(helpers, name)
    assert value is not None


def test_getattr_raises_attribute_error_for_unknown_symbol():
    """Unknown symbol lookup should produce normal module AttributeError."""
    with pytest.raises(AttributeError) as exc:
        _ = helpers.not_a_real_export
    assert "not_a_real_export" in str(exc.value)


def test_all_contains_expected_symbols():
    """__all__ should advertise only supported public exports."""
    assert set(helpers.__all__) == {"format_output", "OutputFormatHandler"}
