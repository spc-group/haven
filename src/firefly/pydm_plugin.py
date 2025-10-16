"""A PyDM data plugin that uses an Ophyd registry object to
communicate with signals.

Provides funcitonality so that PyDM channels can be addressed as e.g.
``haven://mirror.pitch.user_readback``

Inspired by Typhos's plugins.

"""

import asyncio
import inspect
import logging
from typing import Mapping

import numpy as np
from bluesky.protocols import Movable, Subscribable
from ophyd import OphydObject
from ophyd.utils.epics_pvs import AlarmSeverity, _type_map
from ophyd_async.core import Device as AsyncDevice
from pydm.data_plugins.plugin import PyDMConnection, PyDMPlugin
from qasync import asyncSlot
from qtpy.QtCore import Qt, Slot

from haven import beamline

from .exceptions import UnknownOphydSignal

log = logging.getLogger(__name__)


# Copied from Typhos project
############################

"""
Module Docstring
"""

logger = logging.getLogger(__name__)

signal_registry = dict()

type Device = AsyncDevice | OphydObject


def register_signal(signal):
    """
    Add a new Signal to the registry.

    The Signal object is kept within ``signal_registry`` for reference by name
    in the :class:`.SignalConnection`. Signals can be added multiple times,
    but only the first register_signal call for each unique signal name
    has any effect.

    Signals can be referenced by their ``name`` attribute or by their
    full dotted path starting from the parent's name.
    """
    # Pick all the name aliases (name, dotted path)
    if signal is signal.root:
        names = (signal.name,)
    else:
        # .dotted_name does not include the root device's name
        names = (
            signal.name,
            ".".join((signal.root.name, signal.dotted_name)),
        )
    # Warn the user if they are adding twice
    for name in names:
        if name in signal_registry:
            # Case 1: harmless re-add
            if signal_registry[name] is signal:
                logger.debug(
                    "The signal named %s is already registered!",
                    name,
                )
            # Case 2: harmful overwrite! Name collision!
            else:
                logger.warning(
                    "A different signal named %s is already registered!",
                    name,
                )
            return
    logger.debug("Registering signal with names %s", names)
    for name in names:
        signal_registry[name] = signal


