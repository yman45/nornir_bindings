import pytest
from utils.runner import is_in_inventory, add_to_inventory


@pytest.fixture
def tmp_inventory_files(tmp_path):
    conf = tmp_path / "conf.yml"
    inv_hosts = tmp_path / "hosts.yml"
    inv_groups = tmp_path / "groups.yml"
    test_config = '''
---
num_workers: 10
inventory: nornir.plugins.inventory.simple.SimpleInventory
SimpleInventory:
  host_file: "{}"
  group_file: "{}"
    '''.format(inv_hosts, inv_groups)
    hosts = '''
---
cisco-dc1:
  nornir_host: 10.1.1.1
  groups:
    - dc_1
    - cisco_tors
huawei-dc2:
  nornir_host: 10.2.2.2
  groups:
    - dc_2
    - huawei_tors
    '''
    groups = '''
---
defaults:
  domain: grt.dc
  asn: 65666
dc_1:
  dc_name: one_dc
dc_2:
  dc_name: two_dc
tors:
  role: tor_switch
cisco_tors:
  groups:
    - tors
  vendor: cisco
  lineup: nexus
  nornir_nos: nxos
huawei_tors:
  groups:
    - tors
  vendor: huawei
  lineup: ce
  nornir_nos: huawei_vrpv8
    '''
    conf.write_text(test_config)
    inv_hosts.write_text(hosts)
    inv_groups.write_text(groups)
    return conf


def test_is_in_inventory(tmp_inventory_files):
    config = tmp_inventory_files
    assert is_in_inventory(config, 'cisco-dc2') is False
    assert is_in_inventory(config, 'huawei-dc2') is True


def test_add_to_inventory(tmp_inventory_files):
    config = tmp_inventory_files
    assert add_to_inventory(config, 'cisco-dc2', '10.3.3.3',
                            'dc_2, cisco_tors') is True
    assert is_in_inventory(config, 'cisco-dc2') is True
    # assert add_to_inventory(config, 'cisco-dc1') is False
    # check for parameters (group creation, nos, etc...)
