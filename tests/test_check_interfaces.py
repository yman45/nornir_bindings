import pytest
from tests.helpers import create_fake_task, get_file_contents
from operations import check_interfaces
from utils.switch_objects import SwitchInterface


def interface_name_to_file_name(name):
    '''Translate interface name for using into file names replacing different
    symbols with '_'.
    Arguments:
        * name - interface name
    Returns:
        * translated name
    '''
    trans_dict = {ord(':'): '_',
                  ord('/'): '_',
                  ord('.'): '_',
                  ord('-'): '_'}
    return name.lower().translate(trans_dict)


def prepare_interfaces(fake_task, interface_list):
    '''Generate and assign list of utils.switch_objects.SwitchInterface to
    task.host['interfaces'] and returns that list.
    Arguments:
        * fake_task - nornir.core.task.Task with mocked internals
        * interface_list - list of interface names
    Returns:
        * list of utils.switch_objects.SwitchInterface
    '''
    fake_task.host['interfaces'] = [SwitchInterface(x) for x in interface_list]
    return [x for x in fake_task.host['interfaces']]


def get_ip_outputs(interfaces, vendor, pad=''):
    '''Get different file contents for commands that imply both IPv4 and IPv6
    for list of interfaces. Little helper to open up different files.
    Arguments:
        * interfaces - list of interface names
        * vendor - lower case vendor name to use in file names
        * pad (defaults to '') - additional field to insert into file name
    Returns:
        * list of file contents outputs
    '''
    outputs = []
    for interface in interfaces:
        name = interface_name_to_file_name(interface)
        file_names = [vendor+'_show_ipv'+x+pad+'_int_'+name+'.txt' for x in (
            '4', '6')]
        outputs.extend([get_file_contents(x) for x in file_names])
    return outputs


def test_convert_mac_address():
    with pytest.raises(ValueError):
        check_interfaces.convert_mac_address('bc3f.0a2b.16')
    with pytest.raises(ValueError):
        check_interfaces.convert_mac_address('bc3f.0a2b.167254')
    with pytest.raises(ValueError):
        check_interfaces.convert_mac_address('bc3f.0axb.1672')
    assert check_interfaces.convert_mac_address(
            'bc3f.0a2b.1672') == 'bc:3f:0a:2b:16:72'
    assert check_interfaces.convert_mac_address(
            'bc3f-0a2b-1672') == 'bc:3f:0a:2b:16:72'
    assert check_interfaces.convert_mac_address(
            'bc3F-0a2B-1672') == 'bc:3f:0a:2b:16:72'


def test_check_interfaces_status(set_vendor_vars):
    vendor_vars = set_vendor_vars
    cisco_interface_names = [
            'Ethernet1/22/2', 'Ethernet1/25', 'port-channel1.3000', 'Vlan604']
    cisco_task = create_fake_task(get_file_contents(
        'cisco_show_int_brief.txt'), vendor_vars['Cisco Nexus'], None, 'nxos',
        check_interfaces.check_interfaces_status)
    eth1_22_2_int, eth1_25_int, po1_3000_int, vlan604_int = prepare_interfaces(
        cisco_task, cisco_interface_names)
    check_interfaces.check_interfaces_status(cisco_task)
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
            'huawei_vrpv8', check_interfaces.check_interfaces_status)
    int_40ge1_0_28_1, int_40ge1_0_32_4, int_vlanif1517, int_vlanif762 = \
        prepare_interfaces(huawei_task, huawei_interface_names)
    check_interfaces.check_interfaces_status(huawei_task)
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
    outputs = get_ip_outputs(cisco_interface_names, 'cisco')
    cisco_task = create_fake_task(
            None, vendor_vars['Cisco Nexus'], None, 'nxos',
            check_interfaces.get_interfaces_ip_addresses, effect=outputs)
    eth1_22_2_int, eth1_25_int, po1_3000_int, vlan604_int = prepare_interfaces(
        cisco_task, cisco_interface_names)
    check_interfaces.get_interfaces_ip_addresses(cisco_task)
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
    outputs = get_ip_outputs(huawei_interface_names, 'huawei')
    huawei_task = create_fake_task(
            None, vendor_vars['Huawei CE'], None, 'huawei_vrpv8',
            check_interfaces.get_interfaces_ip_addresses, effect=outputs)
    int_40ge1_0_28_1, int_40ge1_0_32_4, int_vlanif1517, int_vlanif762 = \
        prepare_interfaces(huawei_task, huawei_interface_names)
    check_interfaces.get_interfaces_ip_addresses(huawei_task)
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


