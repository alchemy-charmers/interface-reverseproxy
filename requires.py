from charms.reactive import RelationBase, scopes, hook
from charmhelpers.core import hookenv

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
        self.set_remote('config',json.dumps(config))
        self.set_state('{relation_name}.configured')
