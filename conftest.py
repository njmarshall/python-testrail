"""
conftest.py — pytest plugin for TestRail integration
-----------------------------------------------------
Collects ALL test results in memory, then bulk-uploads them
to a dynamically created TestRail run at the end of the session.

Environment variables (required):
    TESTRAIL_URL      - e.g. https://yourorg.testrail.io
    TESTRAIL_USER     - your TestRail email
    TESTRAIL_API_KEY  - your API key (not password)
    TESTRAIL_PROJECT_ID
    TESTRAIL_SUITE_ID

Environment variables (optional):
    TESTRAIL_ENABLED  - set to "true" to activate (default: false)
    TESTRAIL_RUN_NAME - custom run name (default: "Automated Run <timestamp>")
"""

import os
import time
import pytest
from testrail_client import TestRailClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_enabled() -> bool:
    return os.environ.get("TESTRAIL_ENABLED", "false").lower() == "true"


def _get_case_id(item) -> int | None:
    """Extract TestRail case ID from @pytest.mark.testrail_case_id(C1234) marker."""
    marker = item.get_closest_marker("testrail_case_id")
    if marker and marker.args:
        raw = str(marker.args[0]).lstrip("Cc")
        try:
            return int(raw)
        except ValueError:
            return None
    return None


def _build_client() -> TestRailClient:
    return TestRailClient(max_retries=3, retry_delay=2.0)


# ---------------------------------------------------------------------------
# Session-scoped storage
# ---------------------------------------------------------------------------

_results_buffer: list[dict] = []


# ---------------------------------------------------------------------------
# Pytest hooks
# ---------------------------------------------------------------------------

def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "testrail_case_id(id): mark test with a TestRail case ID (e.g. C1234 or 1234)",
    )


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Collect result after each test call phase."""
    outcome = yield
    report  = outcome.get_result()

    if call.when != "call" or not _is_enabled():
        return

    case_id = _get_case_id(item)
    if case_id is None:
        return

    if report.passed:
        status_id = TestRailClient.STATUS_PASSED
        comment   = "✅ Test passed"
    elif report.failed:
        status_id = TestRailClient.STATUS_FAILED
        comment   = f"❌ Test failed\n\n{report.longreprtext}" if hasattr(report, "longreprtext") else "❌ Test failed"
    else:
        status_id = TestRailClient.STATUS_BLOCKED
        comment   = "⚠️ Test skipped / blocked"

    _results_buffer.append({
        "case_id":   case_id,
        "status_id": status_id,
        "comment":   comment,
    })


def pytest_sessionfinish(session, exitstatus):
    """Bulk-upload all collected results to a new TestRail run."""
    if not _is_enabled() or not _results_buffer:
        return

    project_id = int(os.environ["TESTRAIL_PROJECT_ID"])
    suite_id   = int(os.environ["TESTRAIL_SUITE_ID"])
    run_name   = os.environ.get(
        "TESTRAIL_RUN_NAME",
        f"Automated Run {time.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    client = _build_client()

    # 1. Create a fresh test run scoped to executed cases
    case_ids = [r["case_id"] for r in _results_buffer]
    run = client.create_test_run(
        project_id=project_id,
        suite_id=suite_id,
        name=run_name,
        description=f"CI automated run — {len(case_ids)} test(s)",
        case_ids=case_ids,
    )
    run_id = run["id"]
    print(f"\n[TestRail] Created run #{run_id}: {run_name}")

    # 2. Bulk upload all results in one API call
    client.add_results_for_cases(run_id, _results_buffer)
    print(f"[TestRail] Uploaded {len(_results_buffer)} result(s) to run #{run_id}")

    # 3. Close the run
    client.close_test_run(run_id)
    print(f"[TestRail] Closed run #{run_id}")
