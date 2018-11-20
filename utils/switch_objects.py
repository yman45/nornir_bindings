import ipaddress


class SwitchInterface:
    '''Represents switch interface and it's status.
    Attributes:
        * name - interface name; used in __init__
        * ipv4_addresses - list of IPAddress instances, with all IPv4 addresses
            exist on that interface
        * ipv6_addresses - list of IPAddress instances, with all IPv6 addresses
            exist on that interface
        * mode (defaults to 'switched') - either 'switched' or 'routed',
            represents mode of operation of that interface (L2 or L3); used in
            __init__ (default to 'switched')
        * svi - boolean to indicate if this interface is SVI
        * subinterface - boolean to indicate if this interface is subinterface
        * lag - boolean to indicate if this is interface is LAG
    '''
    def __init__(self, name, mode='switched'):
        self.name = name
        self.ipv4_addresses = []
        self.ipv6_addresses = []
        self.mode = mode
        if 'VLAN' in self.name.upper():
            self.svi = True
            self.mode = 'routed'
        else:
            self.svi = False
        if '.' in self.name:
            self.subinterface = True
            self.mode = 'routed'
        else:
            self.subinterface = False
        if self.name.startswith(('port-channel',
                                 'Eth-Trunk')) and '.' not in self.name:
            self.lag = True
        else:
            self.lag = False

    def __str__(self):
        return self.name


class IPAddress:
    '''Represents IP address (both v4 and v6) assigned to switch interface.
    Attributes:
        * address - instance of ipaddress.ip_address; used in __init__
        * prefix_length - prefix length in integer; used in __init__
        * primary - boolean, true if address is primary one; Note, however,
            that in some cases there can not be primary address, for example
            IPv6 in Huawei VRPv8; used in __init__ other way around as
            'secondary' (defaults to None)
    '''
    def __init__(self, address, prefix_length, secondary=None):
        self.address = ipaddress.ip_address(address)
        self.prefix_length = int(prefix_length)
        if not secondary:
            self.primary = True
        else:
            self.primary = False

    def __str__(self):
        view = self.address.compressed + '/' + str(self.prefix_length)
        if self.primary:
            view += ' (P)'
        return view


class BGPNeighbor:
    '''Represents BGP neighbor for a switch.
    Attributes:
        * address - instance of ipaddress.ip_address; used in __init__
        * af - dictionary containing AddressFamily instances assigned to 'ipv4'
            and 'ipv6' keys respectively
    '''
    def __init__(self, address):
        self.address = ipaddress.ip_address(address)
        self.af = {'ipv4': None, 'ipv6': None}


class AddressFamily:
    '''Represents address family for BGP neighbor.
    Attributes:
        * af_type - either 'v4' or 'v6', which represent respective AFI type;
            used in __init__
    '''
    def __init__(self, af_type):
        if af_type == 'v4' or af_type == 'v6':
            self.af_type = 'ip{} unicast'.format(af_type)
        else:
            self.af_type = af_type
        self.learned_routes = 0
        self.sent_routes = 0
