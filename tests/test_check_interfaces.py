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


def create_test_interfaces(interface_names, output, vendor_vars, vrf_name, nos,
                           operation, file_prefix, effect_outputs=None,
                           attr_map=None):
    '''Combine create_fake_task with prepare_interfaces helper functions to
    produce task/host filled with interfaces, execute task and return list of
    interfaces back.
    Arguments:
        * interface_names - list of interface names
        * output - string with CLI output of some command, if we need single
            output
        * vendor_vars - dict with NOS CLI commands
        * vrf_name - name of VRF to test upon
        * nos - NOS name
        * operation - instance of nornir.core.task.Task which we will test
        * file_prefix - prefix to find file names to produce different host
            outputs, if we need more than one
        * effect_outputs (defaults to None) - list of outputs ready to be used
            as mock side effect
        * attr_map (defaults to None) - dict, which maps interface names to
            set of attributes and corresponding values. This values must be
            applied to interface objects before executing task.
    Returns:
        * list of utils.switch_objects.SwitchInterface associated with task
            host
    '''
    if file_prefix:
        outputs = []
        for interface in interface_names:
            name = interface_name_to_file_name(interface)
            file_name = file_prefix + name + '.txt'
            outputs.append(get_file_contents(file_name))
    elif effect_outputs:
        outputs = effect_outputs
    else:
        outputs = None
    fake_task = create_fake_task(output, vendor_vars, vrf_name, nos, operation,
                                 outputs)
    test_interfaces = prepare_interfaces(fake_task, interface_names)
    if attr_map:
        for interface in test_interfaces:
            if interface.name in attr_map:
                for key, value in attr_map[interface.name].items():
                    setattr(interface, key, value)
    operation(fake_task)
    return test_interfaces


def do_interface_checks(dicts, objs):
    '''Get dict with interface names and anticipated values for different
    attributes and list of actual interface objects. Do assert checks between
    anticipated and real values.
    Attributes:
        * dicts - dict of dicts with interface names, they attributes and
            values, like {'name': {'attr': 'value'}, {'attr': 'value'}, 'name':
            ...}
        * objs - list of utils.switch_objects.SwitchInterface
    Returns nothing
    '''
    for interface, obj in zip(dicts, objs):
        for k, v in dicts[interface].items():
            assert getattr(obj, k) == v


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


def test_check_interfaces_status_cisco(set_vendor_vars):
    vendor_vars = set_vendor_vars
    interfaces = {
            'Ethernet1/22/2':
            {'admin_status': 'down', 'oper_status': 'down'},
            'Ethernet1/25':
            {'admin_status': 'up', 'oper_status': 'up'},
            'port-channel1.3000':
            {'admin_status': 'up', 'oper_status': 'up', 'subinterface': True},
            'Vlan604':
            {'admin_status': 'up', 'oper_status': 'down', 'svi': True}
            }
    interface_objects = create_test_interfaces(
            interfaces.keys(), get_file_contents('cisco_show_int_brief.txt'),
            vendor_vars['Cisco Nexus'], None, 'nxos',
            check_interfaces.check_interfaces_status, None)
    do_interface_checks(interfaces, interface_objects)


def test_check_interfaces_status_huawei(set_vendor_vars):
    vendor_vars = set_vendor_vars
    interfaces = {
            '40GE1/0/28:1':
            {'admin_status': 'down', 'oper_status': 'down'},
            '40GE1/0/32:4':
            {'admin_status': 'up', 'oper_status': 'down'},
            'Vlanif1517':
            {'admin_status': 'up', 'oper_status': 'up'},
            'Vlanif762':
            {'admin_status': 'up', 'oper_status': 'up', 'svi': True}
            }
    interface_objects = create_test_interfaces(
            interfaces.keys(), get_file_contents('huawei_show_int_brief.txt'),
            vendor_vars['Huawei CE'], None, 'huawei_vrpv8',
            check_interfaces.check_interfaces_status, None)
    do_interface_checks(interfaces, interface_objects)


