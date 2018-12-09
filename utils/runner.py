import click
import ipaddress
from yaml.scanner import ScannerError
from ruamel.yaml import YAML
from nornir.core import InitNornir


class NoGroupsHost(Exception):
    '''Exception to raise in a process of adding host into inventory if there
    are no groups configured for that host.'''
    pass


@click.command()
@click.option('-c', '--config', default='config.yml')
@click.argument('hostname')
def main(config, hostname):
    if not is_in_inventory(config, hostname):
        click.echo('Host not found in inventory.')
        click.confirm('Add it? [Y/N]', abort=True)
        ip_addr = click.prompt('''Enter IP address to put it in config or
        domain name to do a DNS lookup into > ''')
        try:
            host_defnintion = ipaddress.ip_address(ip_addr)
        except ValueError:
            try:
                import socket
                host_defnintion = socket.gethostbyname(hostname+'.'+ip_addr)
            except socket.gaierror:
                click.echo('Incorrect IP address, hostname or domain')
                exit(1)
        click.echo('Available groups: {}'.format(get_inventory_groups(config)))
        groups = click.prompt('''Enter groups separated by commas, spaces will
        be stripped, unknown groups ignored, new groups creation unsuppoted >
        ''')
        add_to_inventory(config, hostname, host_defnintion, groups)
    else:
        pass


def get_inventory_groups(config):
    '''Parse Nornir config file to find group inventory file and parse it next.
    Grab all configured groups and return them.
    Arguments:
        * config - Nornir configuration file location
    Returns:
        view of dictionary keys, which represents groups defined in inventory
    '''
    yaml = YAML()
    with open(config, 'r', encoding='utf-8') as config_file:
        config_yaml = yaml.load(config_file)
    group_inventory = config_yaml['SimpleInventory']['group_file']
    with open(group_inventory, 'r', encoding='utf-8') as group_file:
        groups = yaml.load(group_file)
    return groups.keys()


def is_in_inventory(config, hostname):
    '''Initialize Nornir and check if hostname is defined in inventory.
    Argumets:
        * config - Nornir configuration file location
        * hostname - hostname that will be looked up
    Returns:
        * True or False - is host in inventory
    '''
    try:
        nrnr = InitNornir(config_file=config)
    except ScannerError:
        click.echo('Invalid Nornir configs')
        exit(1)
    if hostname not in nrnr.inventory.hosts.keys():
        return False
    else:
        return True


def add_to_inventory(config, hostname, ip, groups, no_such_group_ignore=False):
    '''Add host to Nornir inventory file. Raise NoGroupsHost exception if no
    groups configured, or all of them not exist (in keys of
    no_such_group_ignore flag is set).
    Arguments:
        * config - Nornir configuration file location
        * hostname - host name, that will be added into inventory
        * ip - host IP address (checking if it valid is out of scope of that
            function)
        * groups - string that represents groups this host will be added to;
            group names must be separated by commas, spaces will be ignored
        * no_such_group_ignore (default to False) - if True, silently drop
            unexisted groups, otherwise raise ValueError
    Returns nothing
    '''
    if not groups:
        raise NoGroupsHost('No groups configured')
    configured_groups = get_inventory_groups(config)
    groups = [x.strip() for x in groups.split(',')]
    cleaned_groups = []
    # we are going to use this for stripping nonexisiting groups if
    # no_such_group_ignore flag is set
    for group in groups:
        if group not in configured_groups:
            if not no_such_group_ignore:
                raise ValueError('Group {} is not configured'.format(group))
            else:
                continue
        else:
            cleaned_groups.append(group)
    if len(cleaned_groups) == 0:
        raise NoGroupsHost('All configured groups not exist')
    host = {hostname: {"nornir_host": ip, "groups": cleaned_groups}}
    yaml = YAML()
    with open(config, 'r', encoding='utf-8') as config_file:
        config_yaml = yaml.load(config_file)
    host_inventory = config_yaml['SimpleInventory']['host_file']
    yaml.indent(mapping=2, sequence=2, offset=2)
    with open(host_inventory, 'a', encoding='utf-8') as host_file:
        host_file.write('\n')
        yaml.dump(host, host_file)


if __name__ == '__main__':
    main()
