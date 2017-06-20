from charms.reactive import RelationBase, scopes, hook
from charmhelpers.core import hookenv
from collections import defaultdict

import json

class ProxyConfigError(Exception):
    ''' Exception raise if reverse proxy provider can't apply request configuratin '''

class ReverseProxyRequires(RelationBase):
    scope = scopes.UNIT
    auto_accessors=['hostname','ports','cfg_status']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        hookenv.atexit(lambda: self.remove_state('{relation_name}.triggered'))
        hookenv.atexit(lambda: self.remove_state('{relation_name}.departed'))

    @hook('{requires:reverseproxy}-relation-{joined,changed}')
    def changed(self):
        self.set_state('{relation_name}.triggered')
        hookenv.log('reverseproxy.triggered','INFO')
        if self.hostname() and self.ports():
            hookenv.log('reverseproxy.ready','INFO')
            self.set_state('{relation_name}.ready')
            if self.cfg_status() is None:
                hookenv.log('reverseproxy cfg status not yet set','INFO')
            elif self.cfg_status().startswith('passed'):
                hookenv.log(self.cfg_status(),'INFO')
            elif self.cfg_status().startswith('failed'):
                hookenv.log(self.cfg_status(),'ERROR')
                raise ProxyConfigError(self.cfg_status())
                 
    @hook('{requires:reverseproxy}-relation-{departed}')
    def departed(self):
        self.set_state('{relation_name}.triggered')
        self.remove_state('{relation_name}.configured')
        self.set_state('{relation_name}.departed')
        hookenv.log('reverseproxy.departed','INFO')

    def configure(self,config):
        # Basic config validation
        config = defaultdict(lambda: None,config)    
        if config['mode'] not in ('http','tcp'):
            if not config['mode']:
                config['mode'] = 'http'
            else:
                raise ProxyConfigError('"mode" setting must be http or tcp if provided')        
        if config['mode'] == 'http':
            if config['urlbase'] == config['subdomain'] == None:
                raise ProxyConfigError('"urlbase" or "subdomain" must be set in http mode')        
        if not config['external_port']:
            raise ProxyConfigError('"external_port" is required')        
        if not config['internal_host']:
            raise ProxyConfigError('"internal_host" is required')        
        if not config['internal_port']:
            raise ProxyConfigError('"internal_port" is required')        

        self.set_remote('config',json.dumps(config))
        self.set_state('{relation_name}.configured')