def test_check_arbitrary_interface(set_vendor_vars):
    vendor_vars = set_vendor_vars
    interface = ['40GE1/0/32:4']
    fake_task = create_fake_task(get_file_contents(
            'huawei_show_int_brief.txt'), vendor_vars['Huawei CE'], None,
            'huawei_vrpv8', check_interfaces.check_interfaces_status)
    check_interfaces.check_interfaces_status(fake_task,
                                             interface_list=interface)
    assert fake_task.host['interfaces'][0].admin_status == 'up'
    assert fake_task.host['interfaces'][0].oper_status == 'down'
    outputs = get_ip_outputs(interface, 'huawei')
    fake_task = create_fake_task(
            None, vendor_vars['Huawei CE'], None, 'huawei_vrpv8',
            check_interfaces.get_interfaces_ip_addresses, effect=outputs)
    check_interfaces.get_interfaces_ip_addresses(fake_task,
                                                 interface_list=interface)
    assert len(fake_task.host['interfaces'][0].ipv4_addresses) == 0
    assert len(fake_task.host['interfaces'][0].ipv6_addresses) == 3


def test_get_interfaces_ip_neighbors(set_vendor_vars):
    vendor_vars = set_vendor_vars
    sw_task = create_fake_task('placeholder', vendor_vars['Cisco Nexus'],
                               'Galaxy', 'nxos',
                               check_interfaces.get_interfaces_ip_neighbors)
    sw_task.host['interfaces'] = [SwitchInterface('Ethernet1/32')]
    check_interfaces.get_interfaces_ip_neighbors(sw_task)
    assert sw_task.host['interfaces'][0].ipv4_neighbors == 0
    outputs = get_ip_outputs(['Ethernet1/31.3013'], 'cisco',
                             pad='_neighbors_vrf')
    cisco_task = create_fake_task(
            None, vendor_vars['Cisco Nexus'], 'Galaxy', 'nxos',
            check_interfaces.get_interfaces_ip_neighbors, effect=outputs)
    interface = prepare_interfaces(cisco_task, ['Ethernet1/31.3013'])[0]
    check_interfaces.get_interfaces_ip_neighbors(cisco_task)
    assert interface.ipv4_neighbors == 5
    assert interface.ipv6_neighbors == 3
    outputs = get_ip_outputs(['100GE1/0/2.3000', 'Vlanif761'], 'huawei',
                             pad='_neighbors')
    huawei_task = create_fake_task(
            None, vendor_vars['Huawei CE'], 'Lasers', 'huawei_vrpv8',
            check_interfaces.get_interfaces_ip_neighbors, effect=outputs)
    int_100ge1_0_2_3000, int_vlanif761 = prepare_interfaces(
            huawei_task, ['100GE1/0/2.3000', 'Vlanif761'])
    check_interfaces.get_interfaces_ip_neighbors(huawei_task)
    assert int_100ge1_0_2_3000.ipv4_neighbors == 2
    assert int_100ge1_0_2_3000.ipv6_neighbors == 3
    assert int_vlanif761.ipv4_neighbors == 0
    assert int_vlanif761.ipv6_neighbors == 0


