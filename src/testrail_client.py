import pytest
import logging
from testrail import APIClient


class TestRailClient:
    def __init__(self, base_url, username, api_key):
        self.client = None
        APIClient(base_url)
        self.client.user = username
        self.client.password = api_key

    def update_test_result(self, run_id, case_id, status, comment=''):
        try:
            result = self.client.send_post(
                f'add_result_for_case/{run_id}/{case_id}',
                {'status_id': status, 'comment': comment}
            )
            logger = logging.getLogger(__name__)
            logger.info(f'TestRail API response: {result}')
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f'Error updating TestRail result: {e}')
        return None
