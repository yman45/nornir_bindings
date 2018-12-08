import click
import ipaddress
from yaml.scanner import ScannerError
from nornir.core import InitNornir


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
        groups = click.prompt('''Enter groups separated by commas, spaces will
        be stripped, unknown groups ignored, new groups creation unsuppoted >
        ''')
        add_to_inventory(config, hostname, host_defnintion, groups)
    else:
        pass


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


def add_to_inventory(config, hostname, host_definition, groups):
    pass


if __name__ == '__main__':
    main()
