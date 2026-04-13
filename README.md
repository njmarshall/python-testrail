# python-testrail

**TestRail API Integration for Python/pytest**  
_Author: NJ Marshall | Built after being laid off — solved in Python first, then ported to Java_

---

## Overview

This project provides a production-grade integration between **pytest** test suites and **TestRail** test management. It automatically pushes test pass/fail/skip results to TestRail at the end of each suite run — without any per-test boilerplate beyond a single marker.

> **Origin story:** The concept of pushing automated test results to TestRail was pioneered by a fellow SET in Java at a prior company. After being laid off, I took on the challenge independently and found my solution in Python first. This repo is the result. The Java equivalent lives at [java-testrail](https://github.com/njmarshall/java-testrail).

---

## Architecture

```
@pytest.mark.testrail_case_id("C1001")   ← marker on test function
       ↓
conftest.py (pytest hooks)
  ├── pytest_runtest_makereport()  → collects results in memory
  └── pytest_sessionfinish()      → bulk uploads at end of session
       ↓
TestRailClient (requests-based HTTP client)
       ↓
TestRail REST API v2
  ├── POST add_run/{project}          → creates scoped test run
  ├── POST add_results_for_cases      → single bulk upload (all results)
  └── POST close_run/{run}            → marks run complete
```

**Key design decisions:**
- **Bulk upload** — one API call for all results, not per-test
- **Dynamic run creation** — no hardcoded run IDs; each CI execution creates its own run
- **Environment-variable credentials** — no secrets in code or config files
- **Retry with back-off** — handles transient 429/5xx errors gracefully
- **`if: always()` in CI** — results upload even when tests fail

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Mark your tests

```python
@pytest.mark.testrail_case_id("C1001")
def test_login_success():
    assert response.status_code == 200

@pytest.mark.testrail_case_id("C1002")
def test_login_invalid_password():
    assert response.status_code == 401
```

### 3. Set environment variables

```bash
export TESTRAIL_ENABLED=true
export TESTRAIL_URL=https://yourorg.testrail.io
export TESTRAIL_USER=you@company.com
export TESTRAIL_API_KEY=your_api_key_here
export TESTRAIL_PROJECT_ID=1
export TESTRAIL_SUITE_ID=2
```

### 4. Run

```bash
pytest sample_tests.py -v
```

---

## Environment Variables

| Variable              | Required | Description                                            |
|-----------------------|----------|--------------------------------------------------------|
| `TESTRAIL_ENABLED`    | Yes      | Set to `true` to activate uploading                   |
| `TESTRAIL_URL`        | Yes      | Your TestRail instance URL                            |
| `TESTRAIL_USER`       | Yes      | TestRail email address                                |
| `TESTRAIL_API_KEY`    | Yes      | TestRail API key (not password)                       |
| `TESTRAIL_PROJECT_ID` | Yes      | TestRail project ID                                   |
| `TESTRAIL_SUITE_ID`   | Yes      | TestRail suite ID                                     |
| `TESTRAIL_RUN_NAME`   | No       | Custom run name (default: "Automated Run <timestamp>")|

---

## CI/CD (GitHub Actions)

Store secrets in **Settings → Secrets and variables → Actions**, then the workflow runs automatically on every push. See `.github/workflows/pytest-testrail.yml` for the full configuration.

```yaml
- name: Run tests
  if: always()
  env:
    TESTRAIL_ENABLED: "true"
    TESTRAIL_URL:     ${{ secrets.TESTRAIL_URL }}
    # ... other secrets
  run: pytest sample_tests.py -v
```

---

## Project Structure

```
python-testrail/
├── testrail_client.py                      ← TestRail REST API wrapper
├── conftest.py                             ← pytest hooks (collect + bulk upload)
├── sample_tests.py                         ← Example annotated tests
├── requirements.txt
└── .github/workflows/pytest-testrail.yml  ← GitHub Actions CI
```

---

## Related Projects

| Repo | Description |
|------|-------------|
| [java-testrail](https://github.com/njmarshall/java-testrail) | Java/TestNG equivalent of this integration |
| [ai-test-automation](https://github.com/njmarshall/ai-test-automation) | Java framework: RestAssured + TestNG + LLM test generation |
| [ai-test-automation-python](https://github.com/njmarshall/ai-test-automation-python) | Python equivalent: httpx + pytest + Anthropic SDK |

---

## Requirements

- Python 3.11+
- pytest 7.4+
- TestRail instance with API access enabled
