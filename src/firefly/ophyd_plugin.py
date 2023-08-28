import logging

import numpy as np
from qtpy.QtCore import Qt, Slot, QTimer
from qtpy.QtWidgets import QApplication
from ophyd import OphydObject
from haven import registry, exceptions
from pydm.data_plugins import add_plugin
from pydm.data_plugins.plugin import PyDMConnection, PyDMPlugin
# from pydm.data_plugins.epics_plugins.pyepics_plugin_component import (
#     Connection,
#     PyEPICSPlugin,
# )


log = logging.getLogger(__name__)


class Connection(PyDMConnection):
    _cpt: OphydObject = None
    _ctrl_vars: dict = {}
    """A pydm connection for hardware abstraction through Ophyd objects."""

    def __init__(self, channel, address, protocol=None, parent=None):
        name = address
        self._cids = {}
        super().__init__(channel, address, protocol, parent)
        # Resolve the device based on the ohpyd name
        try:
            self._cpt = registry.find(address)
        except (AttributeError, exceptions.ComponentNotFound):
            log.warning(f"Couldn't find ophyd plugin device: {address}")
        else:
            log.debug(f"Found device: {address}: {self._cpt.name}")
        # Listen for changes
        self.prepare_subscriptions()
        self.add_listener(channel)
    
    def prepare_subscriptions(self):
        """Set up routines to respond to changes in the ophyd object."""
        if self._cpt is not None:
            log.debug(f"Preparing subscriptions for {self._cpt.name}")
            self._cids['meta'] = self._cpt.subscribe(self.update_ctrl_vars, event_type="meta", run=False)
            event_type = self._cpt._default_sub
            self._cids[event_type] = self._cpt.subscribe(self.send_new_value, event_type=event_type, run=False)

    def send_new_value(self, *args, **kwargs):
        if "value" in kwargs.keys():
            value = kwargs["value"]
            log.debug(f"Received new value for {self._cpt.name}: {value}")
        else:
            log.debug(f"Did not receive a new value. Skipping update for {self._cpt.name}.")
            return
        log.debug(f"Sending new {type(value)} value for {self._cpt.name}: {value}")
        self.new_value_signal[type(value)].emit(value)

    def update_ctrl_vars(self, *args, **kwargs):
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
        }
        if hasattr(self, 'timestamp_signal'):
            # The timestamp_signal is a recent addition to PyDM
            var_signals["timestamp"] = self.timestamp_signal
        # Process the individual control variable arguments
        for key, signal in var_signals.items():
            if kwargs.get(key) is not None:
                # Use the argument value
                val = kwargs[key]
            else:
                log.debug(f"Could not find {key} control variable for {self._cpt.name}.")
                continue
            # Emit the new value if is different from last time
            if val != self._ctrl_vars.get(key, None):
                log.debug(f"Emitting new {key}: {val}")
                signal.emit(val)
                self._ctrl_vars[key] = val

    def add_listener(self, channel):
        super(Connection, self).add_listener(channel)
        # Clear cached control variables so they can get remitted
        self._ctrl_vars = {}
        # If the channel is used for writing to components, hook it up
        if (sig := channel.value_signal) is not None:
            for dtype in [float, int, str, np.ndarray]:
                try:
                    sig[dtype].connect(self.set_value, Qt.QueuedConnection)
                except KeyError:
                    pass
        # Run the callbacks to make sure the new listener gets notified
        self.run_callbacks()

    def run_callbacks(self):
        """Run the existing callbacks of the Ophyd object."""
        if self._cpt is None:
            self.connection_state_signal.emit(False)
        else:
            cpt = self._cpt
            for event_type in [cpt._default_sub, 'meta']:
                cached = cpt._args_cache[event_type]
                log.debug(f"Running {event_type} callbacks: {cached}")
                if cached is not None:
                    args, kwargs = cached
                elif event_type == "meta":
                    args = ()
                    kwargs = cpt.metadata
                else:
                    continue
                cid = self._cids[event_type]
                callback = cpt._callbacks[event_type][cid]
                callback(*args, **kwargs)

    def close(self):
        """Remove any callbacks previously set up for this connection."""
        if self._cpt is not None:
            for cid in self._cids.values():
                self._cpt.unsubscribe(cid)

    @Slot(float)
    @Slot(int)
    @Slot(str)
    @Slot(np.ndarray)
    def set_value(self, new_value):
        log.debug(f"Setting new value for {self._cpt.name}: {new_value}")
        self._cpt.set(new_value)

class OphydPlugin(PyDMPlugin):
    protocol = "oph"
    connection_class = Connection
