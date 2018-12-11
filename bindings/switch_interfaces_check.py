import json
from nornir.core import InitNornir
from nornir.core.task import Result
from nornir.plugins.functions.text import print_result
from utils.nornir_utils import nornir_set_credentials
from operations import check_interfaces
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
    if task.host['nornir_nos'] == 'nxos':
        task.host['vendor_vars'] = vendor_vars['Cisco Nexus']
    elif task.host['nornir_nos'] == 'huawei_vrpv8':
        task.host['vendor_vars'] = vendor_vars['Huawei CE']
    else:
        raise UnsupportedNOS('{} is unsupported or bogus'.format(
            task.host['nornir_nos']))
    task.run(task=check_interfaces.sanitize_interface_list,
             name='Check provided interface names to be valid',
             interface_list=interface_names)
    task.run(task=check_interfaces.check_interfaces_status,
             name='Check for interfaces operational status')
    task.run(task=check_interfaces.get_interfaces_mode,
             name='Check for interfaces mode (L2/L3)')
    task.run(task=check_interfaces.get_interfaces_general_info,
             name='Get interfaces characteristics')
    result = 'Interfaces state and characteristics:\n'
    for interface in task.host['interfaces']:
        result += '\tInterface {} with "{}" description\n'.format(
                interface.name, interface.description)
        result += '\t\tadmin status: {}, operational status:{}\n'.format(
                interface.admin_status, interface.oper_status)
        result += '\t\t{} mode, MAC address {}, MTU {} bytes'.format(
            interface.mode, interface.mac_address, interface.mtu)
        if interface.svi or interface.subinterface:
            # SVIs and subinterfaces doesn't have speed, duplex and load
            result += '\n'
            continue
        result += ',\n\t\t{} Gb/s, {} duplex, {}/{} in/out Gb/s load\n'.format(
            interface.speed, interface.duplex, interface.load_in,
            interface.load_out)
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