def test_get_interfaces_mode(set_vendor_vars):
    vendor_vars = set_vendor_vars
    cisco_interface_names = [
            'Ethernet1/22/1', 'Ethernet1/23/2', 'Ethernet1/25',
            'port-channel1.3000', 'port-channel2', 'Vlan604']
    cisco_task = create_fake_task(get_file_contents(
        'cisco_show_int_brief.txt'), vendor_vars['Cisco Nexus'], None, 'nxos',
        check_interfaces.get_interfaces_mode)
    (eth1_22_1_int, eth1_23_2_int, eth1_25_int, po1_3000_int, po2_int,
        vlan604_int) = prepare_interfaces(cisco_task, cisco_interface_names)
    check_interfaces.get_interfaces_mode(cisco_task)
    assert eth1_22_1_int.mode == 'switched'
    assert eth1_23_2_int.mode == 'switched'
    assert eth1_25_int.mode == 'routed'
    assert po1_3000_int.mode == 'routed'
    assert po2_int.mode == 'routed'
    assert vlan604_int.mode == 'routed'
    huawei_interface_names = [
             '40GE1/0/17', '40GE1/0/2:1', 'Eth-Trunk1.3017', 'Vlanif761']
    outputs = []
    for interface in huawei_interface_names:
        name = interface_name_to_file_name(interface)
        file_name = 'huawei_show_int_' + name + '.txt'
        outputs.append(get_file_contents(file_name))
    huawei_task = create_fake_task(
            None, vendor_vars['Huawei CE'], None, 'huawei_vrpv8',
            check_interfaces.get_interfaces_mode, effect=outputs)
    int_40ge1_0_17, int_40ge1_0_2_1, int_eth_trunk1_3017, int_vlanif761 = \
        prepare_interfaces(huawei_task, huawei_interface_names)
    check_interfaces.get_interfaces_mode(huawei_task)
    assert int_40ge1_0_17.mode == 'routed'
    assert int_40ge1_0_2_1.mode == 'switched'
    assert int_eth_trunk1_3017.mode == 'routed'
    assert int_vlanif761.mode == 'routed'


def test_get_interfaces_general_info(set_vendor_vars):
    vendor_vars = set_vendor_vars
    cisco_interface_names = [
            'Ethernet1/3/1', 'Ethernet1/31.3000', 'port-channel2', 'Vlan741']
    outputs = []
    for interface in cisco_interface_names:
        name = interface_name_to_file_name(interface)
        file_name = 'cisco_show_int_' + name + '.txt'
        outputs.append(get_file_contents(file_name))
    cisco_task = create_fake_task(
            None, vendor_vars['Cisco Nexus'], None, 'nxos',
            check_interfaces.get_interfaces_general_info, effect=outputs)
    eth1_3_1_int, eth1_31_3000_int, po2_int, vlan741_int = prepare_interfaces(
            cisco_task, cisco_interface_names)
    check_interfaces.get_interfaces_general_info(cisco_task)
    assert eth1_3_1_int.description is None
    assert eth1_3_1_int.mac_address == '74:a0:2f:4c:b6:50'
    assert eth1_3_1_int.mtu == 1500
    assert eth1_3_1_int.speed == 10
    assert eth1_3_1_int.duplex == 'full'
    assert eth1_3_1_int.load_in == 0.005
    assert eth1_3_1_int.load_out == 0.016
    assert eth1_31_3000_int.description is None
    assert eth1_31_3000_int.mac_address == '88:1d:fc:ef:48:3c'
    assert eth1_31_3000_int.mtu == 9000
    assert eth1_31_3000_int.speed is None
    assert eth1_31_3000_int.duplex is None
    assert eth1_31_3000_int.load_in is None
    assert eth1_31_3000_int.load_out is None
    assert po2_int.description == 'leaf-3x4 port-channel3'
    assert po2_int.mac_address == '74:a0:2f:4c:b6:81'
    assert po2_int.mtu == 9000
    assert po2_int.speed == 40
    assert po2_int.duplex == 'full'
    assert po2_int.load_in == 1.178
    assert po2_int.load_out == 1.385
    assert vlan741_int.description is None
    assert vlan741_int.mac_address == '74:a0:2f:4c:b6:81'
    assert vlan741_int.mtu == 9000
    assert vlan741_int.speed is None
    assert vlan741_int.duplex is None
    assert vlan741_int.load_in is None
    assert vlan741_int.load_out is None
    huawei_interface_names = [
            '40GE1/0/2:1', '10GE1/0/2.3013', 'Eth-Trunk0', 'Vlanif761']
    outputs = []
    for interface in huawei_interface_names:
        name = interface_name_to_file_name(interface)
        file_name = 'huawei_show_int_' + name + '.txt'
        outputs.append(get_file_contents(file_name))
    huawei_task = create_fake_task(
            None, vendor_vars['Huawei CE'], None, 'huawei_vrpv8',
            check_interfaces.get_interfaces_general_info, effect=outputs)
    (int_40ge1_0_2_1, int_10ge1_0_2_3013, int_eth_trunk0,
        int_vlanif761) = prepare_interfaces(huawei_task,
                                            huawei_interface_names)
    check_interfaces.get_interfaces_general_info(huawei_task)
    assert int_40ge1_0_2_1.description == '\\'
    assert int_40ge1_0_2_1.mac_address == '30:d1:7e:e3:f9:61'
    assert int_40ge1_0_2_1.mtu == 9712
    assert int_40ge1_0_2_1.speed == 10
    assert int_40ge1_0_2_1.duplex == 'full'
    assert int_40ge1_0_2_1.load_in == 0.143
    assert int_40ge1_0_2_1.load_out == 0.117
    assert int_10ge1_0_2_3013.description is None
    assert int_10ge1_0_2_3013.mac_address == 'bc:9c:31:c6:e2:c2'
    assert int_10ge1_0_2_3013.mtu == 9000
    assert int_10ge1_0_2_3013.speed is None
    assert int_10ge1_0_2_3013.duplex is None
    assert int_10ge1_0_2_3013.load_in is None
    assert int_10ge1_0_2_3013.load_out is None
    assert int_eth_trunk0.description is None
    assert int_eth_trunk0.mac_address == 'ac:4e:91:46:35:91'
    assert int_eth_trunk0.mtu == 9216
    assert int_eth_trunk0.speed == 2
    assert int_eth_trunk0.duplex == 'full'
    assert int_eth_trunk0.load_in == 0.001
    assert int_eth_trunk0.load_out == 0.001
    assert int_vlanif761.description is None
    assert int_vlanif761.mac_address == '30:d1:7e:e3:f9:67'
    assert int_vlanif761.mtu == 9000
    assert int_vlanif761.speed is None
    assert int_vlanif761.duplex is None
    assert int_vlanif761.load_in is None
    assert int_vlanif761.load_out is None


