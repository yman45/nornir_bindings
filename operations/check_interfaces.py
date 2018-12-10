import re
from nornir.core.task import Result
from app_exception import UnsupportedNOS
from utils.switch_objects import SwitchInterface, IPAddress


def cisco_compact_name(int_name):
    '''Convert Cisco full interface name into abbreviated form used, for
    example, in 'show interface brief' output
    Arguments:
        * int_name - full interface name
    Returns:
        * abbreviated interface name
    '''
    if 'Ethernet' in int_name:
        return 'Eth'+int_name[8:]
    elif 'port-channel' in int_name:
        return 'Po'+int_name[12:]
    else:
        return int_name


def convert_mac_address(mac_address):
    '''Convert Cisco and Huawei notation MAC addresses into standard(?)
    representation with colons. Plus lowering case.
    Arguments:
        * mac_address - MAC address in Cisco or Huawei notation
    Returns:
        * MAC address in standard notation
    '''
    mac_address = mac_address.lower()
    if not re.match(r'^[a-f0-9]{4}(.|-)[a-f0-9]{4}(.|-)[a-f0-9]{4}$',
                    mac_address):
        raise ValueError('Unsupported or invalid MAC address format')
    mac_address = (mac_address[:2] + ':' + mac_address[2:4] + ':' +
                   mac_address[5:7] + ':' + mac_address[7:9] + ':' +
                   mac_address[10:12] + ':' + mac_address[12:])
    return mac_address


def convert_load(load_in_bits_second):
    '''Convert bits/second to gigabits/second. If result less that 0.001 (one
    megabit per second) set it to that value.
    Arguments:
        * load_in_bits_second - string describing current load in bits/sec
    Return:
        float rounded to 3rd digit describing loag in gigabits/sec
    '''
    if load_in_bits_second == '0':
        return float(load_in_bits_second)
    result = round(float(load_in_bits_second)/1000000000, 3)
    result = result if result >= 0.001 else 0.001
    return result


def check_interfaces_status(task, interface_list=None):
    '''Nornir task to get switch interfaces administrative and operational
    status. If interface list is provided, new list of
    utils.switch_objects.SwitchInterface will be generated and assigned to
    task.host['interfaces'], so existed ones would be dropped. Otherwise
    existed list in task.host['interfaces'] would be used.
    Arguments:
        * task - instance or nornir.core.task.Task
        * interface_list (defaults to None) - list of strings, which represents
            switch interface names
    Returns:
        * instance of nornir.core.task.Result
    '''
    if interface_list:
        task.host['interfaces'] = [SwitchInterface(x) for x in interface_list]
    connection = task.host.get_connection('netmiko')
    result = 'Interfaces status:\n'
    interfaces_brief_output = connection.send_command(task.host['vendor_vars'][
        'show interfaces brief'])
    for interface in task.host['interfaces']:
        if task.host['nornir_nos'] == 'nxos':
            interface_name = cisco_compact_name(interface.name)
        else:
            interface_name = interface.name
        brief_line_start = interfaces_brief_output.index(interface_name)
        # 'find' will cover end of output (last line) situations
        brief_line_end = interfaces_brief_output.find('\n', brief_line_start)
        brief_line = interfaces_brief_output[brief_line_start:brief_line_end]
        if task.host['nornir_nos'] == 'nxos':
            if ' up ' in brief_line:
                interface.admin_status = 'up'
                interface.oper_status = 'up'
            elif 'Administratively down' in brief_line:
                interface.admin_status = 'down'
                interface.oper_status = 'down'
            else:
                interface.admin_status = 'up'
                interface.oper_status = 'down'
        elif task.host['nornir_nos'] == 'huawei_vrpv8':
            phy_status = re.search(r'{}(\(.+\))?\s+(\*?(down|up))'.format(
                interface.name), brief_line).group(2)
            if phy_status == '*down':
                interface.admin_status = 'down'
                interface.oper_status = 'down'
            elif phy_status == 'down':
                interface.admin_status = 'up'
                interface.oper_status = 'down'
            else:
                interface.admin_status = 'up'
                interface.oper_status = 'up'
        else:
            raise UnsupportedNOS('task received unsupported NOS - {}'.format(
                task.host['nornir_nos']))
        result += '\tInterface {} is in {}/{} state\n'.format(
                interface.name, interface.admin_status, interface.oper_status)
    return Result(host=task.host, result=result)


