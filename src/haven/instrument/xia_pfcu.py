"""Ophyd device support for a set of XIA PFCU-controlled filters.

A PFCUFilterBank controls a set of 4 filters. Optionally, 2 filters in
a filter bank can be used as a shutter.

"""
from enum import IntEnum

from ophyd import Component as Cpt
from ophyd import Device
from ophyd import DynamicDeviceComponent as DCpt, FormattedComponent as FCpt
from ophyd import EpicsSignal, EpicsSignalRO, PVPositionerPC
from apstools.devices.shutters import ShutterBase


class FilterPosition(IntEnum):
    OUT = 0
    IN = 1


class PFCUFilter(PVPositionerPC):
    """A single filter in a PFCU filter bank.

    E.g. 25idc:pfcu0:filter1_mat
    """

    material = Cpt(EpicsSignal, "_mat", kind="config")
    thickness = Cpt(EpicsSignal, "_thick", kind="config")
    notes = Cpt(EpicsSignal, "_other", kind="config")
    setpoint = Cpt(EpicsSignal, "", kind="normal")
    readback = Cpt(EpicsSignalRO, "_RBV", kind="normal")


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
            (FilterPosition.IN, FilterPosition.IN): "unknown"
        }
        current = (self.top_filter.readback.get(), self.bottom_filter.readback.get())
        return states[current]

    def open(self):
        statuses = [
            self.top_filter.setpoint.set(FilterPosition.OUT),
            self.bottom_filter.setpoint.set(FilterPosition.IN),
        ]
        for st in statuses:
            st.wait()

    def close(self):
        statuses = [
            self.top_filter.setpoint.set(FilterPosition.IN),
            self.bottom_filter.setpoint.set(FilterPosition.OUT),
        ]
        for st in statuses:
            st.wait()


class PFCUFilterBank(PVPositionerPC):
    """Parameters
    ==========
    shutters
      Sets of filter numbers to use as shutters. Each entry in
      *shutters* should be a tuple like (top, bottom) where the first
      filter (top) is open when the filter is set to "out".

    """

    num_slots: int = 4

    setpoint = Cpt(EpicsSignal, "config")
    readback = Cpt(EpicsSignalRO, "config_RBV")

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
                        {"top_filter": top, "bottom_filter": bottom},
                    )
                    for idx, (top, bottom) in enumerate(shutters)
                }
            ),
            "filters": DCpt(
                {f"filter{idx}": (PFCUFilter, f"filter{idx}", {}) for idx in filters}
            ),
        }
        # Create any new child class with shutters and filters
        new_cls = type(cls.__name__, (PFCUFilterBank,), comps)
        return object.__new__(new_cls)

    def __init__(cls, *args, shutters=[], **kwargs):
        super().__init__(*args, **kwargs)
