import pytest
from tests.helpers import create_fake_task, get_file_contents
from tasks import check_vrf_status
from app_exception import UnsupportedNOS


def test_find_vrf(set_vendor_vars):
    vendor_vars = set_vendor_vars
    cisco_output = get_file_contents('cisco_show_vrf.txt')
    task_fail = create_fake_task(cisco_output, vendor_vars['Cisco Nexus'],
                                 'Galaxy', 'nxos', check_vrf_status.find_vrf)
    result_fail = check_vrf_status.find_vrf(task_fail)
    assert result_fail.failed is True
    task_true = create_fake_task(cisco_output, vendor_vars['Cisco Nexus'],
                                 'Lasers', 'nxos', check_vrf_status.find_vrf)
    result_true = check_vrf_status.find_vrf(task_true)
    assert result_true.failed is False
    huawei_output = get_file_contents('huawei_show_vrf.txt')
    task_fail = create_fake_task(huawei_output, vendor_vars['Huawei CE'],
                                 'Galaxy', 'huawei_vrpv8',
                                 check_vrf_status.find_vrf)
    result_fail = check_vrf_status.find_vrf(task_fail)
    assert result_fail.failed is True
    task_true = create_fake_task(huawei_output, vendor_vars['Huawei CE'],
                                 'Lasers', 'huawei_vrpv8',
                                 check_vrf_status.find_vrf)
    result_true = check_vrf_status.find_vrf(task_true)
    assert result_true.failed is False


def test_get_vrf_interfaces(set_vendor_vars):
    vendor_vars = set_vendor_vars
    cisco_output_interfaces_true = get_file_contents(
            'cisco_vrf_interfaces_present.txt')
    task_cisco_yes_int = create_fake_task(
            cisco_output_interfaces_true, vendor_vars['Cisco Nexus'],
            'Star', 'nxos', check_vrf_status.get_vrf_interfaces)
    check_vrf_status.get_vrf_interfaces(task_cisco_yes_int)
    assert len(task_cisco_yes_int.host['interfaces']) == 3
    cisco_output_interfaces_false = get_file_contents(
            'cisco_vrf_interfaces_absent.txt')
    task_cisco_no_int = create_fake_task(
            cisco_output_interfaces_false, vendor_vars['Cisco Nexus'],
            'Star', 'nxos', check_vrf_status.get_vrf_interfaces)
    check_vrf_status.get_vrf_interfaces(task_cisco_no_int)
    assert len(task_cisco_no_int.host['interfaces']) == 0
    huawei_output_interfaces_true = get_file_contents(
            'huawei_vrf_interfaces_present.txt')
    task_huawei_yes_int = create_fake_task(
            huawei_output_interfaces_true, vendor_vars['Huawei CE'],
            'Star', 'huawei_vrpv8', check_vrf_status.get_vrf_interfaces)
    check_vrf_status.get_vrf_interfaces(task_huawei_yes_int)
    assert len(task_huawei_yes_int.host['interfaces']) == 2
    huawei_output_interfaces_false = get_file_contents(
            'huawei_vrf_interfaces_absent.txt')
    task_huawei_no_int = create_fake_task(
            huawei_output_interfaces_false, vendor_vars['Huawei CE'],
            'Star', 'huawei_vrpv8', check_vrf_status.get_vrf_interfaces)
    check_vrf_status.get_vrf_interfaces(task_huawei_no_int)
    assert len(task_huawei_no_int.host['interfaces']) == 0
    task_huawei_no_int.host['nornir_nos'] = 'eos'
    with pytest.raises(UnsupportedNOS):
        check_vrf_status.get_vrf_interfaces(task_huawei_no_int)