def test_get_interfaces_ip_addresses_cisco(set_vendor_vars):
    vendor_vars = set_vendor_vars
    interface_names = [
            'Ethernet1/22/2', 'Ethernet1/25', 'port-channel1.3000', 'Vlan604']
    outputs = get_ip_outputs(interface_names, 'cisco')
    (eth1_22_2_int, eth1_25_int, po1_3000_int,
     vlan604_int) = create_test_interfaces(
             interface_names, None, vendor_vars['Cisco Nexus'], None, 'nxos',
             check_interfaces.get_interfaces_ip_addresses, None,
             effect_outputs=outputs)
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


def test_get_interfaces_ip_addresses_huawei(set_vendor_vars):
    vendor_vars = set_vendor_vars
    interface_names = [
             '40GE1/0/28:1', '40GE1/0/32:4', 'Vlanif1517', 'Vlanif762']
    outputs = get_ip_outputs(interface_names, 'huawei')
    (int_40ge1_0_28_1, int_40ge1_0_32_4, int_vlanif1517,
     int_vlanif762) = create_test_interfaces(
             interface_names, None, vendor_vars['Huawei CE'], None,
             'huawei_vrpv8', check_interfaces.get_interfaces_ip_addresses,
             None, effect_outputs=outputs)
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


def test_get_interfaces_ip_neighbors_cisco_no_neighbors(set_vendor_vars):
    vendor_vars = set_vendor_vars
    task = create_fake_task('placeholder', vendor_vars['Cisco Nexus'],
                            'Galaxy', 'nxos',
                            check_interfaces.get_interfaces_ip_neighbors)
    task.host['interfaces'] = [SwitchInterface('Ethernet1/32')]
    check_interfaces.get_interfaces_ip_neighbors(task)
    assert task.host['interfaces'][0].ipv4_neighbors == 0


def test_get_interfaces_ip_neighbors_cisco(set_vendor_vars):
    vendor_vars = set_vendor_vars
    outputs = get_ip_outputs(['Ethernet1/31.3013'], 'cisco',
                             pad='_neighbors_vrf')
    task = create_fake_task(
            None, vendor_vars['Cisco Nexus'], 'Galaxy', 'nxos',
            check_interfaces.get_interfaces_ip_neighbors, effect=outputs)
    interface = prepare_interfaces(task, ['Ethernet1/31.3013'])[0]
    check_interfaces.get_interfaces_ip_neighbors(task)
    assert interface.ipv4_neighbors == 5
    assert interface.ipv6_neighbors == 3


def test_get_interfaces_ip_neighbors_huawei(set_vendor_vars):
    vendor_vars = set_vendor_vars
    outputs = get_ip_outputs(['100GE1/0/2.3000', 'Vlanif761'], 'huawei',
                             pad='_neighbors')
    task = create_fake_task(
            None, vendor_vars['Huawei CE'], 'Lasers', 'huawei_vrpv8',
            check_interfaces.get_interfaces_ip_neighbors, effect=outputs)
    int_100ge1_0_2_3000, int_vlanif761 = prepare_interfaces(
            task, ['100GE1/0/2.3000', 'Vlanif761'])
    check_interfaces.get_interfaces_ip_neighbors(task)
    assert int_100ge1_0_2_3000.ipv4_neighbors == 2
    assert int_100ge1_0_2_3000.ipv6_neighbors == 3
    assert int_vlanif761.ipv4_neighbors == 0
    assert int_vlanif761.ipv6_neighbors == 0


def test_get_interfaces_mode_cisco(set_vendor_vars):
    vendor_vars = set_vendor_vars
    interfaces = {
            'Ethernet1/22/1': {'mode': 'switched'},
            'Ethernet1/23/2': {'mode': 'switched'},
            'Ethernet1/25': {'mode': 'routed'},
            'port-channel1.3000': {'mode': 'routed'},
            'port-channel2': {'mode': 'routed'},
            'Vlan604': {'mode': 'routed'},
            }
    interface_objects = create_test_interfaces(
            interfaces.keys(), get_file_contents('cisco_show_int_brief.txt'),
            vendor_vars['Cisco Nexus'], None, 'nxos',
            check_interfaces.get_interfaces_mode, None)
    do_interface_checks(interfaces, interface_objects)


