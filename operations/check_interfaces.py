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
    connection = task.host.get_connection('netmiko', None)
    result = 'Interfaces status:\n'
    interfaces_brief_output = connection.send_command(task.host['vendor_vars'][
        'show interfaces brief'])
    for interface in task.host['interfaces']:
        if task.host.platform == 'nxos':
            interface_name = cisco_compact_name(interface.name)
        else:
            interface_name = interface.name
        brief_line_start = interfaces_brief_output.index(interface_name)
        # 'find' will cover end of output (last line) situations
        brief_line_end = interfaces_brief_output.find('\n', brief_line_start)
        brief_line = interfaces_brief_output[brief_line_start:brief_line_end]
        if task.host.platform == 'nxos':
            if ' up ' in brief_line:
                interface.admin_status = 'up'
                interface.oper_status = 'up'
            elif 'Administratively down' in brief_line:
                interface.admin_status = 'down'
                interface.oper_status = 'down'
            else:
                interface.admin_status = 'up'
                interface.oper_status = 'down'
        elif task.host.platform == 'huawei_vrpv8':
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
                task.host.platform))
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
    connection = task.host.get_connection('netmiko', None)
    for interface in task.host['interfaces']:
        ipv4_status = connection.send_command(
            task.host['vendor_vars']['show ipv4 interface'].format(
                interface.name))
        ipv6_status = connection.send_command(
            task.host['vendor_vars']['show ipv6 interface'].format(
                interface.name))
        if task.host.platform == 'nxos':
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
        elif task.host.platform == 'huawei_vrpv8':
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
                task.host.platform))
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
    connection = task.host.get_connection('netmiko', None)
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
        vrf_name = task.host.get('vrf_name', 'default')
        ipv4_neighbors = connection.send_command(
            task.host['vendor_vars']['show ipv4 neighbors interface'].format(
                interface.name, vrf_name))
        ipv6_neighbors = connection.send_command(
            task.host['vendor_vars']['show ipv6 neighbors interface'].format(
                interface.name, vrf_name))
        if task.host.platform == 'nxos':
            search_line = r'Total number of entries:\s+(\d+)'
        elif task.host.platform == 'huawei_vrpv8':
            search_line = r'Dynamic:(?:\s+)?(\d+)'
        else:
            raise UnsupportedNOS('task received unsupported NOS - {}'.format(
                task.host.platform))
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
    connection = task.host.get_connection('netmiko', None)
    result = 'Interfaces mode:\n'
    if task.host.platform == 'nxos':
        interfaces_brief_output = connection.send_command(task.host[
            'vendor_vars']['show interfaces brief'])
    for interface in task.host['interfaces']:
        if interface.svi or interface.subinterface:
            result += 'Interface {} mode: routed (by interface type)'.format(
                    interface.name)
            continue
        if task.host.platform == 'nxos':
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
        elif task.host.platform == 'huawei_vrpv8':
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
                task.host.platform))
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
    connection = task.host.get_connection('netmiko', None)
    result = 'Interfaces characteristics:\n'
    for interface in task.host['interfaces']:
        interface_full_output = connection.send_command(
                task.host['vendor_vars']['show interface'].format(
                    interface.name))
        if task.host.platform == 'nxos':
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
            if getattr(interface, 'oper_status', 'down') == 'down' or \
                    interface.svi or interface.subinterface:
                # SVIs and subinterface doesn't have speed, duplex or load; and
                # this attributes has no meaningful values on down interfaces
                # if 'oper_status' was not set, let's consider it's down
                (interface.speed, interface.duplex, interface.load_in,
                    interface.load_out) = (None, None, None, None)
                continue
            # as it can be full or Full duplex - ignore case
            speed_and_duplex = re.search(r'(full|half)-duplex, (\d{1,3}) gb/s',
                                         interface_full_output, flags=re.I)
            interface.duplex = speed_and_duplex.group(1)
            interface.speed = int(speed_and_duplex.group(2))
            interface.load_in = convert_load(re.search(
                r'input rate (\d+) bits/sec,', interface_full_output).group(1))
            interface.load_out = convert_load(re.search(
                r'output rate (\d+) bits/sec,',
                interface_full_output).group(1))
        elif task.host.platform == 'huawei_vrpv8':
            descr = re.search(r'Description: (.+)\n', interface_full_output)
            interface.description = descr.group(1) if descr else None
            interface.mac_address = convert_mac_address(re.search(
                r'Hardware address is ([a-z0-9-]+)\s',
                interface_full_output).group(1))
            interface.mtu = int(re.search(
                r'Maximum (?:Transmit Unit|Frame Length) is (\d{4})',
                interface_full_output).group(1))
            if getattr(interface, 'oper_status', 'down') == 'down' or \
                    interface.svi or interface.subinterface:
                # SVIs and subinterface doesn't have speed, duplex or load; and
                # this attributes has no meaningful values on down interfaces
                # if 'oper_status' was not set, let's consider it's down
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
                task.host.platform))
        result += '\tInterface {} / {}: MAC address {}, MTU {} bytes,'.format(
                interface.name, interface.description, interface.mac_address,
                interface.mtu)
        result += '\t\t{} Gb/s, {} duplex, {}/{} in/out Gb/s load\n'.format(
                interface.speed, interface.duplex, interface.load_in,
                interface.load_out)
    return Result(host=task.host, result=result)


