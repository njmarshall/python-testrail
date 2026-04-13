"""
sample_tests.py — Example tests with TestRail case ID markers
"""

import pytest


@pytest.mark.testrail_case_id("C1001")
def test_user_login_success():
    """Simulates a passing login test."""
    assert True


@pytest.mark.testrail_case_id("C1002")
def test_user_login_invalid_password():
    """Simulates a failing login test."""
    assert 1 + 1 == 3, "Expected login to fail with invalid credentials"


@pytest.mark.testrail_case_id("C1003")
def test_api_health_check():
    """Simulates a passing API health check."""
    status_code = 200
    assert status_code == 200


@pytest.mark.testrail_case_id("C1004")
@pytest.mark.skip(reason="Feature not yet implemented")
def test_password_reset_flow():
    """Skipped test — maps to a blocked result in TestRail."""
    pass
