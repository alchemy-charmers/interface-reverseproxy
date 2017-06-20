from charms.reactive import RelationBase, scopes, hook
from charmhelpers.core import hookenv
from collections import defaultdict

import json

class ProxyConfigError(Exception):
    ''' Exception raise if reverse proxy provider can't apply request configuratin '''

class ReverseProxyRequires(RelationBase):
    scope = scopes.UNIT
    #auto_accessors=['hostname','ports']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        hookenv.atexit(lambda: self.remove_state('{relation_name}.triggered'))
        hookenv.atexit(lambda: self.remove_state('{relation_name}.departed'))

    @hook('{requires:reverseproxy}-relation-{joined,changed}')
    def changed(self):
        self.set_state('{relation_name}.triggered')
        hookenv.log('reverseproxy.triggered','INFO')
        if self.hostname and self.ports:
            hookenv.log('reverseproxy.ready','INFO')
            self.set_state('{relation_name}.ready')
            if self.cfg_status is None:
                hookenv.log('reverseproxy cfg status not yet set','INFO')
            elif self.cfg_status.startswith('passed'):
                hookenv.log(self.cfg_status,'INFO')
            elif self.cfg_status.startswith('failed'):
                hookenv.log(self.cfg_status,'ERROR')
                raise ProxyConfigError(self.cfg_status)
                 
    @hook('{requires:reverseproxy}-relation-{departed}')
    def departed(self):
        self.set_state('{relation_name}.triggered')
        self.set_state('{relation_name}.departed')
        self.remove_state('{relation_name}.configured')
        self.remove_state('{relation_name}.ready')
        hookenv.log('reverseproxy.departed','INFO')

    def configure(self,config):
        # Basic config validation
        config = defaultdict(lambda: None, config)
        required_configs = ('external_port','internal_host','internal_port')
        optional_configs = ('mode','urlbase','subdomain','group_id')
        # Error if missing required configs
        for rconfig in required_configs:
            if not config[rconfig]:
                raise ProxyConfigError('"{}" is required'.format(rconfig))
        # Create key if optional config isn't provided
        for oconfig in optional_configs:
            if not config[oconfig]:
                pass 
        # Check that mode is valid, set default if not provided
        if config['mode'] not in ('http','tcp'):
            if not config['mode']:
                config['mode'] = 'http'
            else:
                raise ProxyConfigError('"mode" setting must be http or tcp if provided')        
        # Check for http required options
        if config['urlbase'] == config['subdomain'] == None and config['mode'] == 'http':
            raise ProxyConfigError('"urlbase" or "subdomain" must be set in http mode')        

        self.set_remote('config',json.dumps(config))
        self.set_state('{relation_name}.configured')

    @property
    def cfg_status(self):
        return self.get_remote(hookenv.local_unit()+'.cfg_status')

    @property
    def hostname(self):
        return self.get_remote('hostname')

    @property
    def ports(self):
        return self.get_remote('ports')