class SignalConnection(PyDMConnection):
    """
    Connection to monitor an Ophyd Signal.

    This is meant as a generalized connection to any type of Ophyd Signal. It
    handles reporting updates to listeners as well as pushing new values that
    users request in the PyDM interface back to the underlying signal.

    The signal `data_type` is used to inform PyDM on the Python type that the
    signal will expect and emit. It is expected that this type is static
    through the execution of the application.

    Attributes
    ----------
    signal : ophyd.Signal
        Stored signal object.
    """

    supported_types = [int, float, str, np.ndarray]

    def __init__(self, channel, address, protocol=None, parent=None):
        # Create base connection
        super().__init__(channel, address, protocol=protocol, parent=parent)
        self._connection_open: bool = True
        self.signal_type: type | None = None
        self.is_float: bool = False
        self.enum_strs: tuple[str, ...] = ()

        # Collect our signal
        self.signal = self.find_signal(address)
        # Subscribe to updates from Ophyd
        self.value_cid = self.signal.subscribe(
            self.send_new_value,
            event_type=self.signal.SUB_VALUE,
        )
        self.meta_cid = self.signal.subscribe(
            self.send_new_meta,
            event_type=self.signal.SUB_META,
        )
        # Add listener
        self.add_listener(channel)

    def __dtor__(self) -> None:
        self._connection_open = False
        self.close()

    def find_signal(self, address: str) -> Device:
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
        return signal_registry[address]

    def cast(self, value):
        """
        Cast a value to the correct Python type based on ``signal_type``.

        If ``signal_type`` is not set, the result of ``ophyd.Signal.describe``
        is used to determine what the correct Python type for value is. We need
        to be aware of the correct Python type so that we can emit the value
        through the correct signal and convert values returned by the widget to
        the correct type before handing them to Ophyd Signal.
        """
        # If this is the first time we are receiving a new value note the type
        # We make the assumption that signals do not change types during a
        # connection
        if not self.signal_type:
            dtype = self.signal.describe()[self.signal.name]["dtype"]
            # Only way this raises a KeyError is if ophyd is confused
            self.signal_type = _type_map[dtype][0]
            logger.debug(
                "Found signal type %r for %r. Using Python type %r",
                dtype,
                self.signal.name,
                self.signal_type,
            )

        logger.debug("Casting %r to %r", value, self.signal_type)
        if self.enum_strs:
            # signal_type is either int or str
            # use enums to cast type
            if self.signal_type is int:
                # Get the index
                try:
                    value = self.enum_strs.index(value)
                except (TypeError, ValueError, AttributeError):
                    value = int(value)
            elif self.signal_type is str:
                # Get the enum string
                try:
                    value = self.enum_strs[value]
                except (TypeError, ValueError):
                    value = str(value)
            else:
                raise TypeError(
                    f"Invalid combination: enum_strs={self.enum_strs} with signal_type={self.signal_type}"
                )
        elif self.signal_type is np.ndarray:
            value = np.asarray(value)
        else:
            value = self.signal_type(value)
        return value

    @Slot(int)
    @Slot(float)
    @Slot(str)
    @Slot(np.ndarray)
    def put_value(self, new_val):
        """
        Pass a value from the UI to Signal.

        We are not guaranteed that this signal is writeable so catch exceptions
        if they are created. We attempt to cast the received value into the
        reported type of the signal unless it is of type ``np.ndarray``.
        """
        new_val = self.cast(new_val)
        logger.debug("Putting value %r to %r", new_val, self.address)
        self.signal.put(new_val)

    def send_new_value(self, value=None, **kwargs):
        """
        Update the UI with a new value from the Signal.
        """
        if not self._connection_open:
            return

        try:
            value = self.cast(value)
            self.new_value_signal[self.signal_type].emit(value)
        except Exception:
            logger.exception(
                "Unable to update %r with value %r.", self.signal.name, value
            )

    def send_new_meta(
        self,
        connected=None,
        write_access=None,
        severity=None,
        precision=None,
        units=None,
        enum_strs=None,
        **kwargs,
    ):
        """
        Update the UI with new metadata from the Signal.

        Signal metadata updates always send all available metadata, so
        default values to this function will not be sent ever if the signal
        has valid data there.

        We default missing metadata to None and skip emitting in general,
        but for severity we default to NO_ALARM for UI purposes. We don't
        want the UI to assume that anything is in an alarm state.
        """
        if not self._connection_open:
            return

        # Only emit the non-None values
        if connected is not None:
            self.connection_state_signal.emit(connected)
        if write_access is not None:
            self.write_access_signal.emit(write_access)
        if precision is not None:
            if precision <= 0:
                # Help the user a bit by replacing a clear design error
                # with a sensible default
                if self.is_float:
                    # Float precision at 0 is unhelpful
                    precision = 3
                else:
                    # Integer precision can't be negative
                    precision = 0
            self.prec_signal.emit(precision)
        if units is not None:
            self.unit_signal.emit(units)
        if enum_strs is not None:
            self.enum_strings_signal.emit(enum_strs)
            self.enum_strs = enum_strs

        # Special handling for severity
        if severity is None:
            severity = AlarmSeverity.NO_ALARM
        self.new_severity_signal.emit(severity)

    def add_listener(self, channel):
        """
        Add a listener channel to this connection.

        This attaches values input by the user to the `send_new_value` function
        in order to update the Signal object in addition to the default setup
        performed in PyDMConnection.
        """
        # Perform the default connection setup
        logger.debug("Adding %r ...", channel)
        super().add_listener(channel)
        try:
            # Gather the current value
            signal_val = self.signal.get()
            # Gather metadata
            signal_meta = self.signal.metadata
        except Exception:
            logger.exception(
                "Failed to gather proper information "
                "from signal %r to initialize %r",
                self.signal.name,
                channel,
            )
            return
        if isinstance(signal_val, (float, np.floating)):
            # Precision is commonly omitted from non-epics signals
            # Pick a sensible default for displaying floats
            self.is_float = True
            # precision might be missing entirely
            signal_meta.setdefault("precision", 3)
            # precision might be None, which is code for unset
            if signal_meta["precision"] is None:
                signal_meta["precision"] = 3
        else:
            self.is_float = False

        # Report new meta for context, then value
        self.send_new_meta(**signal_meta)
        self.send_new_value(signal_val)
        # If the channel is used for writing to PVs, hook it up to the
        # 'put' methods.
        if channel.value_signal is not None:
            for _typ in self.supported_types:
                try:
                    val_sig = channel.value_signal[_typ]
                    val_sig.connect(self.put_value, Qt.QueuedConnection)
                except KeyError:
                    logger.debug(
                        "%s has no value_signal for type %s", channel.address, _typ
                    )

    def remove_listener(self, channel, destroying=False, **kwargs):
        """
        Remove a listener channel from this connection.

        This removes the `send_new_value` connections from the channel in
        addition to the default disconnection performed in PyDMConnection.
        """
        logger.debug("Removing %r ...", channel)
        # Disconnect put_value from outgoing channel
        if channel.value_signal is not None and not destroying:
            for _typ in self.supported_types:
                try:
                    channel.value_signal[_typ].disconnect(self.put_value, destroying)
                except (KeyError, TypeError):
                    logger.debug(
                        "Unable to disconnect value_signal from %s " "for type %s",
                        channel.address,
                        _typ,
                    )
        # Disconnect any other signals
        super().remove_listener(channel, destroying=destroying, **kwargs)
        logger.debug("Successfully removed %r", channel)

    def close(self):
        """Unsubscribe from the Ophyd signal."""
        self.signal.unsubscribe(self.value_cid)
        self.signal.unsubscribe(self.meta_cid)


class SignalPlugin(PyDMPlugin):
    """Plugin registered with PyDM to handle SignalConnection."""

    protocol = "sig"
    connection_class = SignalConnection

    def add_connection(self, channel):
        """Add a connection to a channel."""
        try:
            # Add a PyDMConnection for the channel
            super().add_connection(channel)
        # There is a chance that we raise an Exception on creation. If so,
        # don't add this to our list of good to go connections. The next
        # attempt we try again.
        except KeyError:
            logger.error(
                "Unable to find signal for %r in signal registry."
                "Use typhos.plugins.register_signal()",
                channel,
            )
        except Exception:
            logger.exception("Unable to create a connection to %r", channel)

    def remove_connection(self, channel, destroying=False):
        try:
            return super().remove_connection(channel, destroying=destroying)
        except RuntimeError as ex:
            # deleteLater() at teardown can raise; let's silence that
            if not str(ex).endswith("has been deleted"):
                raise

            with self.lock:
                self.connections.pop(self.get_connection_id(channel), None)


# Our code is below
###################


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
        log.debug(f"Sending new write access: {self.is_writable}")
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