def test_get_interfaces_mode_huawei(set_vendor_vars):
    vendor_vars = set_vendor_vars
    interfaces = {
            '40GE1/0/17': {'mode': 'routed'},
            '40GE1/0/2:1': {'mode': 'switched'},
            'Eth-Trunk1.3017': {'mode': 'routed'},
            'Vlanif761': {'mode': 'routed'},
            }
    interface_objects = create_test_interfaces(
            interfaces.keys(), None, vendor_vars['Huawei CE'], None,
            'huawei_vrpv8', check_interfaces.get_interfaces_mode,
            'huawei_show_int_')
    do_interface_checks(interfaces, interface_objects)
    vendor_vars = set_vendor_vars


def test_get_interfaces_general_info_cisco(set_vendor_vars):
    vendor_vars = set_vendor_vars
    interfaces = {
            'Ethernet1/3/1':
            {'description': None, 'mac_address': '74:a0:2f:4c:b6:50', 'mtu':
                1500, 'speed': 10, 'duplex': 'full', 'load_in': 0.005,
                'load_out': 0.016},
            'Ethernet1/31.3000':
            {'description': None, 'mac_address': '88:1d:fc:ef:48:3c', 'mtu':
                9000, 'speed': None, 'duplex': None, 'load_in': None,
                'load_out': None},
            'port-channel2':
            {'description': 'leaf-3x4 port-channel3', 'mac_address':
                '74:a0:2f:4c:b6:81', 'mtu': 9000, 'speed': 40, 'duplex':
                'full', 'load_in': 1.178, 'load_out': 1.385},
            'Vlan741':
            {'description': None, 'mac_address': '74:a0:2f:4c:b6:81', 'mtu':
                9000, 'speed': None, 'duplex': None, 'load_in': None,
                'load_out': None}
            }
    up_map = {'Ethernet1/3/1': {'oper_status': 'up'},
              'port-channel2': {'oper_status': 'up'}}
    interface_objects = create_test_interfaces(
            interfaces.keys(), None, vendor_vars['Cisco Nexus'], None, 'nxos',
            check_interfaces.get_interfaces_general_info, 'cisco_show_int_',
            attr_map=up_map)
    do_interface_checks(interfaces, interface_objects)


def test_get_interfaces_general_info_huawei(set_vendor_vars):
    vendor_vars = set_vendor_vars
    interfaces = {
            '40GE1/0/2:1':
            {'description': '\\', 'mac_address': '30:d1:7e:e3:f9:61', 'mtu':
                9712, 'speed': None, 'duplex': None, 'load_in': None,
                'load_out': None},
            '10GE1/0/2.3013':
            {'description': None, 'mac_address': 'bc:9c:31:c6:e2:c2', 'mtu':
                9000, 'speed': None, 'duplex': None, 'load_in': None,
                'load_out': None},
            'Eth-Trunk0':
            {'description': None, 'mac_address': 'ac:4e:91:46:35:91', 'mtu':
                9216, 'speed': 2, 'duplex': 'full', 'load_in': 0.001,
                'load_out': 0.001},
            'Vlanif761':
            {'description': None, 'mac_address': '30:d1:7e:e3:f9:67', 'mtu':
                9000, 'speed': None, 'duplex': None, 'load_in': None,
                'load_out': None}
            }
    up_map = {'Eth-Trunk0': {'oper_status': 'up'}}
    interface_objects = create_test_interfaces(
            interfaces.keys(), None, vendor_vars['Huawei CE'], None,
            'huawei_vrpv8', check_interfaces.get_interfaces_general_info,
            'huawei_show_int_', attr_map=up_map)
    do_interface_checks(interfaces, interface_objects)


def test_sanitize_interface_list_no_interface():
    task = create_fake_task(None, None, None, None,
                            check_interfaces.sanitize_interface_list)
    result = check_interfaces.sanitize_interface_list(task, '')
    assert result.failed is True


