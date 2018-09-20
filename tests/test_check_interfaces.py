from tests.helpers import create_fake_task, get_file_contents
from tests.helpers import interface_name_to_file_name
from tasks import check_interfaces
from utils.switch_objects import SwitchInterface


def test_check_interfaces_status(set_vendor_vars):
    vendor_vars = set_vendor_vars
    cisco_interface_names = [
            'Ethernet1/22/2', 'Ethernet1/25', 'port-channel1.3000', 'Vlan604']
    cisco_task = create_fake_task(get_file_contents(
        'cisco_show_int_brief.txt'), vendor_vars['Cisco Nexus'], None,
        check_interfaces.check_interfaces_status)
    cisco_task.host['interfaces'] = [SwitchInterface(
        x) for x in cisco_interface_names]
    cisco_task.host['nornir_nos'] = 'nxos'
    check_interfaces.check_interfaces_status(cisco_task)
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
    assert po1_3000_int.subinterface is True
    assert vlan604_int.oper_status == 'down'
    assert vlan604_int.svi is True
    huawei_interface_names = [
            '40GE1/0/28:1', '40GE1/0/32:4', 'Vlanif1517', 'Vlanif762']
    huawei_task = create_fake_task(get_file_contents(
            'huawei_show_int_brief.txt'), vendor_vars['Huawei CE'], None,
            check_interfaces.check_interfaces_status)
    huawei_task.host['interfaces'] = [SwitchInterface(
        x) for x in huawei_interface_names]
    huawei_task.host['nornir_nos'] = 'huawei_vrpv8'
    check_interfaces.check_interfaces_status(huawei_task)
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
    assert int_vlanif762.svi is True


def test_get_interfaces_ip_addresses(set_vendor_vars):
    vendor_vars = set_vendor_vars
    cisco_interface_names = [
            'Ethernet1/22/2', 'Ethernet1/25', 'port-channel1.3000', 'Vlan604']
    outputs = []
    for interface in cisco_interface_names:
        name = interface_name_to_file_name(interface)
        file_names = ['cisco_show_ipv'+x+'_int_'+name+'.txt' for x in (
            '4', '6')]
        outputs.extend([get_file_contents(x) for x in file_names])
    cisco_task = create_fake_task(None, vendor_vars['Cisco Nexus'], None,
                                  check_interfaces.get_interfaces_ip_addresses,
                                  effect=outputs)
    cisco_task.host['interfaces'] = [SwitchInterface(
        x) for x in cisco_interface_names]
    cisco_task.host['nornir_nos'] = 'nxos'
    check_interfaces.get_interfaces_ip_addresses(cisco_task)
    eth1_22_2_int = cisco_task.host['interfaces'][0]
    eth1_25_int = cisco_task.host['interfaces'][1]
    po1_3000_int = cisco_task.host['interfaces'][2]
    vlan604_int = cisco_task.host['interfaces'][3]
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
    outputs = []
    for interface in huawei_interface_names:
        name = interface_name_to_file_name(interface)
        file_names = ['huawei_show_ipv'+x+'_int_'+name+'.txt' for x in (
            '4', '6')]
        outputs.extend([get_file_contents(x) for x in file_names])
    huawei_task = create_fake_task(
            None, vendor_vars['Huawei CE'], None,
            check_interfaces.get_interfaces_ip_addresses, effect=outputs)
    huawei_task.host['interfaces'] = [SwitchInterface(
        x) for x in huawei_interface_names]
    huawei_task.host['nornir_nos'] = 'huawei_vrpv8'
    check_interfaces.get_interfaces_ip_addresses(huawei_task)
    int_40ge1_0_28_1 = huawei_task.host['interfaces'][0]
    int_40ge1_0_32_4 = huawei_task.host['interfaces'][1]
    int_vlanif1517 = huawei_task.host['interfaces'][2]
    int_vlanif762 = huawei_task.host['interfaces'][3]
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
