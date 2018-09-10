import re
from app_exception import AppException


class UnacceptableCondition(AppException):
    pass


class SwitchInterface:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name


def find_vrf(vrf_name, vendor_dict, connection=None, output=None):
    if connection is not None:
        output = connection.send_command(vendor_dict['show vrf'])
    if re.search(vendor_dict['vrf regexp'].format(vrf_name), output):
        return "VRF {} is present on a device".format(vrf_name)
    else:
        return "VRF {} is not found on a device".format(vrf_name)


def get_vrf_interfaces(vrf_name, vendor_dict, nos, connection=None,
                       output=None):
    if connection is not None:
        output = connection.send_command(
                vendor_dict['show vrf interfaces'].format(vrf_name))
    if nos == 'nxos':
        if vrf_name not in output:
            return []
        else:
            return [SwitchInterface(
                x.split(' ')[0]) for x in output.strip().split('\n')[1:]]
    elif nos == 'huawei_vrpv8':
        if 'Interface Number : 0' in output:
            return []
        else:
            start_mark = 'Interface list : '
            start = output.index(start_mark)
            return [SwitchInterface(x.strip(' ,')) for x in output[start+len(
                start_mark):].strip().split('\n')]
    else:
        raise UnacceptableCondition(
                'task received unsupported NOS - {}'.format(nos))


def get_vrf_ll_neighbors(task, vrf_name):
    pass


def get_vrf_bgp_status(task, vrf_name):
    pass
