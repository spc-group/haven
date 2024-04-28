"""Ophyd device support for a set of XIA PFCU-controlled filters.

A PFCUFilterBank controls a set of 4 filters. Optionally, 2 filters in
a filter bank can be used as a shutter.

"""

import asyncio
import time
from enum import IntEnum
from typing import Mapping

from apstools.devices.positioner_soft_done import PVPositionerSoftDone
from apstools.devices.shutters import ShutterBase
from ophyd import Component as Cpt
from ophyd import Device
from ophyd import DynamicDeviceComponent as DCpt
from ophyd import EpicsSignal, EpicsSignalRO
from ophyd import FormattedComponent as FCpt
from ophyd import PVPositioner, PVPositionerPC, PseudoPositioner, PositionerBase
from ophyd.signal import InternalSignal, DerivedSignal
from pcdsdevices.signal import MultiDerivedSignal

from .. import exceptions
from .._iconfig import load_config
from .device import aload_devices, make_device
from .motor import HavenMotor


class FilterPosition(IntEnum):
    OUT = 0
    IN = 1


class EnumPositioner(PVPositionerSoftDone):

    @property
    def inposition(self):
        """
        Do readback and setpoint (both from cache) agree by index?

        Returns::

            inposition = readback == setpoint
        """
        # Since this method must execute quickly, do NOT force
        # EPICS CA gets using `use_monitor=False`.
        rb = self.readback.get(as_string=False)
        sp = self.setpoint.get(as_string=False)
        return rb == sp


class PFCUFilter(EnumPositioner):
    """A single filter in a PFCU filter bank.

    E.g. 25idc:pfcu0:filter1_mat
    """

    material = Cpt(EpicsSignal, "_mat", kind="config")
    thickness = Cpt(EpicsSignal, "_thick", kind="config")
    thickness_unit = Cpt(EpicsSignal, "_thick.EGU", kind="config")
    notes = Cpt(EpicsSignal, "_other", kind="config")

    def __init__(self, *args, readback_pv="_RBV", **kwargs):
        super().__init__(*args, readback_pv=readback_pv, **kwargs)


class ShutterStates(IntEnum):
    OPEN = 0
    CLOSED = 1
    TOP_CLOSED = 2
    BOTTOM_CLOSED = 3
    UNKNOWN = 4


shutter_state_map = {
    # (top filter, bottom filter): state
    (FilterPosition.OUT, FilterPosition.IN): ShutterStates.OPEN,
    (FilterPosition.IN, FilterPosition.OUT): ShutterStates.CLOSED,
    (FilterPosition.OUT, FilterPosition.OUT): ShutterStates.BOTTOM_CLOSED,
    (FilterPosition.IN, FilterPosition.IN): ShutterStates.TOP_CLOSED,
}


def shutter_readback(mds: MultiDerivedSignal, items: Mapping) -> int:
    """Calculate the readback back state based on filter PVs."""
    top_signal, bottom_signal = mds.signals
    current = (items[top_signal], items[bottom_signal])
    return shutter_state_map[current]


def shutter_setpoint(mds: MultiDerivedSignal, value: int) -> Mapping:
    """Calculate the filter PVs setpoints."""
    top_signal, bottom_signal = mds.signals
    # Get the states based on the desired shutter position
    try:
        top_position, bottom_position = next(
            key for key, val in shutter_state_map.items() if val == value
        )
    except KeyError:
        raise ValueError(value)
    items = {top_signal: top_position, bottom_signal: bottom_position}
    return items


class PFCUShutter(PVPositionerPC):
    """A shutter made of two PFCU4 filters.

    Parameters
    ==========
    top_filter
      The PV for the filter that is open when the filter is set to
      "out".
    bottom_filter
      The PV for the filter that is open when the filter is set to
      "in".

    """

    readback = Cpt(
        MultiDerivedSignal,
        attrs=["top_filter.readback", "bottom_filter.readback"],
        calculate_on_get=shutter_readback,
    )
    setpoint = Cpt(
        MultiDerivedSignal,
        attrs=["top_filter.setpoint", "bottom_filter.setpoint"],
        calculate_on_put=shutter_setpoint,
        calculate_on_get=shutter_readback,
    )

    top_filter = FCpt(PFCUFilter, "{self.prefix}filter{self._top_filter}")
    bottom_filter = FCpt(PFCUFilter, "{self.prefix}filter{self._bottom_filter}")

    def __init__(self, *args, top_filter: str, bottom_filter: str, **kwargs):
        self._top_filter = top_filter
        self._bottom_filter = bottom_filter
        super().__init__(
            *args, limits=(ShutterStates.OPEN, ShutterStates.CLOSED), **kwargs
        )


