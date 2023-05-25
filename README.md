# python-testrail
Implementation of TestRail API calls in Python
## TestRail - Introduction
TestRail is a web-based test management tool used by testers, developers and other stake holders to manage, review, track and organize software testing efforts. It follows a centralized test management concept that helps in easy communication and enables rapid development of task across QA team, dev team, and other stakeholders.
## How can test automation in Python update test results in TestRail?
To update test results in TestRail through test automation, you can use TestRail's API (Application Programming Interface) to interact with the TestRail system programmatically. Here are the general steps to follow:
1. **Integrate your test automation framework with TestRail**: You need to establish a connection between your test automation framework and TestRail using the TestRail API (See [the TestRail API doumentation](https://support.testrail.com/hc/en-us/categories/7076541806228-API-Manual)). 
2. **Obtain the necessary information**: Gather the required information that you'll need to update the test results in TestRail. This includes the TestRail **project ID**, **test run ID**, **test case ID**, and **the status** (pass, fail, blocked, etc.) of each test case.
3. **Write code to update test results**: Write code to make API requests to TestRail and update the test results accordingly. You'll typically need to make a POST request to the appropriate endpoint, providing the necessary parameters such as **test run ID**, **test case ID**, **updated status** and **comment**.
4. **Parse automation test results**: Once your test automation framework completes the test execution, parse the test results to identify the status (pass/fail) of each test case.
5. **Update test results using API**: Utilize the code written in step 4 to update the test results in TestRail by making API calls. Pass the relevant information, such as test run ID, test case ID, and the obtained test case status, to update the results in TestRail accordingly.
## How to execute TestRail API call everytime a pytest test finishes
1. **Install necessary libraries**: Ensure that you have the required libraries installed by running the following command:
```
pip install pytest-testrail requests
```
2. You can utilize pytest hooks and custom test reporting. Here's an example of how you can achieve this:
```
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
```
In this example, the hook checks if the test has a marker called case_id using the **get_testrail_case_id** functioin. If the test has the particular marker, the case ID is extracted, and the test result is updated using the **update_test_result** function from **TestRailClient**. The third parmeter, **status**, has two possible result: **1** for passed and **5** for failed.
