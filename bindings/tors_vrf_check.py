import json
from nornir.core import InitNornir
from nornir.core.task import Result
from nornir.plugins.functions.text import print_result
from utils.nornir_utils import nornir_set_credentials
from tasks import check_vrf_status, check_interfaces, check_mac_table
from app_exception import UnsupportedNOS


def check_vrf(task, vrf_name):
    '''Nornir task that execute different subtasks to get an high level
    overview of VRF operational state on a ToR switch. Criterias for final
    rating are opinionated. In theory task may run well on other types of
    switches.
    Arguments:
        * task - instance of nornir.core.task.Task
        * vrf_name - name of VRF to check for
    Returns:
        * instance of nornir.core.task.Result
    '''
    with open('tasks/vendor_vars.json', 'r', encoding='utf-8') as jsonf:
        vendor_vars = json.load(jsonf)
    if task.host['nornir_nos'] == 'nxos':
        task.host['vendor_vars'] = vendor_vars['Cisco Nexus']
        nos_name = 'Cisco NX-OS'
    elif task.host['nornir_nos'] == 'huawei_vrpv8':
        task.host['vendor_vars'] = vendor_vars['Huawei CE']
        nos_name = 'Huawei VRPv8'
    else:
        raise UnsupportedNOS('{} is unsupported or bogus'.format(
            task.host['nornir_nos']))
    task.host['vrf_name'] = vrf_name
    task.run(task=check_vrf_status.find_vrf,
             name='Check if VRF exists on node')
    task.run(task=check_vrf_status.get_vrf_interfaces,
             name='Get VRF interfaces list')
    task.run(task=check_interfaces.check_interfaces_status,
             name='Check interfaces status for VRF')
    task.run(task=check_interfaces.get_interfaces_ip_addresses,
             name='Gather IP addresses for interfaces in VRF')
    task.run(task=check_interfaces.get_interfaces_ip_neighbors,
             name='Gather IP neighbors for interfaces in VRF')
    task.run(task=check_mac_table.get_interfaces_macs,
             name='Gather learned MAC for interfaces in VRF')
    task.run(task=check_vrf_status.check_vrf_bgp_neighbors,
             name='Get BGP neighbors in VRF and they state')
    result = 'Host {} running {}, VRF {} status:\n'.format(
            task.host.name, nos_name, task.host['vrf_name'])
    oper_up_interfaces = [x for x in task.host[
        'interfaces'] if x.oper_status == 'up']
    result += '\t{} interfaces in VRF, {} of them operationally up\n'.format(
            len(task.host['interfaces']), len(oper_up_interfaces))
    ipv4_addresses = []
    ipv6_addresses = []
    for interface in task.host['interfaces']:
        ipv4_addresses.extend(interface.ipv4_addresses)
        ipv6_addresses.extend([x for x in interface.ipv6_addresses
                              if not x.address.is_link_local])
    result += '\t{}/{} v4/v6 addresses present (except link-locals)\n'.format(
            len(ipv4_addresses), len(ipv6_addresses))
    v4_neighbors = sum([x.ipv4_neighbors for x in task.host['interfaces']])
    v6_neighbors = sum([x.ipv6_neighbors for x in task.host['interfaces']])
    result += '\t{}/{} v4/v6 neighbors learned on interfaces\n'.format(
            v4_neighbors, v6_neighbors)
    learned_macs = sum([x.macs_learned for x in task.host['interfaces']])
    result += '\t{} MAC addresses learned in VRF VLANs\n'.format(learned_macs)
    num_neighbors = len(task.host['bgp_neighbors'])
    established_neighbors = len([x for x in task.host[
        'bgp_neighbors'].values() if x.state == 'established'])
    neighbors_with_prefixes = []
    for neighbor in task.host['bgp_neighbors'].values():
        if neighbor.af['ipv4'] and neighbor.af['ipv4'].learned_routes:
            neighbors_with_prefixes.append(neighbor)
            continue
        elif neighbor.af['ipv6'] and neighbor.af['ipv6'].learned_routes:
            neighbors_with_prefixes.append(neighbor)
    result += '\t{} BGP neighbors configured, {} of them '.format(
        num_neighbors, established_neighbors)
    result += 'in established state, {} of them sent prefixes\n'.format(
        len(neighbors_with_prefixes))
    if not any([num_neighbors, established_neighbors,
                neighbors_with_prefixes]):
        overall_status = 'No VRF connectivity'
    elif not learned_macs:
        overall_status = 'No MACs learned, probably no devices connected'
    elif not any([v4_neighbors, v6_neighbors]):
        overall_status = 'No IP neighbors learned, devices may not be \
                properly configured'
    elif not any([ipv4_addresses, ipv6_addresses]):
        overall_status = 'No IP address configured in VRF'
    elif not oper_up_interfaces:
        overall_status = 'All interfaces down'
    elif not task.host['interfaces']:
        overall_status = 'No interfaces configured'
    else:
        overall_status = 'VRF looks good!'
    result += overall_status
    return Result(task.host, result=result)


if __name__ == '__main__':
    # grab hosts from inventory, execute binding and print out only topmost
    # (umbrella task) results
    nrnr = InitNornir(config_file='config.yml')
    nornir_set_credentials(nrnr)
    vrf_name = input('Enter VRF name > ')
    result = nrnr.run(task=check_vrf, vrf_name=vrf_name)
    for host in result:
        print_result(result[host][0])
