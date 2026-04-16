"""
test_testrail_mock.py — Mock-based tests for TestRailClient
------------------------------------------------------------
Validates the full TestRail integration flow without a live TestRail
instance or license. All HTTP calls are intercepted by unittest.mock,
which returns realistic TestRail API v2 JSON responses.

What is being tested:
  1. TestRailClient.create_test_run()       — POST add_run/{project_id}
  2. TestRailClient.add_results_for_cases() — POST add_results_for_cases/{run_id}
  3. TestRailClient.add_result_for_case()   — POST add_result_for_case/{run_id}/{case_id}
  4. TestRailClient.close_test_run()        — POST close_run/{run_id}
  5. Retry logic                            — 429 / 503 retries up to max_retries
  6. Hard failure                           — 401 raises RuntimeError immediately
  7. Network error retry + give-up          — RequestException exhausts retries
  8. URL construction                       — trailing slash, v2 pattern
"""

import pytest
from unittest.mock import patch, MagicMock
from requests.exceptions import HTTPError, ConnectionError as ReqConnectionError

from testrail_client import TestRailClient


# ---------------------------------------------------------------------------
# Shared fixtures & helpers
# ---------------------------------------------------------------------------

BASE_URL   = "https://mock.testrail.io"
USERNAME   = "neil@example.com"
API_KEY    = "mock-api-key-abc123"
PROJECT_ID = 1
SUITE_ID   = 10
RUN_ID     = 42


def _make_client(**kwargs) -> TestRailClient:
    """Build a client with known credentials — no env vars needed."""
    return TestRailClient(
        base_url=BASE_URL,
        username=USERNAME,
        api_key=API_KEY,
        max_retries=kwargs.get("max_retries", 3),
        retry_delay=kwargs.get("retry_delay", 0),  # 0s keeps tests fast
    )


def _mock_response(payload: dict, status_code: int = 200) -> MagicMock:
    """Return a fake requests.Response-like object."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = payload
    if status_code >= 400:
        mock.raise_for_status.side_effect = HTTPError(
            f"Mock HTTP {status_code}", response=mock
        )
    else:
        mock.raise_for_status.return_value = None
    return mock


# ---------------------------------------------------------------------------
# 1. create_test_run
# ---------------------------------------------------------------------------

class TestCreateTestRun:

    def test_creates_run_with_correct_payload(self):
        """Verifies the right JSON body is sent to add_run/{project_id}."""
        fake_run = {"id": RUN_ID, "name": "CI Run", "suite_id": SUITE_ID}

        with patch("requests.Session.request") as mock_http:
            mock_http.return_value = _mock_response(fake_run)
            client = _make_client()
            result = client.create_test_run(
                project_id=PROJECT_ID,
                suite_id=SUITE_ID,
                name="CI Run",
                description="Automated",
                case_ids=[1001, 1002],
            )

        assert result["id"] == RUN_ID
        body = mock_http.call_args.kwargs["json"]
        assert body["suite_id"]    == SUITE_ID
        assert body["name"]        == "CI Run"
        assert body["include_all"] is False
        assert body["case_ids"]    == [1001, 1002]

    def test_include_all_when_no_case_ids(self):
        """When case_ids is None, include_all should be True."""
        fake_run = {"id": RUN_ID, "name": "Full Run", "suite_id": SUITE_ID}

        with patch("requests.Session.request") as mock_http:
            mock_http.return_value = _mock_response(fake_run)
            client = _make_client()
            client.create_test_run(
                project_id=PROJECT_ID,
                suite_id=SUITE_ID,
                name="Full Run",
            )

        body = mock_http.call_args.kwargs["json"]
        assert body["include_all"] is True
        assert "case_ids" not in body


# ---------------------------------------------------------------------------
# 2. add_results_for_cases (bulk upload)
# ---------------------------------------------------------------------------

class TestBulkResultUpload:

    def test_bulk_upload_sends_all_results(self):
        """Verifies all results reach the bulk endpoint in one call."""
        results = [
            {"case_id": 1001, "status_id": TestRailClient.STATUS_PASSED,  "comment": "✅ Passed"},
            {"case_id": 1002, "status_id": TestRailClient.STATUS_FAILED,  "comment": "❌ Failed"},
            {"case_id": 1003, "status_id": TestRailClient.STATUS_BLOCKED, "comment": "⚠️ Skipped"},
        ]

        with patch("requests.Session.request") as mock_http:
            mock_http.return_value = _mock_response({"results": results})
            client = _make_client()
            client.add_results_for_cases(RUN_ID, results)

        url_called = mock_http.call_args.args[1]
        assert f"add_results_for_cases/{RUN_ID}" in url_called
        body = mock_http.call_args.kwargs["json"]
        assert len(body["results"]) == 3

    def test_status_constants_match_testrail_spec(self):
        """Status IDs must match TestRail's documented API values."""
        assert TestRailClient.STATUS_PASSED  == 1
        assert TestRailClient.STATUS_BLOCKED == 2
        assert TestRailClient.STATUS_RETEST  == 4
        assert TestRailClient.STATUS_FAILED  == 5


# ---------------------------------------------------------------------------
# 3. add_result_for_case (single upload)
# ---------------------------------------------------------------------------

