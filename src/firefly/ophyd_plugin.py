import logging

import numpy as np
from qtpy.QtCore import Qt, Slot
from ophyd import OphydObject
from haven import registry, exceptions
from pydm.data_plugins import add_plugin
from pydm.data_plugins.plugin import PyDMConnection, PyDMPlugin
# from pydm.data_plugins.epics_plugins.pyepics_plugin_component import (
#     Connection,
#     PyEPICSPlugin,
# )


log = logging.getLogger(__name__)


class OphydConnection(PyDMConnection):
    _cpt: OphydObject = None
    _ctrl_vars: dict = {}
    """A pydm connection for hardware abstraction through Ophyd objects."""

    def __init__(self, channel, address, protocol=None, parent=None):
        name = address
        super().__init__(channel, address, protocol, parent)
        # Resolve the device based on the ohpyd name
        try:
            self._cpt = registry.find(address)
        except (AttributeError, exceptions.ComponentNotFound):
            print(f"Could not find device: {address}")
            self.connection_state_signal.emit(False)
        else:
            print(f"Found device: {address}: {self._cpt.name}")
            # Listen for changes
            self.prepare_subscriptions()
            self.add_listener(channel)
    
    def prepare_subscriptions(self):
        """Set up routines to respond to changes in the ophyd object."""
        print(f"Preparing subs for {self._cpt.name}")
        if self._cpt is not None:
            self._cpt.subscribe(self.send_new_value, run=True)
            # Set up metadata callbacks
            self._cpt.subscribe(self.update_ctrl_vars, event_type="meta", run=True)

    def send_new_value(self, *args, **kwargs):
        if "value" in kwargs:
            value = kwargs["value"]
        else:
            return
        log.debug(f"Sending new value for {self._cpt.name}: {value}")
        self.new_value_signal.emit(value)

    def update_ctrl_vars(self, *args, **kwargs):
        # See which control variables have changed
        new_vars = {k: v for k, v in kwargs.items() if v != self._ctrl_vars.get(k)}
        log.debug(f"Updating ctrl vars for {self._cpt.name}: {new_vars}")
        # Emit signal if variable has changed
        var_signals = {
            "connected": self.connection_state_signal,
            "severity": self.new_severity_signal,
            "write_access": self.write_access_signal,
            "enum_strs": self.enum_strings_signal,
            "units": self.unit_signal,
            "precision": self.prec_signal,
            "lower_ctrl_limit": self.lower_ctrl_limit_signal,
            "upper_ctrl_limit": self.upper_ctrl_limit_signal,
            "timestamp": self.timestamp_signal,
        }
        for key, signal in var_signals.items():
            if value := new_vars.get(key):
                signal.emit(value)
        self._ctrl_vars.update(new_vars)

    def add_listener(self, channel):
        # Clear cached control variables so they can get remitted
        self._ctrl_vars = {}
        super().add_listener(channel)
        # If the channel is used for writing to components, hook it up
        if channel.value_signal is not None:
            channel.value_signal.connect(self.set_value, Qt.QueuedConnection)
        # Run the callbacks to make sure the new listener gets notified
        if self._cpt is not None:
            self._cpt._run_subs(sub_type=self._cpt._default_sub)
            self._cpt._run_metadata_callbacks()

    @Slot(float)
    @Slot(int)
    @Slot(str)
    @Slot(np.ndarray)
    def set_value(self, new_value):
        self._cpt.set(new_value).wait()

class OphydPlugin(PyDMPlugin):
    protocol = "oph"
    connection_class = OphydConnection

    # def add_connection(self, channel):
    #     import pdb; pdb.set_trace()
    #     super().add_connection(channel)
