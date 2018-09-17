import ipaddress


class SwitchInterface:
    def __init__(self, name):
        self.name = name
        self.ipv4_addresses = []
        self.ipv6_addresses = []

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
