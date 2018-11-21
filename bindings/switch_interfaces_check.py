import json
from nornir.core import InitNornir
from nornir.core.task import Result
from nornir.plugins.functions.text import print_result
from utils.nornir_utils import nornir_set_credentials
from operations import check_interfaces
from app_exception import UnsupportedNOS


def check_switch_interfaces(task, interface_names):
    '''Nornir task that execute different subtasks to get an high level
    overview of interfaces state and characteristics on switch.
    !!!NOT COMPLETED Doesn't check for interface name to be legit.
    Didn't support multiple hosts!!!
    Arguments:
        * task - instance of nornir.core.task.Task
        * interface_names - names of interfaces to check for
    Returns:
        * instance of nornir.core.task.Result
    '''
    with open('operations/vendor_vars.json', 'r', encoding='utf-8') as jsonf:
        vendor_vars = json.load(jsonf)
    if task.host['nornir_nos'] == 'nxos':
        task.host['vendor_vars'] = vendor_vars['Cisco Nexus']
    elif task.host['nornir_nos'] == 'huawei_vrpv8':
        task.host['vendor_vars'] = vendor_vars['Huawei CE']
    else:
        raise UnsupportedNOS('{} is unsupported or bogus'.format(
            task.host['nornir_nos']))
    task.run(task=check_interfaces.check_interfaces_status,
             name='Check for interfaces operational status',
             interface_list=interface_names)
    task.run(task=check_interfaces.get_interfaces_mode,
             name='Check for interfaces mode (L2/L3)')
    task.run(task=check_interfaces.get_interfaces_general_info,
             name='Get interfaces characteristics')
    result = 'Interfaces state and characteristics:\n'
    for interface in task.host['interfaces']:
        result += '\tInterface {} with "{}" description\n'.format(
                interface.name, interface.description)
        result += '\t\t{} mode, MAC address {}, MTU {} bytes,\n'.format(
            interface.mode, interface.mac_address, interface.mtu)
        if interface.svi or interface.subinterface:
            # SVIs and subinterfaces doesn't have speed, duplex and load
            continue
        result += '\t\t{} Gb/s, {} duplex, {}/{} in/out Gb/s load\n'.format(
            interface.speed, interface.duplex, interface.load_in,
            interface.load_out)
    return Result(task.host, result=result)


if __name__ == '__main__':
    # grab hosts from inventory, execute operations and print out only topmost
    # (umbrella operation) results
    nrnr = InitNornir(config_file='config.yml')
    nrnr = nrnr.filter(name='man1-s305')
    nornir_set_credentials(nrnr)
    interface_names = input('Enter interface names > ')
    interface_list = interface_names.split(', ')
    result = nrnr.run(task=check_switch_interfaces,
                      interface_names=interface_list)
    for host in result:
        print_result(result[host][0])
