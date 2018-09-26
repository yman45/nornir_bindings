import json
import pytest


@pytest.fixture
def set_vendor_vars(scope='session'):
    '''Open JSON file with CLI commands association, read it and return as
    dictionary. Operate as pytest fixture per session.
    '''
    with open('tasks/vendor_vars.json', 'r', encoding='utf-8')as jsonf:
        vendor_vars = json.load(jsonf)
    return vendor_vars