class PFCUShutterSignal(DerivedSignal):
    def _mask(self, pos):
        num_filters = 4
        return 1 << (num_filters - pos)

    def top_mask(self):
        return self._mask(self.parent._top_filter)

    def bottom_mask(self):
        return self._mask(self.parent._bottom_filter)

    def forward(self, value):
        """Convert shutter state to filter bank state."""
        # Bit masking to set both blades together
        old_bits = self.derived_from.parent.readback.get(as_string=False)
        if value == ShutterStates.OPEN:
            open_bits = self.bottom_mask()
            close_bits = self.top_mask()
        elif value == ShutterStates.CLOSED:
            close_bits = self.bottom_mask()
            open_bits = self.top_mask()
        else:
            raise ValueError(bin(value))
        new_bits = (old_bits | open_bits) & (0b1111 - close_bits)
        return new_bits

    def inverse(self, value):
        """Convert filter bank state to shutter state."""
        # Determine which filters are open and closed
        top_position = int(bool(value & self.top_mask()))
        bottom_position = int(bool(value & self.bottom_mask()))
        result = shutter_state_map[(top_position, bottom_position)]
        return result


class PFCUFastShutter(PVPositionerPC):
    """A shutter made of two PFCU4 filters.

    For faster operation, both filters will be moved at the same
    time. That means this shutter must be a sub-component of a
    :py:class:`PFCUFilterBank`.

    Parameters
    ==========
    top_filter
      The PV for the filter that is open when the filter is set to
      "out".
    bottom_filter
      The PV for the filter that is open when the filter is set to
      "in".

    """

    readback = Cpt(PFCUShutterSignal, derived_from="parent.parent.readback")
    setpoint = Cpt(PFCUShutterSignal, derived_from="parent.parent.setpoint")

    top_filter = FCpt(PFCUFilter, "{self.prefix}filter{self._top_filter}")
    bottom_filter = FCpt(PFCUFilter, "{self.prefix}filter{self._bottom_filter}")

    def __init__(self, *args, top_filter: str, bottom_filter: str, **kwargs):
        self._top_filter = top_filter
        self._bottom_filter = bottom_filter
        super().__init__(
            *args, limits=(ShutterStates.OPEN, ShutterStates.CLOSED), **kwargs
        )

    #     # Subscriptions for updating the readback value
    #     self.top_filter.readback.subscribe(self.update_readback_signal)
    #     self.bottom_filter.readback.subscribe(self.update_readback_signal)

    # def move(self, position, moved_cb=None, timeout=None):
    #     print(f"Moving to {position}")

    # def update_readback_signal(self, *args, **kwargs):
    #     state = self.state
    #     # Set the derived signals
    #     statuses = [
    #         self.readback.set(state, internal=True),
    #         self.is_open.set(int(state == "open"), internal=True),
    #         self.is_closed.set(int(state == "closed"), internal=True),
    #     ]
    #     # Wait for the signals to be updated
    #     for st in statuses:
    #         st.wait(timeout=5)

    # @property
    # def state(self):
    #     return self._state()

    # def _state(self, **kwargs):
    #     states = {
    #         # (top filter, bottom filter): state
    #         (FilterPosition.OUT, FilterPosition.IN): "open",
    #         (FilterPosition.IN, FilterPosition.OUT): "closed",
    #         (FilterPosition.OUT, FilterPosition.OUT): "unknown",
    #         (FilterPosition.IN, FilterPosition.IN): "unknown",
    #     }
    #     current = (
    #         self.top_filter.readback.get(**kwargs),
    #         self.bottom_filter.readback.get(**kwargs),
    #     )
    #     return states[current]

    # def filter_bank(self):
    #     try:
    #         parent = self.parent.parent
    #         assert isinstance(parent, PFCUFilterBank)
    #     except (AttributeError, AssertionError):
    #         return None
    #     return parent

    # def _mask(self, pos):
    #     num_filters = 4
    #     return 1 << (num_filters - pos)

    # def top_mask(self):
    #     return self._mask(self._top_filter)

    # def bottom_mask(self):
    #     return self._mask(self._bottom_filter)

    # def open(self):
    #     # See if we have access to the whole filter bank, or just this filter
    #     filter_bank = self.filter_bank()
    #     if filter_bank is None:
    #         # No filter bank, so just set the blades individually
    #         self.top_filter.set(FilterPosition.OUT).wait()
    #         self.bottom_filter.set(FilterPosition.IN).wait()
    #     else:
    #         # We have a filter bank, so set both blades together
    #         old_bits = filter_bank.readback.get(as_string=False)
    #         new_bits = (old_bits | self.bottom_mask()) & (0b1111 - self.top_mask())
    #         filter_bank.set(new_bits).wait()

    # def close(self):
    #     # See if we have access to the whole filter bank, or just this filter
    #     filter_bank = self.filter_bank()
    #     if filter_bank is None:
    #         self.top_filter.set(FilterPosition.IN).wait()
    #         self.bottom_filter.set(FilterPosition.OUT).wait()
    #     else:
    #         # We have a filter bank, so set both blades together
    #         old_bits = filter_bank.readback.get(as_string=False)
    #         new_bits = (old_bits | self.top_mask()) & (0b1111 - self.bottom_mask())
    #         filter_bank.set(new_bits).wait()

    # def get(self, **kwargs):
    #     return self._state(**kwargs)


