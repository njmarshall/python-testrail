import pytest

@pytest.mark.testrail(100)
def test_addition():
    assert 2 + 2 == 4


@pytest.mark.testrail(101)
def test_subtraction():
    assert 5 - 3 == 1


@pytest.mark.testrail(103)
def test_multiply():
    assert 3 * 4 == 12
