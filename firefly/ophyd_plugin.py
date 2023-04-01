import logging

from haven import registry, exceptions
from pydm.data_plugins import add_plugin
from pydm.data_plugins.epics_plugins.pyepics_plugin_component import (
    Connection,
    PyEPICSPlugin,
)


log = logging.getLogger(__name__)


class OphydConnection(Connection):
    """A pydm connection for retrieving ophyd signals from haven registry.

    If the signal has a valid PV, then this connection functions as a
    conventional PyDMEpicsConnection. The *name* argument should match
    the *name* given when constructing the ophyd signal. The signal
    should be a leaf of the device hierarchy, i.e. one that
    corresponds to an EPICS PV.

    If the signal is not found, or does not have a PV, then the name
    will be used as is so that widgets display suitable feedback.

    """

    def __init__(self, channel, name, protocol=None, parent=None):
        # Resolve the device based on the ohpyd name
        try:
            component = registry.find(name)
        except exceptions.ComponentNotFound:
            # Component does not exist, so make a dummy component
            log.warning(f"Could not find component {name} in instrument registry.")
            component = type("NullDevice", (), {"pvname": name})
        try:
            pv = component.pvname
        except AttributeError:
            pv = name
            log.warning(
                f"Component {name} does not have a pv, consider using one of its children."
            )
        # Use the new PV to get a regular PV connection
        log.info(f"Converted ophyd name {name} to PV {pv}")
        super().__init__(channel=channel, pv=pv, protocol=protocol, parent=parent)


class OphydPlugin(PyEPICSPlugin):
    protocol = "oph"
    connection_class = OphydConnection