class PFCUFilterBank(EnumPositioner):
    """Parameters
    ==========
    shutters
      Sets of filter numbers to use as shutters. Each entry in
      *shutters* should be a tuple like (top, bottom) where the first
      filter (top) is open when the filter is set to "out".

    """

    num_slots: int = 4

    def __new__(cls, *args, shutters=[], **kwargs):
        # Determine which filters to use as filters vs shutters
        all_shutters = [v for shutter in shutters for v in shutter]
        filters = [
            idx for idx in range(1, cls.num_slots + 1) if idx not in all_shutters
        ]
        # Create device components for filters and shutters
        comps = {
            "shutters": DCpt(
                {
                    f"shutter_{idx}": (
                        PFCUShutter,
                        "",
                        {
                            "top_filter": top,
                            "bottom_filter": bottom,
                            "labels": {"shutters"},
                        },
                    )
                    for idx, (top, bottom) in enumerate(shutters)
                }
            ),
            "filters": DCpt(
                {
                    f"filter{idx}": (
                        PFCUFilter,
                        f"filter{idx}",
                        {"labels": {"filters"}},
                    )
                    for idx in filters
                }
            ),
        }
        # Create any new child class with shutters and filters
        new_cls = type(cls.__name__, (PFCUFilterBank,), comps)
        return object.__new__(new_cls)

    def __init__(
        cls,
        *args,
        shutters=[],
        readback_pv="config_RBV",
        setpoint_pv="config",
        **kwargs,
    ):
        super().__init__(
            *args, readback_pv=readback_pv, setpoint_pv=setpoint_pv, **kwargs
        )


def load_xia_pfcu4_coros(config=None):
    if config is None:
        config = load_config()
    # Read the filter bank configurations from the config file
    for name, cfg in config.get("pfcu4", {}).items():
        try:
            prefix = cfg["prefix"]
            shutters = cfg.get("shutters", [])
        except KeyError as ex:
            raise exceptions.UnknownDeviceConfiguration(
                f"Device {name} missing '{ex.args[0]}': {cfg}"
            ) from ex
        # Make the device
        yield make_device(
            PFCUFilterBank,
            prefix=prefix,
            name=name,
            shutters=shutters,
            labels={"filter_banks"},
        )


def load_xia_pfcu4s(config=None):
    asyncio.run(aload_devices(*load_xia_pfcu4_coros(config=config)))
