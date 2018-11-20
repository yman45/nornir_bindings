from copy import copy
from utils.switch_objects import SwitchInterface


def test_interface_type_assignment():
    test_names = {
            'Eth1/26': 'physical',
            'Eth1/1/4': 'physical',
            '100GE1/0/5': 'physical',
            '40GE1/0/32:4': 'physical',
            'Eth-Trunk1.3009': 'subinterface',
            'port-channel1.17': 'subinterface',
            'Eth1/32.9': 'subinterface',
            '100GE1/0/1.1000': 'subinterface',
            'Eth-Trunk12': 'lag',
            'port-channel12': 'lag',
            'Vlanif20': 'svi',
            'Vlan315': 'svi'
            }
    switches = {
            'subinterface': False,
            'svi': False,
            'lag': False
            }
    for name, _type in test_names.items():
        interface_switches = copy(switches)
        interface = SwitchInterface(name)
        if _type is not 'physical':
            interface_switches[_type] = True
        for switch in interface_switches:
            assert getattr(interface, switch) is interface_switches[switch]
