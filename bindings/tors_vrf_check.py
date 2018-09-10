import json
from nornir.core import InitNornir
from nornir.plugins.functions.text import print_result
from nornir.core.task import Result
from utils.nornir_utils import nornir_set_credentials
from tasks.check_vrf_status import find_vrf
from app_exception import AppException


class UnsupportedNOS(AppException):
    pass


def check_vrf(task, vrf_name):
    with open('vendor_specifics.json', 'r', encoding='utf-8') as jsonf:
        vendor_specs = json.load(jsonf)
    if task.host["nornir_nos"] == "nxos":
        vendor_dict = vendor_specs['Cisco Nexus']
    elif task.host["nornir_nos"] == 'huawei_vrpv8':
        vendor_dict = vendor_specs['Huawei CE']
    else:
        raise UnsupportedNOS("{} is unsupported or bogus".format(
            task.host["nornir_nos"]))
    connection = task.host.get_connection("netmiko")
    vrf_present = find_vrf(vrf_name=vrf_name, vendor_dict=vendor_dict,
                           connection=connection)
    return Result(host=task.host, result=vrf_present)


nrnr = InitNornir(config_file="config.yml")
nornir_set_credentials(nrnr)
result = nrnr.run(task=check_vrf, vrf_name="***REMOVED***")
print_result(result)
