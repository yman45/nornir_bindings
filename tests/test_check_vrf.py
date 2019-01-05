import pytest
from tests.helpers import create_fake_task, get_file_contents
from operations import check_vrf_status
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
    result = check_vrf_status.get_vrf_interfaces(task_cisco_no_int)
    assert len(task_cisco_no_int.host['interfaces']) == 0
    assert result.failed is True
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
    result = check_vrf_status.get_vrf_interfaces(task_huawei_no_int)
    assert len(task_huawei_no_int.host['interfaces']) == 0
    assert result.failed is True
    task_huawei_no_int.host.platform = 'eos'
    with pytest.raises(UnsupportedNOS):
        check_vrf_status.get_vrf_interfaces(task_huawei_no_int)


def test_check_vrf_bgp_neighbors(set_vendor_vars):
    vendor_vars = set_vendor_vars
    cisco_v6_task = create_fake_task(get_file_contents(
        'cisco_show_bgp_ipv6_vrf_neighbors.txt'), vendor_vars['Cisco Nexus'],
        'Galaxy', 'nxos', check_vrf_status.check_vrf_bgp_neighbors)
    check_vrf_status.check_vrf_bgp_neighbors(cisco_v6_task, af='v6')
    assert len(cisco_v6_task.host['bgp_neighbors']) == 2
    assert cisco_v6_task.host['bgp_neighbors']['fe80::152:12'].state == \
        'established'
    assert cisco_v6_task.host['bgp_neighbors']['fe80::152:12']._type == \
        'external'
    assert cisco_v6_task.host['bgp_neighbors']['fe80::152:12'].as_number == \
        '65001'
    assert cisco_v6_task.host['bgp_neighbors']['fe80::152:12'].router_id.\
        compressed == '172.20.134.2'
    assert cisco_v6_task.host['bgp_neighbors']['fe80::152:12'].af['ipv4'] is \
        None
    v6 = cisco_v6_task.host['bgp_neighbors']['fe80::152:12'].af['ipv6']
    assert v6.learned_routes == 1975
    assert v6.sent_routes == 7
    huawei_v6_task = create_fake_task(get_file_contents(
        'huawei_show_bgp_ipv6_vrf_neighbors.txt'), vendor_vars['Huawei CE'],
        'Galaxy', 'huawei_vrpv8', check_vrf_status.check_vrf_bgp_neighbors)
    check_vrf_status.check_vrf_bgp_neighbors(huawei_v6_task, af='v6')
    assert len(huawei_v6_task.host['bgp_neighbors']) == 2
    assert huawei_v6_task.host['bgp_neighbors']['fe80::dd:a1'].state == \
        'established'
    assert huawei_v6_task.host['bgp_neighbors']['fe80::dd:a1']._type == \
        'external'
    assert huawei_v6_task.host['bgp_neighbors']['fe80::dd:a1'].as_number == \
        '65012'
    assert huawei_v6_task.host['bgp_neighbors']['fe80::dd:a1'].router_id.\
        compressed == '172.24.16.1'
    assert huawei_v6_task.host['bgp_neighbors']['fe80::dd:a1'].af['ipv4'] is \
        None
    v6 = huawei_v6_task.host['bgp_neighbors']['fe80::dd:a1'].af['ipv6']
    assert v6.learned_routes == 1980
    assert v6.sent_routes == 1982
