import json
import logging

from collections import defaultdict
from ops.framework import EventBase, EventSetBase, EventSource, Object, StoredState


class ProxyConfigError(Exception):
    """Proxy configuration isn't valid."""

    pass


class ProxyReady(EventBase):
    pass


class InterfaceRequiresEvents(EventSetBase):
    proxy_ready = EventSource(ProxyReady)


class ProxyConfig:
    def __init__(self, config):
        """Initialize a ProxyConfig."""
        self._config = defaultdict(lambda: None, config)
        self._validate_config()

    def _validate_config(self):
        """Validate the ProyxConfig."""
        required_configs = ("external_port", "internal_host", "internal_port")

        # Verify required settings are provided

        for entry in self._config:
            for required in required_configs:
                if not entry[required]:
                    raise ProxyConfigError('"{}" is required'.format(required))

        # Validate mode setting

        if entry["mode"] not in ("http", "tcp"):
            if not entry["mode"]:
                entry["mode"] = "http"
            else:
                raise ProxyConfigError('"mode" setting must be http or tcp if provided')
        # Set default value for 'check' if not set

        if entry["check"] is None:
            entry["check"] = True
        # Check for http required options

        if entry["urlbase"] == entry["subdomain"] is None and entry["mode"] == "http":
            raise ProxyConfigError('"urlbase" or "subdomain" must be set in http mode')

    def __getitem__(self, key):
        return self._config.get(key)

    def __setitem__(self, key, value):
        self._config[key] = value
        self._validate_config()

    def __contains__(self, key):
        return key in self._config


class ReverseProxyRequires(Object):

    on = InterfaceRequiresEvents

    state = StoredState()

    def __init__(self, charm, relation_name):
        super().__init(charm, relation_name)
        self._relation_name = relation_name
        self._relation = self.model.get_relation(relation_name)
        self.framework.observe(
            charm.on[relation_name].relation_changed, self.on_relation_changed
        )
        # TODO: Observer and handle departed
        self.state.set_default(hostname=False)
        self.state.set_default(ports=False)

    def on_relation_changed(self, event):
        """React to relaction changed."""
        hostname = event.relation.data[event.unit].get("hostname")
        ports = event.relation.data[event.unit].get("ports")

        if hostname and ports:
            self.state.hostname = hostname
            self.state.ports = ports
            self.on.proxy_ready.emit()
            logging.debug("Proyx {} is ready".format(hostname))

    def set_proxy_config(self, config):
        """Configure the proxy relation."""
        configs = []
        configs.extend(config)

        for config in configs:
            if type(config) is not ProxyConfig:
                raise ProxyConfigError(
                    "Proxy config must be of type ProxyConfig not {}".format(
                        type(config)
                    )
                )

        self._relation.data[self.model.unit]["config"] = json.dumps(configs)

    @property
    def proxy_hostname(self):
        """Hostname for the remote host."""

        return self.state.hostname

    @property
    def proxy_ports(self):
        """Ports for the remote host."""

        return self.state.ports


# class ProxyListenTcpInterfaceRequires(Object):
#
#     on = InterfaceProvidesEvents()
#
#     state = StoredState()
#
#     def __init__(self, charm, relation_name):
#         super().__init__(charm, relation_name)
#         self._relation_name = relation_name
#         self._listen_proxies = None
#         self.framework.observe(charm.on[relation_name].relation_changed, self.on_relation_changed)
#
#     def on_relation_changed(self, event):
#         self.on.backends_changed.emit()
#
#     @property
#     def listen_proxies(self):
#         if self._listen_proxies is None:
#             self._listen_proxies = []
#             for relation in self.model.relations[self._relation_name]:
#                 # TODO: Work around https://github.com/canonical/operator/issues/175.
#                 # Once a -joined event actually fires we will process this relation.
#                 if not relation.units:
#                     continue
#                 app_data = relation.data[relation.app]
#                 listen_options = json.loads(app_data.get('listen_options', '[]'))
#                 listen_options.append('mode tcp')
#                 server_options = []
#                 for unit in relation.units:
#                     server_option = relation.data[unit].get('server_option')
#                     if server_option is not None:
#                         server_options.append(server_option)
#                 # Only expose a section if there are actual backends present.
#                 if relation.units:
#                     section_name = f'{relation.name}_{relation.id}_{relation.app.name}'
#                     self._listen_proxies.append(
#                         ListenProxyData(section_name, listen_options, server_options))
#         return self._listen_proxies
#
#     @property
#     def frontend_ports(self):
#         _ports = []
#         for relation in self.model.relations[self._relation_name]:
#             # TODO: Work around https://github.com/canonical/operator/issues/175.
#             # Once a -joined event actually fires we will process this relation.
#             if not relation.units:
#                 continue
#             frontend_port = relation.data[relation.app].get('frontend_port')
#             if frontend_port is not None:
#                 _ports.append(frontend_port)
#         return _ports
#
#
# class ProxyListenTcpInterfaceProvides(Object):
#
#     def __init__(self, charm, relation_name):
#         super().__init__(charm, relation_name)
#         self._relation_name = relation_name
#         # TODO: there could be multiple independent reverse proxies in theory, address that later.
#         self._relation = self.model.get_relation(relation_name)
#
#     def expose_server(self, frontend_port, listen_options, server_option):
#         # Expose common settings via app relation data from a leader unit.
#         if self.model.unit.is_leader():
#             app_data = self._relation.data[self.model.app]
#             app_data['frontend_port'] = str(frontend_port)
#             app_data['listen_options'] = json.dumps(listen_options)
#         self._relation.data[self.model.unit]['server_option'] = server_option
