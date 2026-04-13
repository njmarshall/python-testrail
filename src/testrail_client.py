"""
TestRail API Client - Python Implementation
Author: NJ Marshall
Description: Production-grade TestRail integration with bulk result upload,
             dynamic test run creation, retry logic, and environment-based config.
"""

import os
import time
import requests
from requests.auth import HTTPBasicAuth
from typing import Optional


class TestRailClient:
    """
    Wrapper around the TestRail REST API v2.
    Supports authentication, result upload (single + bulk), and test run management.
    """

    STATUS_PASSED  = 1
    STATUS_BLOCKED = 2
    STATUS_RETEST  = 4
    STATUS_FAILED  = 5

    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        api_key: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ):
        self.base_url   = (base_url   or os.environ["TESTRAIL_URL"]).rstrip("/")
        self.username   = username    or os.environ["TESTRAIL_USER"]
        self.api_key    = api_key     or os.environ["TESTRAIL_API_KEY"]
        self.max_retries  = max_retries
        self.retry_delay  = retry_delay
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(self.username, self.api_key)
        self.session.headers.update({"Content-Type": "application/json"})

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _url(self, endpoint: str) -> str:
        return f"{self.base_url}/index.php?/api/v2/{endpoint}"

    def _request(self, method: str, endpoint: str, **kwargs):
        url = self._url(endpoint)
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.HTTPError as e:
                if response.status_code in (429, 500, 502, 503) and attempt < self.max_retries:
                    time.sleep(self.retry_delay * attempt)
                    continue
                raise RuntimeError(
                    f"TestRail API error [{response.status_code}] on {endpoint}: {e}"
                ) from e
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * attempt)
                    continue
                raise RuntimeError(f"Network error on {endpoint}: {e}") from e

    # ------------------------------------------------------------------
    # Test Run management
    # ------------------------------------------------------------------

    def create_test_run(
        self,
        project_id: int,
        suite_id: int,
        name: str,
        description: str = "",
        case_ids: Optional[list] = None,
    ) -> dict:
        """Dynamically create a new test run and return its details."""
        payload = {
            "suite_id":    suite_id,
            "name":        name,
            "description": description,
            "include_all": case_ids is None,
        }
        if case_ids:
            payload["case_ids"] = case_ids
        return self._request("POST", f"add_run/{project_id}", json=payload)

    def close_test_run(self, run_id: int) -> dict:
        return self._request("POST", f"close_run/{run_id}", json={})

    # ------------------------------------------------------------------
    # Result upload
    # ------------------------------------------------------------------

    def add_result_for_case(
        self,
        run_id: int,
        case_id: int,
        status_id: int,
        comment: str = "",
        elapsed: Optional[str] = None,
    ) -> dict:
        """Upload a single test result."""
        payload = {"status_id": status_id, "comment": comment}
        if elapsed:
            payload["elapsed"] = elapsed
        return self._request(
            "POST", f"add_result_for_case/{run_id}/{case_id}", json=payload
        )

    def add_results_for_cases(self, run_id: int, results: list[dict]) -> dict:
        """
        Bulk upload results in a single API call.
        Each result dict must have: case_id, status_id.
        Optional keys: comment, elapsed.
        """
        return self._request(
            "POST",
            f"add_results_for_cases/{run_id}",
            json={"results": results},
        )
