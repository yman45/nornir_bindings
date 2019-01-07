import json
from nornir import InitNornir
from nornir.core.task import Result
from nornir.plugins.functions.text import print_result
from utils.nornir_utils import nornir_set_credentials
from operations import check_interfaces, check_mac_table
from app_exception import UnsupportedNOS


def check_switch_interfaces(task, interface_names):
    '''Nornir task that execute different subtasks to get an high level
    overview of interfaces state and characteristics on switch. This binding
    didn't target execution on multiple hosts (because, obiously, you supply
    interface names to it), but in some cases it can work.
    Arguments:
        * task - instance of nornir.core.task.Task
        * interface_names - names of interfaces to check for
    Returns:
        * instance of nornir.core.task.Result
    '''
    with open('operations/vendor_vars.json', 'r', encoding='utf-8') as jsonf:
        vendor_vars = json.load(jsonf)
    if task.host.platform == 'nxos':
        task.host['vendor_vars'] = vendor_vars['Cisco Nexus']
    elif task.host.platform == 'huawei_vrpv8':
        task.host['vendor_vars'] = vendor_vars['Huawei CE']
    else:
        raise UnsupportedNOS('{} is unsupported or bogus'.format(
            task.host.platform))
    task.run(task=check_interfaces.sanitize_interface_list,
             name='Check provided interface names to be valid',
             interface_list=interface_names)
    task.run(task=check_interfaces.check_interfaces_status,
             name='Check for interfaces operational status')
    task.run(task=check_interfaces.get_interfaces_mode,
             name='Check for interfaces mode (L2/L3)')
    task.run(task=check_interfaces.get_interfaces_general_info,
             name='Get interfaces characteristics')
    task.run(task=check_interfaces.get_interfaces_ip_addresses,
             name='Get interfaces IP addresses')
    task.run(task=check_interfaces.get_interfaces_ip_neighbors,
             name='Get interfaces IP neighbors (ARP/ND)')
    task.run(task=check_mac_table.get_interfaces_macs,
             name='Get number of MACs learned on interfaces')
    task.run(task=check_interfaces.get_interfaces_vlan_list,
             name='Get interfaces switchport configuration')
    task.run(task=check_interfaces.get_interfaces_vrf_binding,
             name='Check if interfaces bound to VRF')
    task.run(task=check_interfaces.find_lag_hierarchy,
             name='Discover LAG relationships')
    result = 'Interfaces state and characteristics:\n'
    for interface in task.host['interfaces']:
        result += '\tInterface {} with "{}" description\n'.format(
                interface.name, interface.description)
        result += '\t\tadmin status: {}, operational status:{}\n'.format(
                interface.admin_status, interface.oper_status)
        result += '\t\t{} mode, MAC address {}, MTU {} bytes\n'.format(
            interface.mode, interface.mac_address, interface.mtu)
        if interface.oper_status == 'up' and not (interface.svi or
                                                  interface.subinterface):
            result += '\t\t{} Gb/s, {} duplex, '.format(interface.speed,
                                                        interface.duplex)
            result += '{}/{} in/out Gb/s load\n'.format(interface.load_in,
                                                        interface.load_out)
        if interface.mode == 'routed':
            if interface.ipv4_addresses:
                result += '\t\tIPv4 addresses on interface: {}\n'.format(
                        ', '.join([str(x) for x in interface.ipv4_addresses]))
            else:
                result += '\t\tNo IPv4 addresses\n'
            if interface.ipv6_addresses:
                result += '\t\tIPv6 addresses on interface: {}\n'.format(
                        ', '.join([str(x) for x in interface.ipv6_addresses]))
            else:
                result += '\t\tNo IPv6 addresses\n'
            result += '\t\tNumber or neighbors learned (ARP/NDP): '
            result += '{}/{}\n'.format(interface.ipv4_neighbors,
                                       interface.ipv6_neighbors)
            if interface.vrf:
                result += '\t\tInterface is bound to VRF {}\n'.format(
                        interface.vrf)
        if interface.mode == 'switched' or interface.svi:
            result += '\t\tMAC addresses learned on interface: {}\n'.format(
                    interface.macs_learned)
        if interface.mode == 'switched':
            result += '\t\tVLANs configuration: {} mode, PVID - {}'.format(
                    interface.switch_mode, interface.pvid)
            if interface.switch_mode == 'trunk':
                result += ', allowed list - {}'.format(interface.vlan_list)
            result += '\n'
        if interface.lag:
            result += '\t\tLAG members are: [{}]\n'.format(', '.join(
                interface.members))
        elif not interface.svi and not interface.subinterface:
            if interface.member:
                result += '\t\tInterface is a member of LAG: {}\n'.format(
                        interface.member)
    return Result(task.host, result=result)


def execute(nornir):
    '''Execute this binding.
    Arguments:
        * nornir - instnace of nornir.core.Nornir
    Returns:
        * instance of nornir.core.task.Result
    '''
    interface_names = input('Enter interface names > ')
    return nornir.run(task=check_switch_interfaces,
                      interface_names=interface_names)


if __name__ == '__main__':
    # grab one host from inventory, execute operations and print out only
    # topmost (umbrella operation) results
    nrnr = InitNornir(config_file='config.yml')
    nrnr = nrnr.filter(name='test-host')
    nornir_set_credentials(nrnr)
    result = execute(nrnr)
    for host in result:
        print_result(result[host][0])