def sanitize_interface_list(task, interface_list):
    '''Nornir task to clean up interface list, bound to task host or provided
    separately as an argument. User input interface names, which may be
    incorrect (misspeled or non existent on a switch) or in shortened form.
    This task will remove incorrect names and expand correct ones into full
    form. If interface list is provided, new list of
    utils.switch_objects.SwitchInterface will be generated and assigned
    to task.host['interfaces'], so existed ones would be dropped. Otherwise
    existed list in task.host['interfaces'] would be used.
    Arguments:
        * task - instance or nornir.core.task.Task
        * interface_list (defaults to None) - list of strings, which represents
            switch interface names
    Returns:
        * instance of nornir.core.task.Result
    '''
    if not interface_list:
        return Result(host=task.host, failed=True,
                      result='No interfaces provided')
    interface_list = [x.strip() for x in interface_list.split(',')]
    clean_interface_list = []
    for interface in interface_list:
        connection = task.host.get_connection('netmiko', None)
        show_interface = connection.send_command(
                task.host['vendor_vars']['show interface'].format(interface))
        # interface names can be found in a similar way for both NX-OS and
        # VRPv8, at least for now
        if ('invalid interface format' not in show_interface.lower() and
                'error: wrong parameter' not in show_interface.lower()):
            clean_interface_list.append(show_interface.split(' ')[0])
    if len(clean_interface_list) == 0:
        return Result(host=task.host, failed=True,
                      result='No valid interface names found')
    else:
        task.host['interfaces'] = [SwitchInterface(
            x) for x in clean_interface_list]
        return Result(
            host=task.host,
            result='{} interfaces found to be valid ot of {} provided'.format(
                len(clean_interface_list), len(interface_list)))


