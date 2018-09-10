import re


def find_vrf(vrf_name, vendor_dict, connection=None, output=None):
    if connection is not None:
        output = connection.send_command(vendor_dict['show vrf'])
    if re.search(vendor_dict['vrf regexp'].format(vrf_name), output):
        return "VRF {} is present on a device".format(vrf_name)
    else:
        return "VRF {} is not found on a device".format(vrf_name)


def get_vrf_interfaces(task, vrf_name):
    pass


def get_vrf_ll_neighbors(task, vrf_name):
    pass


def get_vrf_bgp_status(task, vrf_name):
    pass
