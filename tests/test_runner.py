import pytest
from utils.runner import is_in_inventory, add_to_inventory
from utils.runner import get_inventory_groups, NoGroupsHost


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


def test_get_inventory_groups(tmp_inventory_files):
    config = tmp_inventory_files
    assert 'cisco_tors' in get_inventory_groups(config)
    assert 'dc_2' in get_inventory_groups(config)


def test_add_to_inventory(tmp_inventory_files):
    config = tmp_inventory_files
    add_to_inventory(config, 'cisco-dc2', '10.3.3.3',
                     'dc_2, cisco_tors')
    assert is_in_inventory(config, 'cisco-dc2') is True
    with pytest.raises(ValueError):
        add_to_inventory(config, 'cisco-dc3', '10.4.4.4.',
                         'dc_3, cisco_tors')
    assert add_to_inventory(
            config, 'cisco-dc4', '10.5.5.5',
            'dc_4, cisco_tors', no_such_group_ignore=True) is None
    with pytest.raises(NoGroupsHost):
        add_to_inventory(config, 'huawei-dc3', '10.6.6.6', 'dc_3, hawei_tors',
                         no_such_group_ignore=True)
    with pytest.raises(NoGroupsHost):
        add_to_inventory(config, 'huawei-dc4', '10.7.7.7', '')
