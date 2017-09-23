from charms.reactive import RelationBase, scopes, hook, helpers
from charmhelpers.core import hookenv

import socket
import json


class ReverseProxyProvides(RelationBase):
    scope = scopes.UNIT
#    auto_accessors=['config']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        hookenv.atexit(lambda: self.remove_state('{relation_name}.triggered'))
        hookenv.atexit(lambda: self.remove_state('{relation_name}.changed'))
        hookenv.atexit(lambda: self.remove_state('{relation_name}.departed'))

    @hook('{provides:reverseproxy}-relation-{joined,changed}')
    def changed(self):
        self.set_state('{relation_name}.triggered')
        if self.config is not None and helpers.data_changed(hookenv.remote_unit(), self.config):
            self.set_state('{relation_name}.changed')
            hookenv.log('Setting {relation_name}.changed', 'DEBUG')
        else:
            hookenv.log('No change, remote_unit: {}'.format(hookenv.remote_unit()), 'DEBUG')
            hookenv.log('No change, config: {}'.format(self.config), 'DEBUG')

    @hook('{provides:reverseproxy}-relation-{departed}')
    def departed(self):
        hookenv.log('reverseproxy.departed', 'INFO')
        self.set_state('{relation_name}.triggered')
        self.set_state('{relation_name}.departed')
        # Clear states and data on depart
        self.remove_state('{relation_name}.ready')
        self.set_remote(hookenv.remote_unit() + '.cfg_status', None)
        helpers.data_changed(hookenv.remote_unit(), None)

    def configure(self, ports=None, hostname=None):
        hookenv.log('provides:reverseproxy.configure called for unit {}'.format(hookenv.remote_unit()), 'DEBUG')
        hookenv.log('provides:reverseproxy.configure current hook {}'.format(hookenv.hook_name()), 'DEBUG')
        hostname = hostname or socket.getfqdn()
        ports = ports or []
        relation_info = {
            'hostname': hostname,
            'ports': ports
        }
        self.set_remote(**relation_info)
        self.set_state('{relation_name}.ready')

    def set_cfg_status(self, cfg_good, msg=None):
        ''' After receiving a reverse proxy request, the provider should provide a status update
        cfg_good: Boolean value to represnt if the config was valid
        msg: Optional msg to to explain the status
        '''
        msg = msg or ''
        if cfg_good:
            status = 'passed: ' + msg
            hookenv.log(status, 'INFO')
        else:
            status = 'failed: ' + msg
            hookenv.log(status, 'WARNING')
        self.set_remote(hookenv.remote_unit() + '.cfg_status', status)

    @property
    def config(self):
        if self.get_remote('config') is None:
            return None
        return json.loads(self.get_remote('config'))
