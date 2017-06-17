from charms.reactive import RelationBase, scopes, hook
from charmhelpers.core import hookenv

import json

class ReverseProxyRequires(RelationBase):
    scope = scopes.UNIT
    auto_accessors=['hostname','ports','cfg_good','status_msg']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        hookenv.atexit(lambda: self.remove_state('{relation_name}.triggered'))

    @hook('{requires:reverseproxy}-relation-{joined,changed}')
    def changed(self):
        self.set_state('{relation_name}.triggered')
        hookenv.log('reverseproxy.triggered','INFO')
        if self.hostname() and self.ports():
            hookenv.log('reverseproxy.ready','INFO')
            self.set_state('{relation_name}.ready')
            if self.cfg_good is False:
                hookenv.log('reverseproxy cfg failed: {}'.format(self.status_msg),'ERROR')
                #TODO raise error or set blocked in addation to logging?
            elif self.cfg_good is None:
                hookenv.log('reverseproxy cfg not yet set','INFO')
            elif self.cfg_good is True:
                hookenv.log('reverseproxy cfg passed: {}'.format(self.status_msg),'INFO')
                 
    @hook('{requires:reverseproxy}-relation-{departed}')
    def departed(self):
        self.set_state('{relation_name}.triggered')
        self.remove_state('{relation_name}.configured')
        hookenv.log('reverseproxy.departed','INFO')

    def configure(self,config):
        self.set_remote('config',json.dumps(config))
        self.set_state('{relation_name}.configured')
