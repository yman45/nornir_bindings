from tests.helpers import create_fake_task, get_file_contents
from utils.switch_objects import SwitchInterface
from operations import check_mac_table


def test_get_interfaces_macs(set_vendor_vars):
    vendor_vars = set_vendor_vars
    cisco_no_mac_int_task = create_fake_task(get_file_contents(
            'cisco_show_mac_table_int_eth1_15.txt'),
            vendor_vars['Cisco Nexus'], None, 'nxos',
            check_mac_table.get_interfaces_macs)
    check_mac_table.get_interfaces_macs(cisco_no_mac_int_task,
                                        interface_list=['Ethernet1/15'])
    assert cisco_no_mac_int_task.host['interfaces'][0].macs_learned == 0
    cisco_svi_task = create_fake_task(get_file_contents(
            'cisco_show_mac_table_vlan412.txt'), vendor_vars['Cisco Nexus'],
            None, 'nxos', check_mac_table.get_interfaces_macs)
    check_mac_table.get_interfaces_macs(cisco_svi_task,
                                        interface_list=['Vlan412'])
    assert cisco_svi_task.host['interfaces'][0].macs_learned == 3
    huawei_no_mac_svi_task = create_fake_task(get_file_contents(
            'huawei_show_mac_table_vlan515.txt'),
            vendor_vars['Huawei CE'], None, 'huawei_vrpv8',
            check_mac_table.get_interfaces_macs)
    check_mac_table.get_interfaces_macs(huawei_no_mac_svi_task,
                                        interface_list=['Vlanif515'])
    assert huawei_no_mac_svi_task.host['interfaces'][0].macs_learned == 0
    huawei_int_task = create_fake_task(get_file_contents(
            'huawei_show_mac_table_int_10ge1_0_28.txt'),
            vendor_vars['Huawei CE'], None, 'huawei_vrpv8',
            check_mac_table.get_interfaces_macs)
    check_mac_table.get_interfaces_macs(huawei_int_task,
                                        interface_list=['10GE1/0/28'])
    assert huawei_int_task.host['interfaces'][0].macs_learned == 4
    routing_int_task = create_fake_task(
            None, vendor_vars['Huawei CE'], None, 'huawei_vrpv8',
            check_mac_table.get_interfaces_macs)
    routing_int_task.host['interfaces'] = [SwitchInterface('100GE1/0/1',
                                                           mode='routed')]
    check_mac_table.get_interfaces_macs(routing_int_task)
    assert routing_int_task.host['interfaces'][0].macs_learned == 0
