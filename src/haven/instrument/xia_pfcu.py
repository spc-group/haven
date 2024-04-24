"""Ophyd device support for a set of XIA PFCU-controlled filters.

A PFCUFilterBank controls a set of 4 filters. Optionally, 2 filters in
a filter bank can be used as a shutter.

"""

import asyncio
import time
from enum import IntEnum

from apstools.devices.positioner_soft_done import PVPositionerSoftDone
from apstools.devices.shutters import ShutterBase
from ophyd import Component as Cpt
from ophyd import Device
from ophyd import DynamicDeviceComponent as DCpt
from ophyd import EpicsSignal, EpicsSignalRO
from ophyd import FormattedComponent as FCpt
from ophyd import PVPositioner, PVPositionerPC

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


class PFCUShutter(ShutterBase):
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

    top_filter = FCpt(PFCUFilter, "{self.prefix}filter{self._top_filter}")
    bottom_filter = FCpt(PFCUFilter, "{self.prefix}filter{self._bottom_filter}")

    def __init__(self, *args, top_filter: str, bottom_filter: str, **kwargs):
        self._top_filter = top_filter
        self._bottom_filter = bottom_filter
        super().__init__(*args, **kwargs)

    @property
    def state(self):
        states = {
            # (top filter, bottom filter): state
            (FilterPosition.OUT, FilterPosition.IN): "open",
            (FilterPosition.IN, FilterPosition.OUT): "close",
            (FilterPosition.OUT, FilterPosition.OUT): "unknown",
            (FilterPosition.IN, FilterPosition.IN): "unknown",
        }
        current = (self.top_filter.readback.get(), self.bottom_filter.readback.get())
        return states[current]

    def filter_bank(self):
        try:
            parent = self.parent.parent
            assert isinstance(parent, PFCUFilterBank)
        except (AttributeError, AssertionError):
            return None
        return parent

    def _mask(self, pos):
        num_filters = 4
        return 1 << (num_filters - pos)

    def top_mask(self):
        return self._mask(self._top_filter)

    def bottom_mask(self):
        return self._mask(self._bottom_filter)

    def open(self):
        # See if we have access to the whole filter bank, or just this filter
        filter_bank = self.filter_bank()
        if filter_bank is None:
            # No filter bank, so just set the blades individually
            self.top_filter.set(FilterPosition.OUT).wait()
            self.bottom_filter.set(FilterPosition.IN).wait()
        else:
            # We have a filter bank, so set both blades together
            old_bits = filter_bank.readback.get(as_string=False)
            new_bits = (old_bits | self.top_mask()) & (0b1111 - self.bottom_mask())
            filter_bank.setpoint.set(new_bits).wait()

    def close(self):
        # See if we have access to the whole filter bank, or just this filter
        filter_bank = self.filter_bank()
        if filter_bank is None:
            self.top_filter.set(FilterPosition.IN).wait()
            self.bottom_filter.set(FilterPosition.OUT).wait()
        else:
            # We have a filter bank, so set both blades together
            old_bits = filter_bank.readback.get(as_string=False)
            new_bits = (old_bits | self.bottom_mask()) & (0b1111 - self.top_mask())
            filter_bank.setpoint.set(new_bits).wait()


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
                    f"shutter{idx}": (
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
