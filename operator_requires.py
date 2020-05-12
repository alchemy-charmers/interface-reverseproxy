import json
import logging
from collections import defaultdict

from ops.framework import EventBase, EventSetBase, EventSource, Object, StoredState


class ProxyConfigError(Exception):
    """Proxy configuration isn't valid."""

    pass


class ProxyReady(EventBase):
    """Emitted if the proxy provides host and port configurations."""

    pass


class ProxyConnected(EventBase):
    """Emitted when a relation is established."""

    pass


class ProxyStatusAvailable(EventBase):
    """Emitted when a status is available from the proxy."""

    pass


class InterfaceRequiresEvents(EventSetBase):
    proxy_ready = EventSource(ProxyReady)
    proxy_connected = EventSource(ProxyConnected)
    proxy_status_available = EventSource(ProxyStatusAvailable)


class ProxyConfig:
    def __init__(self, config):
        """Initialize a ProxyConfig."""
        self._config = defaultdict(lambda: None, config)
        self._validate_config()

    def _validate_config(self):
        """Validate the ProyxConfig."""
        required_configs = ("external_port", "internal_host", "internal_port")

        # Verify required settings are provided

        for required in required_configs:
            if not self._config[required]:
                raise ProxyConfigError('"{}" is required'.format(required))

        # Validate mode setting

        if self._config["mode"] not in ("http", "tcp", "tcp+tls"):
            if not self._config["mode"]:
                self._config["mode"] = "http"
            else:
                raise ProxyConfigError('"mode" setting must be http, tcp or tcp+tls if provided')
        # Set default value for 'check' if not set

        if self._config["check"] is None:
            self._config["check"] = True
        # Check for http required options

        if (
            self._config["urlbase"] == self._config["subdomain"] is None
            and self._config["mode"] == "http"
        ):
            raise ProxyConfigError('"urlbase" or "subdomain" must be set in http mode')

    def __getitem__(self, key):
        return self._config.get(key)

    def __setitem__(self, key, value):
        self._config[key] = value
        self._validate_config()

    def __contains__(self, key):
        return key in self._config


class ProxyConfigEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ProxyConfig):
            return obj._config

        return json.JSONEncoder.default(self, obj)


class ReverseProxyRequires(Object):

    on = InterfaceRequiresEvents()

    state = StoredState()

    def __init__(self, charm, relation_name):
        super().__init__(charm, relation_name)
        self._relation_name = relation_name
        self._relation = self.model.get_relation(relation_name)
        self.framework.observe(
            charm.on[relation_name].relation_changed, self.on_relation_changed
        )
        self.framework.observe(
            charm.on[relation_name].relation_joined, self.on_relation_joined
        )
        # TODO: Observer and handle departed
        self.state.set_default(hostname=False)
        self.state.set_default(ports=False)
        self.state.set_default(config_status=False)

    def on_relation_joined(self, event):
        """React to relation joined."""
        logging.debug("Emitting proxy joined event")
        self.on.proxy_connected.emit()

    def on_relation_changed(self, event):
        """React to relaction changed."""
        hostname = event.relation.data[event.unit].get("hostname")
        ports = event.relation.data[event.unit].get("ports")

        if hostname and ports:
            self.state.hostname = hostname
            self.state.ports = ports
            self.on.proxy_ready.emit()
            logging.debug("Proyx {} is ready".format(hostname))

        status_key = "{}.config_status".format(self.model.unit)
        config_status = event.relation.data[event.unit].get(status_key)

        if config_status:
            self.state.config_status = config_status
            if config_status.startswith('passed'):
                logging.info(config_status)
            elif config_status.startswith('failed'):
                logging.error(config_status)
            self.on.proxy_status_available.emit()

    def set_proxy_config(self, config):
        """Configure the proxy relation."""
        configs = []

        if isinstance(config, list):
            configs = config
        else:
            configs.append(config)

        logging.debug("Verifying type of proxy configs")

        for config in configs:
            if not isinstance(config, ProxyConfig):
                raise ProxyConfigError(
                    "Proxy config must be of type ProxyConfig not {}".format(
                        type(config)
                    )
                )

        logging.debug("Setting proxy configs on relation")
        self._relation.data[self.model.unit]["config"] = json.dumps(
            configs, cls=ProxyConfigEncoder
        )

    @property
    def proxy_hostname(self):
        """Hostname for the remote host."""

        return self.state.hostname

    @property
    def proxy_ports(self):
        """Ports for the remote host."""

        return self.state.ports

    @property
    def config_status(self):
        """Status from the host for provided config."""

        return self.state.config_status