def test_sanitize_interface_list_huawei(set_vendor_vars):
    vendor_vars = set_vendor_vars
    interface_names = [
            '40GE1/0/2:1', '10GE1/0/2.3013', 'Eth-Trunk0', 'Vlanif761']
    outputs = []
    for interface in interface_names:
        name = interface_name_to_file_name(interface)
        file_name = 'huawei_show_int_' + name + '.txt'
        outputs.append(get_file_contents(file_name))
    # add incorrect interface
    interface_names.insert(2, '24GE1/77')
    outputs.insert(2, '''"^\nError: Wrong parameter found at '^' position."''')
    task = create_fake_task(
            None, vendor_vars['Huawei CE'], None, 'huawei_vrpv8',
            check_interfaces.sanitize_interface_list, effect=outputs)
    check_interfaces.sanitize_interface_list(task, ', '.join(interface_names))
    assert len(task.host['interfaces']) == 4
    assert '24GE1/77' not in [x.name for x in task.host['interfaces']]
    assert 'Eth-Trunk0' in [x.name for x in task.host['interfaces']]


def test_sanitize_interface_list_cisco(set_vendor_vars):
    vendor_vars = set_vendor_vars
    interface_names = [
            'Ethernet1/3/1', 'Ethernet1/31.3000', 'port-channel2', 'Vlan741']
    outputs = []
    for interface in interface_names:
        name = interface_name_to_file_name(interface)
        file_name = 'cisco_show_int_' + name + '.txt'
        outputs.append(get_file_contents(file_name))
    # add incorrect interface
    interface_names.insert(2, 'etoh1/3/2')
    outputs.insert(2, '''"^\nInvalid interface format at '^' marker."''')
    task = create_fake_task(
            None, vendor_vars['Cisco Nexus'], None, 'nxos',
            check_interfaces.sanitize_interface_list, effect=outputs)
    check_interfaces.sanitize_interface_list(task, ', '.join(interface_names))
    assert len(task.host['interfaces']) == 4
    assert 'Ethernet1/3/2' not in [x.name for x in task.host['interfaces']]
    assert 'Vlan741' in [x.name for x in task.host['interfaces']]


def test_get_interfaces_vlan_list_cisco(set_vendor_vars):
    vendor_vars = set_vendor_vars
    interfaces = {
            'Ethernet1/22/2': {'vlan_list': [222], 'switch_mode': 'access'},
            'Ethernet1/29': {'vlan_list': None, 'switch_mode': None},
            'Ethernet1/6/3': {'vlan_list': [222, 517, 724, 799],
                              'switch_mode': 'trunk'}
            }
    interface_objects = create_test_interfaces(
            interfaces.keys(), None, vendor_vars['Cisco Nexus'], None, 'nxos',
            check_interfaces.get_interfaces_vlan_list,
            'cisco_show_int_switchport_')
    do_interface_checks(interfaces, interface_objects)


def test_get_interfaces_vlan_list_huawei(set_vendor_vars):
    vendor_vars = set_vendor_vars
    interfaces = {
            '10GE1/0/14':
            {'vlan_list': [642], 'switch_mode': 'access', 'pvid': 642},
            '100GE1/0/3':
            {'vlan_list': None, 'switch_mode': None, 'pvid': None},
            '10GE1/0/7':
            {'vlan_list':
                [507, 599, 614, 622, 670, 671, 672, 673, 1333, 1444, 1556],
                'switch_mode': 'trunk', 'pvid': 670}
            }
    interface_objects = create_test_interfaces(
            interfaces.keys(), None, vendor_vars['Huawei CE'], None,
            'huawei_vrpv8', check_interfaces.get_interfaces_vlan_list,
            'huawei_show_int_switchport_')
    do_interface_checks(interfaces, interface_objects)


def test_get_interfaces_vrf_binding_cisco(set_vendor_vars):
    vendor_vars = set_vendor_vars
    interfaces = {
            'Vlan215': {'vrf': 'Star'},
            'Ethernet1/31.200': {'vrf': 'World'},
            'Ethernet1/32.144': {'vrf': 'World'},
            'Vlan1222': {'vrf': 'Galaxy'},
            'Vlan1': {'vrf': 'default'},
            'Ethernet1/26': {'vrf': 'default'},
            'mgmt0': {'vrf': 'management'},
            'Ethernet1/5/3': {'vrf': None}
            }
    mode_map = {'Ethernet1/26': {'mode': 'routed'},
                'Ethernet1/5/3': {'mode': 'routed'},
                'mgmt0': {'mode': 'routed'}
                }
    interface_objects = create_test_interfaces(
            interfaces.keys(),
            get_file_contents('cisco_show_vrf_interfaces_all.txt'),
            vendor_vars['Cisco Nexus'], None, 'nxos',
            check_interfaces.get_interfaces_vrf_binding, None,
            attr_map=mode_map)
    do_interface_checks(interfaces, interface_objects)


