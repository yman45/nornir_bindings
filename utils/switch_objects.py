import ipaddress


class SwitchInterface:
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

    def __str__(self):
        return self.name


class IPAddress:
    def __init__(self, address, prefix_length, secondary=None):
        self.address = ipaddress.ip_address(address)
        self.prefix_length = int(prefix_length)
        if not secondary:
            self.primary = True
        else:
            self.primary = False

    def __str__(self):
        view = self.address.compressed + '/' + self.prefix_length
        if self.primary:
            view += ' (P)'
        return view
