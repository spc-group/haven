from ophyd_async.core import StandardReadable, StandardReadableFormat
from ophyd_async.epics.core import epics_signal_r, epics_signal_rw

from haven.devices.motor import Motor


class ChannelCutMonochromator(StandardReadable):
    """A dual-crystal mono where the geometry of the two crystals is fixed.

    This type of mono would often be used as a secondary monochromator
    to improve energy resolution.

    """

    _ophyd_labels_ = {"monochromators"}

    def __init__(self, name="", *args, prefix: str, **kwargs):
        with self.add_children_as_readables():
            self.bragg = Motor(f"{prefix}bragg")
            self.energy = Motor(f"{prefix}energy")
            self.beam_offset = epics_signal_r(float, f"{prefix}offset")
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            self.d_spacing = epics_signal_rw(
                float, read_pv=f"{prefix}energyC1", write_pv=f"{prefix}dspacing"
            )
            self.gap = epics_signal_rw(
                float, read_pv=f"{prefix}energyC4", write_pv=f"{prefix}gap"
            )
            self.bragg_direction = epics_signal_rw(
                float, read_pv=f"{prefix}energyC2", write_pv=f"{prefix}bragg_dir"
            )
            self.bragg_offset = epics_signal_rw(
                float, read_pv=f"{prefix}energyC3", write_pv=f"{prefix}bragg_offset"
            )
        super().__init__(name=name, *args, **kwargs)
