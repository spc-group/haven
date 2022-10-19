from ophyd import (
    Device,
    EpicsMotor,
    EpicsSignal,
    Component as Cpt,
    FormattedComponent as FCpt,
    Kind,
)
from enum import IntEnum


from .scaler_triggered import ScalerTriggered
from .instrument_registry import registry
from .._iconfig import load_config
from ..signal import Signal, SignalRO


iconfig = load_config()

pv_prefix = iconfig["fluorescence_detectors"]["vortex"]["pv_prefix"]


class XspressDetector(ScalerTriggered, Device):
    """A fluorescence detector plugged into an Xspress3 readout."""

    num_frames = Cpt(EpicsSignal, "NumImages", kind=Kind.config)
    trigger_mode = Cpt(EpicsSignal, "TriggerMode", kind=Kind.config)
    acquire = Cpt(EpicsSignal, "Acquire", kind=Kind.omitted)
    erase = Cpt(EpicsSignal, "Erase", kind=Kind.omitted)

    class erase_states(IntEnum):
        DONE = 0
        ERASE = 1

    class acquire_states(IntEnum):
        DONE = 0
        ACQUIRE = 1

    class mode(IntEnum):
        SOFTWARE = 0
        INTERNAL = 1
        IDC = 2
        TTL_VETO_ONLY = 3
        TTL_BOTH = 4
        LVDS_VETO_ONLY = 5
        LVDS_BOTH = 6

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stage_sigs[self.erase] = self.erase_states.ERASE
        self.stage_sigs[self.trigger_mode] = self.mode.TTL_VETO_ONLY
        self.stage_sigs[self.acquire] = self.acquire_states.ACQUIRE

    @property
    def stage_num_frames(self):
        """How many frames to prepare for when staging this detector."""
        return self.stage_sigs.get(self.num_frames, 1)

    @stage_num_frames.setter
    def stage_num_frames(self, val):
        self.stage_sigs[self.num_frames] = val


vortex_single = XspressDetector(
    pv_prefix,
    name="vortex_single",
    labels={
        "fluorescence_detectors",
    },
)