def get_interfaces_vlan_list(task, interface_list=None):
    '''Nornir task to get switch interfaces VLAN list and switching mode. Trunk
    and access modes are supported as of now. In any case PVID grabbed, which
    is access VLAN for access interface and native VLAN for trunk, and for
    trunks allowed VLAN list also gathered. If interface list is provided, new
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
    def int_not_switching(interface):
        '''Set switching attributes to None if interface in routed mode.
        Arguments:
            * interface - instance of utils.SwitchInterface
        Returns string that describes the result, i.e. 'interface not
            switching'
        '''
        interface.switch_mode = None
        interface.pvid = None
        interface.vlan_list = None
        return '\tInterface {} is not switching'.format(interface.name)

    def deaggregate_vlans(vlan_list, separator=' '):
        '''Translate string with VLAN numbers and ranges to list of integers.
        Arguments:
            * vlan_list - string that represents VLAN list, grabbed out of
                switch
            * separator (defaults to ' ') - character, that separates VLAN
                numbers on the list
        Returns list of integers
        '''
        new_list = []
        for num in vlan_list.strip().split(separator):
            # we grub newline characters on Huawei
            if not num or num == '\n':
                continue
            elif '-' not in num:
                new_list.append(int(num))
            else:
                new_list.extend(range(int(num.split('-')[0]),
                                      int(num.split('-')[1])+1))
        return new_list

    if interface_list:
        task.host['interfaces'] = [SwitchInterface(x) for x in interface_list]
    connection = task.host.get_connection('netmiko', None)
    result = 'Interfaces switching attributes:\n'
    for interface in task.host['interfaces']:
        if interface.mode != 'switched':
            result += int_not_switching(interface)
            continue
        switchport_output = connection.send_command(
                task.host['vendor_vars']['show interface switchport'].format(
                    interface.name))
        if task.host.platform == 'nxos':
            if 'switchport: disabled' in switchport_output.lower():
                result += int_not_switching(interface)
                continue
            interface.switch_mode = re.search(
                r'Operational Mode: (trunk|access)',
                switchport_output).group(1)
            if interface.switch_mode == 'access':
                interface.pvid = int(re.search(
                    r'Access Mode VLAN: (\d{1,4})',
                    switchport_output).group(1))
                interface.vlan_list = [interface.pvid]
            elif interface.switch_mode == 'trunk':
                interface.pvid = int(re.search(
                    r'Trunking Native Mode VLAN: (\d{1,4})',
                    switchport_output).group(1))
                interface.vlan_list = deaggregate_vlans(re.search(
                    r'Trunking VLANs Allowed: ([0-9,-]+)',
                    switchport_output).group(1), separator=',')
        elif task.host.platform == 'huawei_vrpv8':
            # Huawei return nothing for non switched port
            if not switchport_output:
                result += int_not_switching(interface)
                continue
            # we need re.S because long VLAN list will be separated by newlines
            vlan_regex = re.compile(r'''
            (?:\d{1,3})?GE\d{1,2}/\d{1,2}/\d{1,2}(?::\d)?\s+# interface name
            (access|trunk)\s+# switchport type
            (\d{1,4})\s+# PVID
            ((?:\d|--).*)# Allowed VLAN list
            ''', re.X | re.S)
            vlan_search = vlan_regex.search(switchport_output)
            interface.switch_mode = vlan_search.group(1)
            interface.pvid = int(vlan_search.group(2))
            if interface.switch_mode == 'access':
                interface.vlan_list = [interface.pvid]
            elif interface.switch_mode == 'trunk':
                interface.vlan_list = deaggregate_vlans(vlan_search.group(3))
        else:
            raise UnsupportedNOS('task received unsupported NOS - {}'.format(
                task.host.platform))
        result += '\tInterface {} is in {} mode, PVID is {}, '.format(
                interface.name, interface.switch_mode, str(interface.pvid))
        result += 'allowed VLANs: {}\n'.format(', '.join(str(
            interface.vlan_list)))
    return Result(host=task.host, result=result)


def get_interfaces_vrf_binding(task, interface_list=None):
    '''Nornir task to identify if interfaces bound to any VRF instance. If
    interface is in switched mode or not bound to any VRF it's vrf attribute
    will be set to None.  If interface list is provided, new list of
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
    connection = task.host.get_connection('netmiko', None)
    result = 'Interfaces to VRF bindings:\n'
    vrf_interfaces = connection.send_command(
            task.host['vendor_vars']['show vrf interfaces'].format(''))
    if task.host.platform == 'nxos':
        vrf_interfaces = '\n'.join(vrf_interfaces.strip().split('\n')[1:])
        refind = re.findall(
                r'([0-9A-Za-z/:.]+)\s+([0-9A-Za-z_:.-]+)\s+(\d+|N/A)',
                vrf_interfaces)
        vrf_bind_map = {m[0]: m[1] for m in refind}
    elif task.host.platform == 'huawei_vrpv8':
        vrf_bind_map = {}
        vrfs = vrf_interfaces.split('VPN-Instance Name and ID')[1:]
        for vrf in vrfs:
            vrf_name = vrf[vrf.index(':')+1:vrf.index(',')].strip()
            if not re.search(r'interface number\s*:\s*0', vrf, flags=re.I):
                interfaces_list = vrf[vrf.index(
                    'Interface list : ')+17:].split('\n')
            else:
                interfaces_list = []
            vrf_bind_map.update({interface.strip(
                ', '): vrf_name for interface in interfaces_list})
    else:
        raise UnsupportedNOS('task received unsupported NOS - {}'.format(
            task.host.platform))
    for interface in task.host['interfaces']:
        if interface.mode == 'switched':
            interface.vrf = None
            result += '\tInterface {} is swithed (L2)\n'.format(interface.name)
            continue
        if interface.name in vrf_bind_map:
            interface.vrf = vrf_bind_map[interface.name]
            result += '\tInterface {} bound to VRF {}\n'.format(interface.name,
                                                                interface.vrf)
        else:
            interface.vrf = None
            result += '\tInterface {} is not bound to any VRF\n'.format(
                    interface.name)
    return Result(host=task.host, result=result)


