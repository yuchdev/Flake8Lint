"""A test module whose test function carries a fully structured docstring (no X005)."""


def test_compliant_case():
    """[Unit] demonstrate a fully structured test docstring.

    Scenario: the documented behaviour is exercised end to end.
    Boundaries: only the public surface under test is touched.
    On failure, first check: the inputs and fixtures for drift.
    """
    assert True
