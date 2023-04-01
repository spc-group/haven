import logging

from haven import registry, exceptions
from pydm.data_plugins import add_plugin
from pydm.data_plugins.epics_plugins.pyepics_plugin_component import Connection, PyEPICSPlugin


log = logging.getLogger(__name__)


class OphydConnection(Connection):
    """A pydm connection class for retrieving ophyd objects from haven
    registry.

    """
    def __init__(self, channel, name, protocol=None, parent=None):
        # Resolve the device based on the ohpyd name
        from pprint import pprint
        pprint(registry.component_names)
        try:
            component = registry.find(name)
        except exceptions.ComponentNotFound:
            # Component does not exist, so make a dummy component
            log.warning(f"Could not find component {name} in instrument registry.")
            component = type("NullDevice", (), {'pvname': name})
        try:
            pv = component.pvname
        except AttributeError:
            pv = name
            log.warning(f"Component {name} does not have a pv, consider using one of its children.")
        # Use the new PV to get a regular PV connection
        log.info(f"Converted ophyd name {name} to PV {pv}")
        super().__init__(channel=channel, pv=pv, protocol=protocol, parent=parent)


class OphydPlugin(PyEPICSPlugin):
    protocol = "oph"
    connection_class = OphydConnection
