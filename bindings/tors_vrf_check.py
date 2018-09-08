from nornir.core import InitNornir
from nornir.plugins.functions.text import print_result
from nornir.plugins.tasks.networking import netmiko_send_command
from utils.nornir_utils import nornir_set_credentials

nrnr = InitNornir(config_file="config.yml")
nornir_set_credentials(nrnr)
cisco_tors = nrnr.filter(lineup="nexus")
cmd = "show version"
result = cisco_tors.run(task=netmiko_send_command, command_string=cmd)
print_result(result)