def test_get_interfaces_vrf_binding_huawei(set_vendor_vars):
    vendor_vars = set_vendor_vars
    interfaces = {
            'Vlanif334': {'vrf': 'Star'},
            'Vlanif422': {'vrf': 'Star'},
            '100GE1/0/4.215': {'vrf': 'Star'},
            '100GE1/0/6': {'vrf': 'Star'},
            'Vlanif516': {'vrf': 'Galaxy'},
            '10GE1/0/32': {'vrf': 'Galaxy'},
            '10GE1/0/5:4': {'vrf': None}
            }
    mode_map = {'100GE1/0/6': {'mode': 'routed'},
                '10GE1/0/32': {'mode': 'routed'},
                '10GE1/0/5:4': {'mode': 'routed'}
                }
    interface_objects = create_test_interfaces(
            interfaces.keys(),
            get_file_contents('huawei_show_vrf_interfaces_all.txt'),
            vendor_vars['Huawei CE'], None, 'huawei_vrpv8',
            check_interfaces.get_interfaces_vrf_binding, None,
            attr_map=mode_map)
    do_interface_checks(interfaces, interface_objects)


def test_find_lag_hierarchy_cisco(set_vendor_vars):
    vendor_vars = set_vendor_vars
    interfaces = {
            'port-channel1': {'members': ['Ethernet1/32']},
            'port-channel2': {'members': ['Ethernet1/31']},
            'Ethernet1/31': {'member': 'port-channel2'},
            'Ethernet1/32': {'member': 'port-channel1'}
            }
    interface_objects = create_test_interfaces(
            interfaces.keys(),
            get_file_contents('cisco_show_int_brief.txt'),
            vendor_vars['Cisco Nexus'], None, 'nxos',
            check_interfaces.find_lag_hierarchy, None)
    do_interface_checks(interfaces, interface_objects)


def test_find_lag_hierarchy_huawei(set_vendor_vars):
    vendor_vars = set_vendor_vars
    interfaces = {
            'Eth-Trunk1': {'members': ['40GE1/0/17', '40GE1/0/19']},
            'Eth-Trunk2': {'members': ['40GE1/0/18', '40GE1/0/20']},
            '40GE1/0/17': {'member': 'Eth-Trunk1'},
            '40GE1/0/18': {'member': 'Eth-Trunk2'},
            '40GE1/0/19': {'member': 'Eth-Trunk1'},
            '40GE1/0/20': {'member': 'Eth-Trunk2'},
            }
    interface_objects = create_test_interfaces(
            interfaces.keys(),
            get_file_contents('huawei_show_int_brief.txt'),
            vendor_vars['Huawei CE'], None, 'huawei_vrpv8',
            check_interfaces.find_lag_hierarchy, None)
    do_interface_checks(interfaces, interface_objects)


def test_find_lag_hierarchy_cisco_no_lag(set_vendor_vars):
    vendor_vars = set_vendor_vars
    interfaces = {
            'Ethernet1/31': {'member': None},
            'Ethernet1/32': {'member': None}
            }
    interface_objects = create_test_interfaces(
            interfaces.keys(),
            get_file_contents('cisco_show_int_brief_no_lag.txt'),
            vendor_vars['Cisco Nexus'], None, 'nxos',
            check_interfaces.find_lag_hierarchy, None)
    do_interface_checks(interfaces, interface_objects)


def test_find_lag_hierarchy_huawei_no_lag(set_vendor_vars):
    vendor_vars = set_vendor_vars
    interfaces = {
            '40GE1/0/18': {'member': None},
            '40GE1/0/5': {'member': None},
            }
    interface_objects = create_test_interfaces(
            interfaces.keys(),
            get_file_contents('huawei_show_int_brief_no_lag.txt'),
            vendor_vars['Huawei CE'], None, 'huawei_vrpv8',
            check_interfaces.find_lag_hierarchy, None)
    do_interface_checks(interfaces, interface_objects)
