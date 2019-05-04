from charms.reactive import RelationBase, scopes, hook
from charmhelpers.core import hookenv
from collections import defaultdict

import json


class ProxyConfigError(Exception):
    ''' Exception raiseed if reverse proxy provider can't apply request configuratin '''


class ReverseProxyRequires(RelationBase):
    scope = scopes.UNIT
    # auto_accessors=['hostname','ports']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        hookenv.atexit(lambda: self.remove_state('{relation_name}.triggered'))
        hookenv.atexit(lambda: self.remove_state('{relation_name}.departed'))

    @hook('{requires:reverseproxy}-relation-{joined,changed}')
    def changed(self):
        self.set_state('{relation_name}.triggered')
        hookenv.log('reverseproxy.triggered', 'DEBUG')
        # if self.hostname and self.ports:
        #     hookenv.log('reverseproxy.ready', 'INFO')
        self.set_state('{relation_name}.ready')
        hookenv.log('reverseproxy.ready', 'DEBUG')
        if self.cfg_status is None:
            hookenv.log('reverseproxy cfg status not yet set', 'INFO')
        elif self.cfg_status.startswith('passed'):
            hookenv.log(self.cfg_status, 'INFO')
        elif self.cfg_status.startswith('failed'):
            hookenv.log(self.cfg_status, 'ERROR')
            raise ProxyConfigError(self.cfg_status)

    @hook('{requires:reverseproxy}-relation-{departed}')
    def departed(self):
        self.set_state('{relation_name}.triggered')
        self.set_state('{relation_name}.departed')
        self.remove_state('{relation_name}.configured')
        self.remove_state('{relation_name}.ready')
        hookenv.log('reverseproxy.departed', 'INFO')

    def configure(self, config):
        # If a single config is provided make it a list of one
        configs = []
        if isinstance(config, dict):
            configs.append(config)
        else:
            configs = config
        # Make all configs a defaultdict
        configs = [defaultdict(lambda: None, d) for d in configs]
        # Valid all configs
        required_configs = ('external_port', 'internal_host', 'internal_port')
        for entry in configs:
            # Error if missing required configs
            for rconfig in required_configs:
                if not entry[rconfig]:
                    raise ProxyConfigError('"{}" is required'.format(rconfig))
            # Check that mode is valid, set default if not provided
            if entry['mode'] not in ('http', 'tcp'):
                if not entry['mode']:
                    entry['mode'] = 'http'
                else:
                    raise ProxyConfigError('"mode" setting must be http or tcp if provided')
            # Set default value for 'check' if not set
            if entry['check'] is None:
                entry['check'] = True
            # Set http check params if appropriate
            if (entry['mode'] != 'http' or entry['check'] is False) and entry['httpchk']:
                entry['httpchk'] = None
            # Check for http required options
            if entry['urlbase'] == entry['subdomain'] is None and entry['mode'] == 'http':
                raise ProxyConfigError('"urlbase" or "subdomain" must be set in http mode')

        self.set_remote('config', json.dumps(configs))
        self.set_state('{relation_name}.configured')

    @property
    def cfg_status(self):
        return self.get_remote(hookenv.local_unit() + '.cfg_status')

    @property
    def hostname(self):
        return self.get_remote('hostname')

    @property
    def ports(self):
        return self.get_remote('ports')