def find_lag_hierarchy(task, interface_list=None):
    '''Nornir task to identify LAG relationship, or which interface is member
    of which LAG. For LAG list of members recorded, or just empty list. For
    physical interfaces it's either a string (LAG inteface name) or None. If
    interface list is provided, new list of
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
    connection = task.host.get_connection('netmiko', None)
    result = 'LAG interfaces relationship:\n'
    int_brief_output = connection.send_command(
            task.host['vendor_vars']['show interfaces brief'])
    hier = {}
    if task.host.platform == 'nxos':
        in_lag_ints = re.findall(r'^(Eth[0-9/]+).+(\d+)$', int_brief_output,
                                 re.M)
        for match in in_lag_ints:
            lag_name = 'port-channel' + match[1]
            if lag_name not in hier:
                hier[lag_name] = []
            hier[lag_name].append(match[0].replace('Eth', 'Ethernet'))
    elif task.host.platform == 'huawei_vrpv8':
        lags_start = int_brief_output.find('Eth-Trunk')
        if lags_start != -1:
            for line in int_brief_output[lags_start:].split('\n'):
                if line.startswith('Eth-Trunk'):
                    lag = line.split(' ')[0]
                    hier[lag] = []
                elif line.startswith(' '):
                    hier[lag].append(line.strip().split(' ')[0])
                else:
                    break
    else:
        raise UnsupportedNOS('task received unsupported NOS - {}'.format(
            task.host.platform))
    for int_ in task.host['interfaces']:
        if int_.svi or int_.subinterface:
            result += "\tInterface {} can't be in LAG\n".format(int_.name)
            continue
        elif int_.lag:
            int_.members = hier[int_.name] if int_.name in hier else []
            result += "\tLAG {} has members {}\n".format(int_.name,
                                                         int_.members)
        else:
            int_.member = None
            for lag in hier:
                if int_.name in hier[lag]:
                    int_.member = lag
                    break
            if int_.member:
                result += "\tInterface {} is member of {}".format(int_.name,
                                                                  int_.member)
            else:
                result += "\tInterface {} is not member of any LAG".format(
                        int_.name)
    if not hier:
        result = 'No LAG present on a device'
    return Result(host=task.host, result=result)


def identify_breakout_ports(task, interface_list=None):
    '''Nornir task to identify interfaces created by breakout. Such state
    identified by interface name. For NX-OS there will be 2 '/' symbols, for
    VRPv8 there will be ':' symbol.
    Arguments:
        * task - instance or nornir.core.task.Task
        * interface_list (defaults to None) - list of strings, which represents
            switch interface names
    Returns:
        * instance of nornir.core.task.Result
    '''
    if interface_list:
        task.host['interfaces'] = [SwitchInterface(x) for x in interface_list]
    result = 'Interfaces created by breakout:\n'
    if task.host.platform not in ['nxos', 'huawei_vrpv8']:
        raise UnsupportedNOS('task received unsupported NOS - {}'.format(
            task.host.platform))
    for interface in task.host['interfaces']:
        if task.host.platform == 'nxos' and interface.name.count('/') == 2:
            interface.breakout = True
            result += f'\tInterface {interface.name} created by breakout'
        elif task.host.platform == 'huawei_vrpv8' and interface.name.find(
                ':') != -1:
            interface.breakout = True
            result += f'\tInterface {interface.name} created by breakout'
        else:
            interface.breakout = False
    return Result(host=task.host, result=result)


def get_transceiver_stats(task, interface_list=None):
    if interface_list:
        task.host['interfaces'] = [SwitchInterface(x) for x in interface_list]
    result = 'Interface transceiver statistics:\n'
    connection = task.host.get_connection('netmiko', None)
    if task.host.platform not in ['nxos', 'huawei_vrpv8']:
        raise UnsupportedNOS('task received unsupported NOS - {}'.format(
            task.host.platform))
    all_transceiver_stats = connection.send_command(
                task.host['vendor_vars']['show interface transceiver detail'])
    for interface in task.host['interfaces']:
        if task.host.platform == 'nxos':
            pass
        elif task.host.platform == 'huawei_vrpv8':
            # if not all_transceiver_stats:
            # Work on non-fiber/no transceiver situation
            stats_start = all_transceiver_stats.index(
                    f'{interface} transceiver information:')
            stats_end = all_transceiver_stats[stats_start+40:].find(
                    'transceiver information:')
            if stats_end == -1:
                stats_end = len(all_transceiver_stats) - 1
            stats_chunk = all_transceiver_stats[stats_start:stats_end]
            ddm_supported = re.search(
                    r'Digital Diagnostic Monitoring\s+:(YES|NO)', stats_chunk)
            interface.ddm = True if ddm_supported.group(1) == 'YES' else False
            vendor_name = re.search(r'Vendor Name\s+:(.+)', stats_chunk)
            transceiver_model = re.search(r'Vendor Part Number\s+:(.+)',
                                          stats_chunk)
            interface.transceiver = vendor_name.group(
                    1) + ' ' + transceiver_model.group(1)
            interface.module_type = re.search(
                    r'Transceiver Type\s+:(.+)', stats_chunk).group(1).replace(
                            '_', '-')
            if not interface.ddm or 'Current RX Power' not in stats_chunk:
                # DDM can be supported, but no stats listed
                interface.optical_lanes = None
                interface.rx_power = None
                continue
            if 'Lane' not in stats_chunk:
                interface.optical_lanes = 1
                rx_power = re.search(
                    r'Current RX Power \(dBm\)\s+:(-?\d{1,2}\.\d{1,2})',
                    stats_chunk)
                interface.rx_power = float(rx_power.group(1))
            else:
                rx_pwr_start = stats_chunk.index('Current RX Power (dBm)')
                next_new_line = stats_chunk.index('\n', rx_pwr_start)
                rx_pwr_end = stats_chunk.index('Default RX Power',
                                               rx_pwr_start)
                rx_pwr_chunk = stats_chunk[next_new_line:rx_pwr_end]
                lanes_rxs = re.findall(r'(-?\d{1,2}\.\d{1,2})', rx_pwr_chunk)
                interface.rx_power = list(map(float, lanes_rxs))
                interface.optical_lanes = len(interface.rx_power)
    return Result(host=task.host, result=result)