def get_interfaces_ip_addresses(task, interface_list=None):
    '''Nornir task to get switch interfaces IP addresses (both IPv4 and IPv6).
    If interface list is provided, new list of
    utils.switch_objects.SwitchInterface will be generated and assigned to
    task.host['interfaces'], so existed ones would be dropped. Otherwise
    existed list in task.host['interfaces'] would be used.
    Arguments:
        * task - instance or nornir.core.task.Task
        * interface_list (defaults to None) - list of strings, which represents
            switch interface names
    Returns:
        * instance of nornir.core.task.Result
    '''
    if interface_list:
        task.host['interfaces'] = [SwitchInterface(
            x, mode='routed') for x in interface_list]
    result = 'IP addresses on interfaces:\n'
    connection = task.host.get_connection('netmiko')
    for interface in task.host['interfaces']:
        ipv4_status = connection.send_command(
            task.host['vendor_vars']['show ipv4 interface'].format(
                interface.name))
        ipv6_status = connection.send_command(
            task.host['vendor_vars']['show ipv6 interface'].format(
                interface.name))
        if task.host['nornir_nos'] == 'nxos':
            if 'IP is disabled' not in ipv4_status:
                pattern = re.compile(
                        r'IP address: '
                        r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
                        r', '
                        r'IP subnet: \d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
                        r'/(\d{1,2})( secondary)?')
                match = pattern.findall(ipv4_status)
                for address in match:
                    interface.ipv4_addresses.append(IPAddress(
                            address[0], address[1], address[2]))
            if 'IPv6 is disabled' not in ipv6_status:
                primary_address = re.search(r'IPv6 address: (\S+)',
                                            ipv6_status).group(1)
                primary_prefix_length = re.search(
                        r'IPv6 subnet:  \S+/(\d{1,3})', ipv6_status).group(1)
                link_local = re.search(r'IPv6 link-local address: (\S+)',
                                       ipv6_status).group(1)
                interface.ipv6_addresses.append(IPAddress(
                    primary_address, primary_prefix_length))
                interface.ipv6_addresses.append(IPAddress(
                    link_local, '64', True))
                sec_start = ipv6_status.find('Secondary configured addresses')
                if sec_start != -1:
                    sec_end = ipv6_status.index('IPv6 link-local address')
                    match = re.findall(r'([0-9A-Fa-f:]+)/(\d{1,3})',
                                       ipv6_status[sec_start:sec_end])
                    for address in match:
                        interface.ipv6_addresses.append(IPAddress(
                            address[0], address[1], True))
        elif task.host['nornir_nos'] == 'huawei_vrpv8':
            if 'Internet Address is' in ipv4_status:
                pattern = re.compile(r'Internet Address is '
                                     r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
                                     r'/(\d{1,2})( Sub)?')
                match = pattern.findall(ipv4_status)
                for address in match:
                    interface.ipv4_addresses.append(IPAddress(
                        address[0], address[1], address[2]))
            if 'The IPv6 address does not exist' not in ipv6_status:
                interface.ipv6_addresses.append(IPAddress(re.search(
                    r'link-local address is ([0-9A-Fa-f:]+)',
                    ipv6_status).group(1), '64', True))
                match = re.findall(
                        r'([0-9A-Fa-f:]+), subnet is [0-9A-Fa-f:]+/(\d{1,3})',
                        ipv6_status)
                for address in match:
                    # There is no primary IPv6 address concept for Huawei,
                    # unlike Cisco
                    interface.ipv6_addresses.append(IPAddress(
                        address[0], address[1], True))
        else:
            raise UnsupportedNOS('task received unsupported NOS - {}'.format(
                task.host['nornir_nos']))
        result += 'Interface {} IP addresses:\n'.format(interface.name)
        if len(interface.ipv4_addresses) == 0:
            result += '\tNo IPv4 addresses\n'
        else:
            result += '\tIPv4: {}\n'.format(', '.join(
                [str(x) for x in interface.ipv4_addresses]))
        if len(interface.ipv6_addresses) == 0:
            result += '\tNo IPv6 addresses\n'
        else:
            result += '\tIPv6: {}\n'.format(', '.join(
                [str(x) for x in interface.ipv6_addresses]))
    return Result(host=task.host, result=result)


