import re
import ipaddress
from nornir.core.task import Result
from app_exception import UnsupportedNOS
from utils.switch_objects import SwitchInterface, BGPNeighbor, AddressFamily


def find_vrf(task):
    '''Nornir task to detect if VRF exists on a switch. Task will fail if no
    VRF found, which prevents other tasks on same host from being executed. VRF
    name contained in task.host['vrf_name'].
    Arguments:
        * task - instance or nornir.core.task.Task
    Returns:
        * instance of nornir.core.task.Result
    '''
    connection = task.host.get_connection('netmiko')
    output = connection.send_command(task.host['vendor_vars']['show vrf'])
    if not re.search(task.host['vendor_vars']['vrf regexp'].format(
            task.host['vrf_name']), output):
        return Result(host=task.host, failed=True,
                      result='VRF {} is not exist on device'.format(
                          task.host['vrf_name']))
    else:
        return Result(host=task.host,
                      result='VRF {} configured on device'.format(
                        task.host['vrf_name']))


def get_vrf_interfaces(task):
    '''Nornir task to grab all interfaces assigned to VRF on a switch. It will
    create list of utils.switch_objects.SwitchInterface and assign it to
    task.host['interfaces'].
    Arguments:
        * task - instance or nornir.core.task.Task
    Returns:
        * instance of nornir.core.task.Result
    '''
    connection = task.host.get_connection('netmiko')
    output = connection.send_command(
            task.host['vendor_vars']['show vrf interfaces'].format(
                task.host['vrf_name']))
    if task.host['nornir_nos'] == 'nxos':
        if task.host['vrf_name'] not in output:
            interfaces_list = []
        else:
            interfaces_list = [SwitchInterface(
                x.split(' ')[0], mode='routed') for x in output.strip().split(
                    '\n')[1:]]
    elif task.host['nornir_nos'] == 'huawei_vrpv8':
        if 'Interface Number : 0' in output:
            interfaces_list = []
        else:
            start_mark = 'Interface list : '
            start = output.index(start_mark)
            interfaces_list = [SwitchInterface(
                x.strip(' ,'), mode='routed') for x in output[start+len(
                    start_mark):].strip().split('\n')]
    else:
        raise UnsupportedNOS(
                'task received unsupported NOS - {}'.format(
                    task.host['nornir_nos']))
    task.host['interfaces'] = interfaces_list
    return Result(
            host=task.host, result='Interfaces bound to VRF {}:\n\t{}'.format(
                task.host['vrf_name'], '\n\t'.join(
                    [x.name for x in interfaces_list])))


