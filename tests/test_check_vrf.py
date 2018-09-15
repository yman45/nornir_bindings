import json
import pytest
from unittest.mock import Mock, patch
from nornir.core.inventory import Host
from nornir.core.task import Task
from tasks import check_vrf_status


@pytest.fixture
def set_vendor_vars(scope='session'):
    with open('tasks/vendor_vars.json', 'r', encoding='utf-8')as jsonf:
        vendor_vars = json.load(jsonf)
    return vendor_vars


def get_file_contents(file_name):
    with open('tests/cmd_outputs/{}'.format(file_name), 'r',
              encoding='utf-8') as in_file:
        contents = in_file.read()
    return contents


def create_fake_task(output, vendor_vars, vrf_name, test_obj):
    connection = Mock()
    connection.send_command = Mock(return_value=output)
    host = Host('test-host')
    host['vendor_vars'] = vendor_vars
    host['vrf_name'] = vrf_name
    host.get_connection = Mock(return_value=connection)
    fake_task = Task(test_obj)
    fake_task.host = host
    return fake_task


def test_find_vrf(set_vendor_vars):
    vendor_vars = set_vendor_vars
    cisco_output = get_file_contents('cisco_show_vrf.txt')
    task_fail = create_fake_task(cisco_output, vendor_vars['Cisco Nexus'],
                                 'Galaxy', check_vrf_status.find_vrf)
    result_fail = check_vrf_status.find_vrf(task_fail)
    assert result_fail.failed is True
    task_true = create_fake_task(cisco_output, vendor_vars['Cisco Nexus'],
                                 'Lasers', check_vrf_status.find_vrf)
    result_true = check_vrf_status.find_vrf(task_true)
    assert result_true.failed is False
    huawei_output = get_file_contents('huawei_show_vrf.txt')
    task_fail = create_fake_task(huawei_output, vendor_vars['Huawei CE'],
                                 'Galaxy', check_vrf_status.find_vrf)
    result_fail = check_vrf_status.find_vrf(task_fail)
    assert result_fail.failed is True
    task_true = create_fake_task(huawei_output, vendor_vars['Huawei CE'],
                                 'Lasers', check_vrf_status.find_vrf)
    result_true = check_vrf_status.find_vrf(task_true)
    assert result_true.failed is False


def test_get_vrf_interfaces(set_vendor_vars):
    vendor_vars = set_vendor_vars
    cisco_output_interfaces_true = get_file_contents(
            'cisco_vrf_interfaces_present.txt')
    task_cisco_yes_int = create_fake_task(
            cisco_output_interfaces_true, vendor_vars['Cisco Nexus'],
            'Star', check_vrf_status.get_vrf_interfaces)
    task_cisco_yes_int.host['nornir_nos'] = 'nxos'
    check_vrf_status.get_vrf_interfaces(task_cisco_yes_int)
    assert len(task_cisco_yes_int.host['interfaces']) == 3
    cisco_output_interfaces_false = get_file_contents(
            'cisco_vrf_interfaces_absent.txt')
    task_cisco_no_int = create_fake_task(
            cisco_output_interfaces_false, vendor_vars['Cisco Nexus'],
            'Star', check_vrf_status.get_vrf_interfaces)
    task_cisco_no_int.host['nornir_nos'] = 'nxos'
    check_vrf_status.get_vrf_interfaces(task_cisco_no_int)
    assert len(task_cisco_no_int.host['interfaces']) == 0
    huawei_output_interfaces_true = get_file_contents(
            'huawei_vrf_interfaces_present.txt')
    task_huawei_yes_int = create_fake_task(
            huawei_output_interfaces_true, vendor_vars['Huawei CE'],
            'Star', check_vrf_status.get_vrf_interfaces)
    task_huawei_yes_int.host['nornir_nos'] = 'huawei_vrpv8'
    check_vrf_status.get_vrf_interfaces(task_huawei_yes_int)
    assert len(task_huawei_yes_int.host['interfaces']) == 2
    huawei_output_interfaces_false = get_file_contents(
            'huawei_vrf_interfaces_absent.txt')
    task_huawei_no_int = create_fake_task(
            huawei_output_interfaces_false, vendor_vars['Huawei CE'],
            'Star', check_vrf_status.get_vrf_interfaces)
    task_huawei_no_int.host['nornir_nos'] = 'huawei_vrpv8'
    check_vrf_status.get_vrf_interfaces(task_huawei_no_int)
    assert len(task_huawei_no_int.host['interfaces']) == 0