def get_interfaces_ip_neighbors(task, interface_list=None):
    '''Nornir task to get switch interfaces IP neighbors (both IPv4 (ARP) and
    IPv6 (NDP)). If interface list is provided, new list of
    utils.switch_objects.SwitchInterface will be generated and assigned to
    task.host['interfaces'], so existed ones would be dropped. Otherwise
    existed list in task.host['interfaces'] would be used.
    Arguments:
        * task - instance or nornir.core.task.Task
        * interface_list (defaults to None) - list of strings, which represents
            switch interface names
    Returns:
        * instance of nornir.core.task.Result
    '''
    if interface_list:
        task.host['interfaces'] = [SwitchInterface(
            x, mode='routed') for x in interface_list]
    connection = task.host.get_connection('netmiko')
    result = 'IP neighbors learned on interfaces:\n'
    for interface in task.host['interfaces']:
        result += '\tInterface {} '.format(interface.name)
        if interface.mode != 'routed':
            interface.ipv4_neighbors = 0
            interface.ipv6_neighbors = 0
            result += 'Interface {} is in switched mode'.format(interface.name)
            continue
        # must use VRF name in 'non-default' VRF for Cisco, but unnecessary in
        # any case for Huawei; we force VRF usage on Cisco even for 'default'
        vrf_name = task.host['vrf_name'] if task.host[
                'vrf_name'] else 'default'
        ipv4_neighbors = connection.send_command(
            task.host['vendor_vars']['show ipv4 neighbors interface'].format(
                interface.name, vrf_name))
        ipv6_neighbors = connection.send_command(
            task.host['vendor_vars']['show ipv6 neighbors interface'].format(
                interface.name, vrf_name))
        if task.host['nornir_nos'] == 'nxos':
            search_line = r'Total number of entries:\s+(\d+)'
        elif task.host['nornir_nos'] == 'huawei_vrpv8':
            search_line = r'Dynamic:(?:\s+)?(\d+)'
        else:
            raise UnsupportedNOS('task received unsupported NOS - {}'.format(
                task.host['nornir_nos']))
        # Huawei returns empty output for 'down' interfaces
        if not ipv4_neighbors:
            interface.ipv4_neighbors = 0
        else:
            interface.ipv4_neighbors = int(re.search(
                search_line, ipv4_neighbors).group(1))
        if not ipv6_neighbors:
            interface.ipv6_neighbors = 0
        else:
            interface.ipv6_neighbors = int(re.search(
                search_line, ipv6_neighbors).group(1))
        result += 'IPv4 neighbors: {}; IPv6 neighbors: {}\n'.format(
                interface.ipv4_neighbors, interface.ipv6_neighbors)
    return Result(host=task.host, result=result)


def get_interfaces_mode(task, interface_list=None):
    '''Nornir task to get switch interfaces mode of operation, which can be
    either routed (L3) or switched (L2). If interface list is provided, new
    list of utils.switch_objects.SwitchInterface will be generated and assigned
    to task.host['interfaces'], so existed ones would be dropped. Otherwise
    existed list in task.host['interfaces'] would be used.
    Arguments:
        * task - instance or nornir.core.task.Task
        * interface_list (defaults to None) - list of strings, which represents
            switch interface names
    Returns:
        * instance of nornir.core.task.Result
    '''
    if interface_list:
        task.host['interfaces'] = [SwitchInterface(x) for x in interface_list]
    connection = task.host.get_connection('netmiko')
    result = 'Interfaces mode:\n'
    if task.host['nornir_nos'] == 'nxos':
        interfaces_brief_output = connection.send_command(task.host[
            'vendor_vars']['show interfaces brief'])
    for interface in task.host['interfaces']:
        if interface.svi or interface.subinterface:
            result += 'Interface {} mode: routed (by interface type)'.format(
                    interface.name)
            continue
        if task.host['nornir_nos'] == 'nxos':
            interface_name = cisco_compact_name(interface.name)
            brief_line_start = interfaces_brief_output.index(interface_name)
            # 'find' will cover end of output (last line) situations
            brief_line_end = interfaces_brief_output.find('\n',
                                                          brief_line_start)
            brief_line = interfaces_brief_output[
                    brief_line_start:brief_line_end]
            if 'routed' in brief_line:
                interface.mode = 'routed'
            elif 'trunk' in brief_line or 'access' in brief_line:
                interface.mode = 'switched'
            else:
                raise ValueError('Can not determine interface {} mode'.format(
                    interface.name))
        elif task.host['nornir_nos'] == 'huawei_vrpv8':
            interface_full_output = connection.send_command(task.host[
                'vendor_vars']['show interface'].format(interface.name))
            if 'Switch Port' in interface_full_output:
                interface.mode = 'switched'
            elif 'Route Port' in interface_full_output:
                interface.mode = 'routed'
            else:
                raise ValueError('Can not determine interface {} mode'.format(
                    interface.name))
        else:
            raise UnsupportedNOS('task received unsupported NOS - {}'.format(
                task.host['nornir_nos']))
        result += '\tInterface {} mode: {}'.format(interface.name,
                                                   interface.mode)
    return Result(host=task.host, result=result)


