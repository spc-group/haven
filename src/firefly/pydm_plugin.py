"""A PyDM data plugin that uses an Ophyd registry object to
communicate with signals.

Provides funcitonality so that PyDM channels can be addressed as e.g.
``haven://mirror.pitch.user_readback``

"""

import asyncio
import inspect
import logging
from typing import Mapping

import numpy as np
from bluesky.protocols import Movable, Subscribable
from ophyd import OphydObject
from ophyd.utils.epics_pvs import AlarmSeverity
from pydm.data_plugins.plugin import PyDMConnection
from qasync import asyncSlot
from typhos.plugins.core import SignalConnection, SignalPlugin

from haven import beamline

from .exceptions import UnknownOphydSignal

log = logging.getLogger(__name__)


class RegistryConnection:
    def find_signal(self, address: str):
        """Find a signal in the registry given its address.
        This method is intended to be overridden by subclasses that
        may use a different mechanism to keep track of signals.
        Parameters
        ----------
        address
          The connection address for the signal. E.g. in
          "sig://sim_motor.user_readback" this would be the
          "sim_motor.user_readback" portion.
        Returns
        -------
        Signal
          The Ophyd signal corresponding to the address.
        """
        return beamline.devices[address]


class HavenConnection(RegistryConnection, SignalConnection):
    pass


class HavenAsyncConnection(RegistryConnection, PyDMConnection):
    _is_ready = False

    def __init__(self, channel, address, protocol=None, parent=None):
        # Create base connection
        super().__init__(channel, address, protocol=protocol, parent=parent)
        self._connection_open = True
        self.signal_type = None
        self.is_float = False
        # Collect our signal
        self.signal = self.find_signal(address)
        self.is_triggerable = hasattr(self.signal, "trigger")
        self.is_movable = isinstance(self.signal, Movable)
        self.is_writable = self.is_movable or self.is_triggerable
        self.is_subscribable = isinstance(self.signal, Subscribable)
        # Subscribe to updates from Ophyd
        if self.is_subscribable:
            self.signal.subscribe(self.send_new_value)
        self._is_ready = True
        # Add listener
        self.add_listener(channel)

    def add_listener(self, channel):
        super().add_listener(channel)
        # If the channel is used for writing to PVs, hook it up to the 'put' methods.
        if channel.value_signal is not None:
            for type_ in [str, int, float, bool, np.ndarray]:
                try:
                    channel.value_signal[type_].connect(self.put_value)
                except KeyError:
                    pass
        # Emit updated value/metadata so the new channel gets notified
        self._meta_task = asyncio.create_task(
            self.send_new_meta(), name=f"meta_{self.signal.name}"
        )

    async def send_new_meta(self):
        # Assume the signal is connected
        self.connection_state_signal.emit(True)
        # Check the bluesky interface for writability
        self.write_access_signal.emit(self.is_writable)
        # Get some more metadata
        if hasattr(self.signal, "describe"):
            description = await self.signal.describe()
            description = description[self.signal.name]
        else:
            description = {}
        # What is the precision of this signal
        if (precision := description.get("precision")) is not None:
            self.prec_signal.emit(precision)
        # What are the units?
        if (units := description.get("units")) is not None:
            self.unit_signal.emit(units)
        # Update choices for enumerated types
        if (enum_strs := description.get("choices")) is not None:
            self.enum_strings_signal.emit(tuple(enum_strs))
        # Send the current value as well so widgets can update
        if self.is_subscribable:
            self.signal._get_cache()._notify(self.send_new_value, want_value=False)
        elif self.is_triggerable:
            # Any value will do, we won't use it anyway
            self.new_value_signal.emit(0)

    def send_new_value(self, reading: Mapping = {}, **kwargs):
        """
        Update the UI with a new value from the Signal.
        """
        # Ignore the run when ``subscribe()`` is first called
        if not self._is_ready:
            return
        # Update value
        reading = reading[self.signal.name]
        if reading is None:
            return
        value = reading["value"]
        try:
            self.new_value_signal[type(value)].emit(value)
        except Exception:
            log.exception("Unable to update %r with value %r.", self.signal.name, value)
        # Update alarm severity
        severity = reading.get("alarm_severity", AlarmSeverity.NO_ALARM)
        self.new_severity_signal.emit(severity)

    def close(self):
        """Unsubscribe from the Ophyd signal."""
        if self.is_subscribable:
            self.signal.clear_sub(self.send_new_value)

    @asyncSlot(int)
    @asyncSlot(float)
    @asyncSlot(str)
    @asyncSlot(bool)
    @asyncSlot(np.ndarray)
    async def put_value(self, new_value):
        if self.is_triggerable:
            # Just trigger the signal and be done
            await self.signal.trigger(wait=False)
        else:
            # Put the proper value to the signal
            old_value = await self.signal.get_value()
            log.info(
                f"Moving signal '{self.signal.name}' from {old_value} to {new_value}"
            )
            await self.signal.set(new_value, wait=False)


class HavenPlugin(SignalPlugin):
    protocol = "haven"

    @staticmethod
    def connection_class(channel, address, protocol):
        # Check if we need the synchronous or asynchronous version
        try:
            sig = beamline.devices[address]
        except KeyError:
            sig = None
        is_ophyd_async = inspect.iscoroutinefunction(getattr(sig, "connect", None))
        is_vanilla_ophyd = isinstance(sig, OphydObject)
        # Get the right Connection class and build it
        if is_ophyd_async:
            return HavenAsyncConnection(channel, address, protocol)
        elif is_vanilla_ophyd:
            return HavenConnection(channel, address, protocol)
        else:
            msg = f"Signal for {address=} must be ophyd or ophyd_async signal. Got {type(sig)=}."
            raise UnknownOphydSignal(msg)
