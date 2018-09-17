import json
import pytest
from unittest.mock import Mock
from nornir.core.inventory import Host
from nornir.core.task import Task
from tasks import check_vrf_status
from app_exception import UnsupportedNOS


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


def create_fake_task(output, vendor_vars, vrf_name, test_obj, effect=None):
    connection = Mock()
    if effect is None:
        connection.send_command = Mock(return_value=output)
    else:
        connection.send_command = Mock(side_effect=effect)
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
    task_huawei_no_int.host['nornir_nos'] = 'eos'
    with pytest.raises(UnsupportedNOS):
        check_vrf_status.get_vrf_interfaces(task_huawei_no_int)


def test_check_interfaces_state(set_vendor_vars):
    vendor_vars = set_vendor_vars
    cisco_interface_names = [
            'Ethernet1/22/2', 'Ethernet1/25', 'port-channel1.3000', 'Vlan604']
    cisco_file_names = [
            'show_int_brief', 'show_ipv4_int_eth1_22_2',
            'show_ipv4_int_eth1_25', 'show_ipv4_int_po1_3000',
            'show_ipv4_int_vlan604', 'show_ipv6_int_eth1_22_2',
            'show_ipv6_int_eth1_25', 'show_ipv6_int_po1_3000',
            'show_ipv6_int_vlan604']
    cisco_outputs = [get_file_contents(
        'cisco_'+x+'.txt') for x in cisco_file_names]
    cisco_task = create_fake_task(None, vendor_vars['Cisco Nexus'], None,
                                  check_vrf_status.check_interfaces_state,
                                  effect=cisco_outputs)
    cisco_task.host['interfaces'] = [
            check_vrf_status.SwitchInterface(x) for x in cisco_interface_names]
    cisco_task.host['nornir_nos'] = 'nxos'
    check_vrf_status.check_interfaces_state(cisco_task)
    eth1_22_2_int = cisco_task.host['interfaces'][0]
    eth1_25_int = cisco_task.host['interfaces'][1]
    po1_3000_int = cisco_task.host['interfaces'][2]
    vlan604_int = cisco_task.host['interfaces'][3]
    assert eth1_22_2_int.admin_status == 'down'
    assert eth1_25_int.admin_status == 'up'
    assert po1_3000_int.admin_status == 'up'
    assert vlan604_int.admin_status == 'up'
    assert eth1_22_2_int.oper_status == 'down'
    assert eth1_25_int.oper_status == 'up'
    assert po1_3000_int.oper_status == 'up'
    assert vlan604_int.oper_status == 'down'
    assert len(eth1_22_2_int.ipv4_addresses) == 0
    assert len(eth1_25_int.ipv4_addresses) == 1
    assert eth1_25_int.ipv4_addresses[0].address.exploded == '172.18.10.9'
    assert eth1_25_int.ipv4_addresses[0].prefix_length == 26
    assert len(po1_3000_int.ipv4_addresses) == 3
    assert po1_3000_int.ipv4_addresses[0].primary is True
    assert po1_3000_int.ipv4_addresses[2].primary is False
    assert len(vlan604_int.ipv4_addresses) == 0
    assert len(eth1_22_2_int.ipv6_addresses) == 0
    assert len(eth1_25_int.ipv6_addresses) == 0
    assert len(po1_3000_int.ipv6_addresses) == 2
    assert po1_3000_int.ipv6_addresses[1].address.is_link_local is True
    assert po1_3000_int.ipv6_addresses[0].prefix_length == 128
    assert len(vlan604_int.ipv6_addresses) == 4
    assert vlan604_int.ipv6_addresses[0].primary is True
    assert vlan604_int.ipv6_addresses[1].primary is False
    huawei_interface_names = [
            '40GE1/0/28:1', '40GE1/0/32:4', 'Vlanif1517', 'Vlanif762']
    huawei_file_names = [
            'show_int_brief', 'show_ipv4_int_40ge1_0_28_1',
            'show_ipv4_int_40ge1_0_32_4', 'show_ipv4_int_vlanif1517',
            'show_ipv4_int_vlanif762', 'show_ipv6_int_40ge1_0_28_1',
            'show_ipv6_int_40ge1_0_32_4', 'show_ipv6_int_vlanif1517',
            'show_ipv6_int_vlanif762']
    huawei_outputs = [get_file_contents(
        'huawei_'+x+'.txt') for x in huawei_file_names]
    huawei_task = create_fake_task(None, vendor_vars['Huawei CE'], None,
                                   check_vrf_status.check_interfaces_state,
                                   effect=huawei_outputs)
    huawei_task.host['interfaces'] = [
            check_vrf_status.SwitchInterface(
                x) for x in huawei_interface_names]
    huawei_task.host['nornir_nos'] = 'huawei_vrpv8'
    check_vrf_status.check_interfaces_state(huawei_task)
    int_40ge1_0_28_1 = huawei_task.host['interfaces'][0]
    int_40ge1_0_32_4 = huawei_task.host['interfaces'][1]
    int_vlanif1517 = huawei_task.host['interfaces'][2]
    int_vlanif762 = huawei_task.host['interfaces'][3]
    assert int_40ge1_0_28_1.admin_status == 'down'
    assert int_40ge1_0_32_4.admin_status == 'up'
    assert int_vlanif1517.admin_status == 'up'
    assert int_vlanif762.admin_status == 'up'
    assert int_40ge1_0_28_1.oper_status == 'down'
    assert int_40ge1_0_32_4.oper_status == 'down'
    assert int_vlanif1517.oper_status == 'up'
    assert int_vlanif762.oper_status == 'up'
    assert len(int_40ge1_0_28_1.ipv4_addresses) == 1
    assert int_40ge1_0_28_1.ipv4_addresses[0].address.exploded == \
        '192.168.13.13'
    assert int_40ge1_0_28_1.ipv4_addresses[0].prefix_length == 24
    assert len(int_40ge1_0_32_4.ipv4_addresses) == 0
    assert len(int_vlanif1517.ipv4_addresses) == 3
    assert int_vlanif1517.ipv4_addresses[0].primary is True
    assert int_vlanif1517.ipv4_addresses[2].primary is False
    assert len(int_vlanif762.ipv4_addresses) == 0
    assert len(int_40ge1_0_28_1.ipv6_addresses) == 0
    assert len(int_40ge1_0_32_4.ipv6_addresses) == 3
    assert int_40ge1_0_32_4.ipv6_addresses[1].primary is False
    assert int_40ge1_0_32_4.ipv6_addresses[2].primary is False
    assert len(int_vlanif1517.ipv6_addresses) == 0
    assert len(int_vlanif762.ipv6_addresses) == 2
    assert int_vlanif762.ipv6_addresses[0].address.is_link_local is True
    assert int_vlanif762.ipv6_addresses[1].prefix_length == 64