def get_interfaces_general_info(task, interface_list=None):
    '''Nornir task to get switch interfaces general information like speed,
    description, MAC address, etc. If interface list is provided, new list of
    utils.switch_objects.SwitchInterface will be generated and assigned to
    task.host['interfaces'], so existed ones would be dropped. Otherwise
    existed list in task.host['interfaces'] would be used.
    Arguments:
        * task - instance or nornir.core.task.Task
        * interface_list (defaults to None) - list of strings, which represents
            switch interface names
    Returns:
        * instance of nornir.core.task.Result
    '''
    if interface_list:
        task.host['interfaces'] = [SwitchInterface(x) for x in interface_list]
    connection = task.host.get_connection('netmiko')
    result = 'Interfaces characteristics:\n'
    for interface in task.host['interfaces']:
        interface_full_output = connection.send_command(
                task.host['vendor_vars']['show interface'].format(
                    interface.name))
        if task.host['nornir_nos'] == 'nxos':
            if 'Description:' not in interface_full_output:
                interface.description = None
            else:
                interface.description = re.search(
                    r'Description: (.+)\n', interface_full_output).group(1)
            interface.mac_address = convert_mac_address(re.search(
                r'address(?:: | is\s+)([a-z0-9.]+)\s',
                interface_full_output).group(1))
            interface.mtu = int(re.search(r'MTU (\d{4}) bytes',
                                          interface_full_output).group(1))
            if interface.svi or interface.subinterface:
                # SVIs and subinterface doesn't have speed, duplex or load
                (interface.speed, interface.duplex, interface.load_in,
                    interface.load_out) = (None, None, None, None)
                continue
            speed_and_duplex = re.search(r'(full|half)-duplex, (\d{1,3}) Gb/s',
                                         interface_full_output)
            interface.duplex = speed_and_duplex.group(1)
            interface.speed = int(speed_and_duplex.group(2))
            interface.load_in = convert_load(re.search(
                r'input rate (\d+) bits/sec,', interface_full_output).group(1))
            interface.load_out = convert_load(re.search(
                r'output rate (\d+) bits/sec,',
                interface_full_output).group(1))
        elif task.host['nornir_nos'] == 'huawei_vrpv8':
            descr = re.search(r'Description: (.+)\n', interface_full_output)
            interface.description = descr.group(1) if descr else None
            interface.mac_address = convert_mac_address(re.search(
                r'Hardware address is ([a-z0-9-]+)\s',
                interface_full_output).group(1))
            interface.mtu = int(re.search(
                r'Maximum (?:Transmit Unit|Frame Length) is (\d{4})',
                interface_full_output).group(1))
            if interface.svi or interface.subinterface:
                # SVIs and subinterface doesn't have speed, duplex or load
                (interface.speed, interface.duplex, interface.load_in,
                    interface.load_out) = (None, None, None, None)
                continue
            if interface.lag:
                interface.duplex = 'full'
                interface.speed = int(re.search(
                    r'Current BW : (\d+)Gbps,',
                    interface_full_output).group(1))
            else:
                interface.duplex = re.search(
                        r'Duplex:\s+(FULL|HALF),',
                        interface_full_output).group(1).lower()
                interface.speed = int(re.search(
                        r'Speed:\s+(\d+),',
                        interface_full_output).group(1))/1000
            interface.load_in = convert_load(re.search(
                r'input rate:? (\d+) bits/sec,',
                interface_full_output).group(1))
            interface.load_out = convert_load(re.search(
                r'output rate:? (\d+) bits/sec,',
                interface_full_output).group(1))
        else:
            raise UnsupportedNOS('task received unsupported NOS - {}'.format(
                task.host['nornir_nos']))
        result += '\tInterface {} / {}: MAC address {}, MTU {} bytes,'.format(
                interface.name, interface.description, interface.mac_address,
                interface.mtu)
        result += '\t\t{} Gb/s, {} duplex, {}/{} in/out Gb/s load\n'.format(
                interface.speed, interface.duplex, interface.load_in,
                interface.load_out)
    return Result(host=task.host, result=result)


def sanitize_interface_list(task, interface_list):
    if not interface_list:
        return Result(host=task.host, failed=True,
                      result='No valid interfaces provided')