@pytest.mark.xfail(reason="operation not implemented")
def test_sanitize_interface_list(set_vendor_vars):
    vendor_vars = set_vendor_vars
    no_interface_task = create_fake_task(
            None, None, None, None, check_interfaces.sanitize_interface_list)
    result = check_interfaces.sanitize_interface_list(no_interface_task, '')
    assert result.failed is True
    huawei_interface_names = [
            '40GE1/0/2:1', '10GE1/0/2.3013', 'Eth-Trunk0', 'Vlanif761']
    outputs = []
    for interface in huawei_interface_names:
        name = interface_name_to_file_name(interface)
        file_name = 'huawei_show_int_' + name + '.txt'
        outputs.append(get_file_contents(file_name))
    # add incorrect interface
    huawei_interface_names.insert(2, '24GE1/77')
    outputs.insert(2, '''"^\nError: Wrong parameter found at '^' position."''')
    huawei_task = create_fake_task(
            None, vendor_vars['Huawei CE'], None, 'huawei_vrpv8',
            check_interfaces.sanitize_interface_list, effect=outputs)
    check_interfaces.sanitize_interface_list(huawei_task,
                                             huawei_interface_names)
    assert len(huawei_task.host['interfaces']) == 4
    assert '24GE1/77' not in huawei_task.host['interfaces']
    assert 'Eth-Trunk0' in huawei_task.host['interfaces']
    vendor_vars = set_vendor_vars
    cisco_interface_names = [
            'Ethernet1/3/1', 'Ethernet1/31.3000', 'port-channel2', 'Vlan741']
    outputs = []
    for interface in cisco_interface_names:
        name = interface_name_to_file_name(interface)
        file_name = 'cisco_show_int_' + name + '.txt'
        outputs.append(get_file_contents(file_name))
    # add incorrect interface
    cisco_interface_names.insert(2, 'etoh1/3/2')
    outputs.insert(2, '''"^\nInvalid interface format at '^' marker."''')
    cisco_task = create_fake_task(
            None, vendor_vars['Cisco Nexus'], None, 'nxos',
            check_interfaces.sanitize_interface_list, effect=outputs)
    check_interfaces.sanitize_interface_list(cisco_task, cisco_interface_names)
    assert len(cisco_task.host['interfaces']) == 4
    assert 'Ethernet1/3/2' not in cisco_task.host['interfaces']
    assert 'Vlan741' in cisco_task.host['interfaces']