class TestSingleResultUpload:

    def test_single_result_hits_correct_endpoint(self):
        """Single passed result hits the correct endpoint."""
        with patch("requests.Session.request") as mock_http:
            mock_http.return_value = _mock_response({"id": 999, "status_id": 1})
            client = _make_client()
            result = client.add_result_for_case(
                run_id=RUN_ID, case_id=1001,
                status_id=TestRailClient.STATUS_PASSED,
                comment="All good",
            )

        assert result["status_id"] == 1
        url_called = mock_http.call_args.args[1]
        assert f"add_result_for_case/{RUN_ID}/1001" in url_called

    def test_elapsed_included_when_provided(self):
        """Optional elapsed field is forwarded when supplied."""
        with patch("requests.Session.request") as mock_http:
            mock_http.return_value = _mock_response({"id": 1})
            client = _make_client()
            client.add_result_for_case(
                run_id=RUN_ID, case_id=1001,
                status_id=TestRailClient.STATUS_PASSED,
                elapsed="2s",
            )

        body = mock_http.call_args.kwargs["json"]
        assert body["elapsed"] == "2s"

    def test_elapsed_omitted_when_not_provided(self):
        """Elapsed field must NOT appear if not supplied."""
        with patch("requests.Session.request") as mock_http:
            mock_http.return_value = _mock_response({"id": 1})
            client = _make_client()
            client.add_result_for_case(
                run_id=RUN_ID, case_id=1001,
                status_id=TestRailClient.STATUS_PASSED,
            )

        body = mock_http.call_args.kwargs["json"]
        assert "elapsed" not in body


# ---------------------------------------------------------------------------
# 4. close_test_run
# ---------------------------------------------------------------------------

class TestCloseTestRun:

    def test_close_run_hits_correct_endpoint(self):
        """close_test_run calls POST close_run/{run_id}."""
        with patch("requests.Session.request") as mock_http:
            mock_http.return_value = _mock_response({"id": RUN_ID})
            client = _make_client()
            client.close_test_run(RUN_ID)

        assert mock_http.call_args.args[0] == "POST"
        assert f"close_run/{RUN_ID}" in mock_http.call_args.args[1]


# ---------------------------------------------------------------------------
# 5. Retry logic — 429 / 503
# ---------------------------------------------------------------------------

class TestRetryLogic:

    def test_retries_on_429_then_succeeds(self):
        """Client retries after a 429 and succeeds on the third attempt."""
        with patch("requests.Session.request") as mock_http, \
             patch("time.sleep"):
            mock_http.side_effect = [
                _mock_response({}, 429),
                _mock_response({}, 429),
                _mock_response({"id": RUN_ID}, 200),
            ]
            result = _make_client(max_retries=3).close_test_run(RUN_ID)

        assert result["id"] == RUN_ID
        assert mock_http.call_count == 3

    def test_retries_on_503_then_succeeds(self):
        """Client retries after a 503 service unavailable."""
        with patch("requests.Session.request") as mock_http, \
             patch("time.sleep"):
            mock_http.side_effect = [
                _mock_response({}, 503),
                _mock_response({"id": RUN_ID}, 200),
            ]
            result = _make_client(max_retries=3).close_test_run(RUN_ID)

        assert result["id"] == RUN_ID
        assert mock_http.call_count == 2


# ---------------------------------------------------------------------------
# 6. Hard failure — 401 / 404 (no retry)
# ---------------------------------------------------------------------------

class TestHardFailure:

    def test_401_raises_immediately_without_retry(self):
        """401 is not retryable — should raise RuntimeError on first attempt."""
        with patch("requests.Session.request") as mock_http:
            mock_http.return_value = _mock_response({}, 401)
            with pytest.raises(RuntimeError, match="401"):
                _make_client(max_retries=3).close_test_run(RUN_ID)

        assert mock_http.call_count == 1

    def test_404_raises_immediately_without_retry(self):
        """404 is not retryable — bad project/run ID should fail fast."""
        with patch("requests.Session.request") as mock_http:
            mock_http.return_value = _mock_response({}, 404)
            with pytest.raises(RuntimeError, match="404"):
                _make_client(max_retries=3).create_test_run(
                    PROJECT_ID, SUITE_ID, "Bad Run"
                )

        assert mock_http.call_count == 1


# ---------------------------------------------------------------------------
# 7. Network error — retries then gives up
# ---------------------------------------------------------------------------

class TestNetworkErrors:

    def test_connection_error_retries_then_raises(self):
        """Persistent connection errors exhaust retries and raise RuntimeError."""
        with patch("requests.Session.request") as mock_http, \
             patch("time.sleep"):
            mock_http.side_effect = ReqConnectionError("Connection refused")
            with pytest.raises(RuntimeError, match="Network error"):
                _make_client(max_retries=3).close_test_run(RUN_ID)

        assert mock_http.call_count == 3

    def test_connection_error_recovers_on_second_attempt(self):
        """Network blip on first call — succeeds on retry."""
        with patch("requests.Session.request") as mock_http, \
             patch("time.sleep"):
            mock_http.side_effect = [
                ReqConnectionError("Blip"),
                _mock_response({"id": RUN_ID}, 200),
            ]
            result = _make_client(max_retries=3).close_test_run(RUN_ID)

        assert result["id"] == RUN_ID
        assert mock_http.call_count == 2


# ---------------------------------------------------------------------------
# 8. URL construction
# ---------------------------------------------------------------------------

class TestUrlConstruction:

    def test_base_url_trailing_slash_is_stripped(self):
        """Trailing slash on base_url must not produce double-slash URLs."""
        client = TestRailClient(
            base_url="https://mock.testrail.io/",
            username=USERNAME,
            api_key=API_KEY,
        )
        url = client._url("add_run/1")
        assert "//" not in url.replace("https://", "")

    def test_url_format_matches_testrail_v2(self):
        """URL must follow TestRail's index.php?/api/v2/ pattern."""
        client = _make_client()
        url = client._url("get_run/42")
        assert url == f"{BASE_URL}/index.php?/api/v2/get_run/42"
