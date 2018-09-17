import json
import pytest


@pytest.fixture
def set_vendor_vars(scope='session'):
    with open('tasks/vendor_vars.json', 'r', encoding='utf-8')as jsonf:
        vendor_vars = json.load(jsonf)
    return vendor_vars
