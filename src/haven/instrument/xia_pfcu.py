"""Ophyd device support for a set of XIA PFCU-controlled filters.

A PFCUFilterBank controls a set of 4 filters. Optionally, 2 filters in
a filter bank can be used as a shutter.

"""

from ophyd import Component as Cpt
from ophyd import Device
from ophyd import DynamicDeviceComponent as DCpt
from ophyd import EpicsSignal, EpicsSignalRO, PVPositionerPC


class PFCUFilterShutter(Device):
    def __init__(self, *args, top_shutter: str, bottom_shutter: str, **kwargs):
        super().__init__(*args, **kwargs)


class PFCUFilter(PVPositionerPC):
    """A single filter in a PFCU filter bank.

    E.g. 25idc:pfcu0:filter1_mat
    """

    material = Cpt(EpicsSignal, "_mat", kind="config")
    thickness = Cpt(EpicsSignal, "_thick", kind="config")
    notes = Cpt(EpicsSignal, "_other", kind="config")
    setpoint = Cpt(EpicsSignal, "", kind="normal")
    readback = Cpt(EpicsSignalRO, "_RBV", kind="normal")


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
                        PFCUFilterShutter,
                        "",
                        {"top_shutter": top, "bottom_shutter": bottom},
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
