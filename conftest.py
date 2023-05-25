from src.TestRailClient import TestRailClient
from src.testrail_config import get_testrail_config


def pytest_runtest_makereport(item, call):
    if call.when == "call":
        case_id = get_testrail_case_id(item)
        if case_id is not None:
            base_url, username, api_key = get_testrail_config()
            client = TestRailClient(base_url, username, api_key)
            if call.excinfo is None:
                client.update_test_result(5, case_id, 1)
                print(f"Test passed: {item.nodeid}, case id: {case_id}")
            else:
                client.update_test_result(5, case_id, 5)
                print(f"Test failed: {item.nodeid}, case id: {case_id}")


def pytest_configure(config):
    config.addinivalue_line(
        'markers',
        'testrail(case_id): Mark test with TestRail case ID'
    )


def get_testrail_case_id(item):
    if 'testrail' in item.keywords:
        marker = item.get_closest_marker('testrail')
        case_id = marker.args[0] if marker else None
        return case_id

    else:
        return None