def check_vrf_bgp_neighbors(task, af='both'):
    '''Nornir task to check state of BGP sessions with neighbors and grab they
    essintial parameters (ASN, session type, routed ID and number of prefixes
    learned for IPv4 unicast and/or IPv6 unicast.
    Arguments:
        * task - instance or nornir.core.task.Task
        * af (defaults to 'both') - which AF we are interested in: both, v4 or
            v6
    Returns:
        * instance of nornir.core.task.Result
    '''
    def get_n_record(host, raw_address):
        '''Check if utils.switch_objects.BGPNeighbor instance already exist in
        task.host['bgp_neighbors'] and grab it. If not create new and assign to
        that list.
        Arguments:
            * host - instance or nornir.core.task.Host
            * raw_address - string, which represents neighbor IP address
        Returns:
            * instance of utils.switch_objects.BGPNeighbor
        '''
        address = ipaddress.ip_address(raw_address).compressed
        if address not in host['bgp_neighbors'].keys():
            neighbor = BGPNeighbor(raw_address)
            host['bgp_neighbors'][neighbor.address.compressed] = neighbor
        else:
            neighbor = host['bgp_neighbors'][address]
        return neighbor

    connection = task.host.get_connection('netmiko')
    result = 'BGP neighbors in VRF {}:\n'.format(task.host['vrf_name'])
    if 'bgp_neighbors' not in task.host.keys():
        task.host['bgp_neighbors'] = {}
    check_af_v4 = True
    check_af_v6 = True
    if af == 'v4':
        check_af_v6 = False
    elif af == 'v6':
        check_af_v4 = False
    if check_af_v4:
        v4_output = connection.send_command(task.host['vendor_vars'][
            'show bgp ipv4 vrf neighbors'].format(task.host['vrf_name']))
    else:
        v4_output = None
    if check_af_v6:
        v6_output = connection.send_command(task.host['vendor_vars'][
            'show bgp ipv6 vrf neighbors'].format(task.host['vrf_name']))
    else:
        v6_output = None
    for output, af_name in zip([v4_output, v6_output], ['v4', 'v6']):
        if task.host['nornir_nos'] == 'nxos':
            if not output or 'BGP neighbor is' not in output:
                continue
            neighbors = output.strip().split('BGP neighbor is ')
            for neighbor in neighbors:
                if not neighbor:
                    continue
                n_record = get_n_record(task.host,
                                        neighbor[:neighbor.index(',')])
                n_record.state = re.search(r'BGP state = (\w+),',
                                           neighbor).group(1).lower()
                n_record.as_number = re.search(r'remote AS (\d+(?:\.\d+)?),',
                                               neighbor).group(1)
                n_record.router_id = ipaddress.ip_address(re.search(
                    r'remote router ID (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})',
                    neighbor).group(1))
                if 'ebgp link' in neighbor[:neighbor.index('Peer index')]:
                    n_record._type = 'external'
                elif 'ibgp link' in neighbor[:neighbor.index('Peer index')]:
                    n_record._type = 'internal'
                routes_count_start = neighbor.index(
                    'For address family: IP{} Unicast'.format(af_name))
                routes_count_end = neighbor.index('sent paths',
                                                  routes_count_start)
                # +10 will retain 'sent paths' words
                routes_count = neighbor[routes_count_start:routes_count_end+10]
                new_af = AddressFamily(af_name)
                new_af.learned_routes = int(re.search(
                    r'(\d+) accepted paths', routes_count).group(1))
                new_af.sent_routes = int(re.search(
                    r'(\d+) sent paths', routes_count).group(1))
                n_record.af['ip{}'.format(af_name)] = new_af
        elif task.host['nornir_nos'] == 'huawei_vrpv8':
            if not output or 'BGP Peer is' not in output:
                continue
            neighbors = output.strip().split('BGP Peer is ')
            for neighbor in neighbors:
                if not neighbor:
                    continue
                n_record = get_n_record(task.host,
                                        neighbor[:neighbor.index(',')])
                n_record.state = re.search(r'BGP current state: (\w+),',
                                           neighbor).group(1).lower()
                n_record.as_number = re.search(r'remote AS (\d+(?:\.\d+)?)',
                                               neighbor).group(1)
                n_record.router_id = ipaddress.ip_address(re.search(
                    r'Remote router ID (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})',
                    neighbor).group(1))
                if 'EBGP link' in neighbor[:neighbor.index('BGP version')]:
                    n_record._type = 'external'
                elif 'IBGP link' in neighbor[:neighbor.index('BGP version')]:
                    n_record._type = 'internal'
                task.host['bgp_neighbors'][
                        n_record.address.compressed] = n_record
                new_af = AddressFamily(af_name)
                new_af.learned_routes = int(re.search(
                    r'Received total routes: (\d+)', neighbor).group(1))
                new_af.sent_routes = int(re.search(
                    r'Advertised total routes: (\d+)', neighbor).group(1))
                n_record.af['ip{}'.format(af_name)] = new_af
        else:
            raise UnsupportedNOS(
                    'task received unsupported NOS - {}'.format(
                        task.host['nornir_nos']))
    for neighbor in task.host['bgp_neighbors'].values():
        result += '\t{} AS {} (router ID {}) of type {} is {}'.format(
                neighbor.address, neighbor.as_number, neighbor.router_id,
                neighbor._type, neighbor.state)
        if neighbor.state != 'established':
            continue
        result += ': '
        result += ', '.join(['{} learned/sent routes: {}/{}'.format(
            x, neighbor.af[x].learned_routes, neighbor.af[x].sent_routes)
            for x in neighbor.af if neighbor.af[x]])
        result += '\n'
    return Result(host=task.host, result=result)
