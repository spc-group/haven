from ophyd import (
    mca,
    Device,
    EpicsSignal,
    Component as Cpt,
    Kind,
)
from enum import IntEnum


from .scaler_triggered import ScalerTriggered
from .instrument_registry import registry
from .._iconfig import load_config
from .. import exceptions


@registry.register
class DxpDetectorBase(mca.EpicsDXPMultiElementSystem):
    """A fluorescence detector based on XIA-DXP XMAP electronics.

    By itself, this class has no multi-channel-analyzers, and so will
    not really be very useful. It should have
    ``ophyd.mca.EpicsMCARecord`` objects added as components.
    
    """


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


def load_dxp_detector(device_name, prefix, num_elements):
    # Build the mca components
    mca_names = [f"mca{n}" for n in range(1, num_elements+1)]
    mcas = {mname: Cpt(mca.EpicsMCARecord, suffix=mname, name=mname)
            for mname in mca_names}
    # Create a dynamic subclass
    class_name = device_name.title().replace("_", "")
    parent_classes = (DxpDetectorBase,)
    Cls = type(class_name, parent_classes, mcas)
    det = Cls(prefix=f"{prefix}:", name=device_name)
    

def load_fluorescence_detectors(config=None):
    # Get the detector definitions from config files
    if config is None:
        config = load_config()
    for name, cfg in config.get("fluorescence_detector", {}).items():
        if "prefix" not in cfg.keys():
            continue
        # Build the detector device
        if cfg["electronics"] == "dxp":
            load_dxp_detector(device_name=name, prefix=cfg["prefix"],
                              num_elements=cfg["num_elements"])
        else:
            msg = f"Electronics '{cfg['electronics']}' for {name} not supported."
            raise exceptions.UnknownDeviceConfiguration(msg)
        
