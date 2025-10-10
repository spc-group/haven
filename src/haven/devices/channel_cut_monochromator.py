from ophyd_async.core import StandardReadable, StandardReadableFormat
from ophyd_async.epics.core import epics_signal_r, epics_signal_rw

from haven.devices.motor import Motor


class ChannelCutMonochromator(StandardReadable):
    """A dual-crystal mono where the geometry of the two crystals is fixed.

    This type of mono would often be used as a secondary monochromator
    to improve energy resolution.

    """

    _ophyd_labels_ = {"monochromators"}

    def __init__(self, name="", *args, prefix: str, vertical_motor: str, **kwargs):
        """Parameters
        ==========
        name
          The name given to this device's data keys.
        prefix
          The PV prefix for the mono support.
        vertical_motor
          The PV prefix for the motor record controlling the vertical
          position of the mono.

        """
        with self.add_children_as_readables():
            self.bragg = Motor(f"{prefix}bragg")
            self.energy = Motor(f"{prefix}energy")
            self.beam_offset = epics_signal_r(float, f"{prefix}offset")
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            self.d_spacing = epics_signal_r(
                float,
                read_pv=f"{prefix}energyC1",
                # write_pv=f"{prefix}dspacing"
            )
            self.gap = epics_signal_r(
                float,
                read_pv=f"{prefix}energyC4",
                # write_pv=f"{prefix}gap",
            )
            self.bragg_direction = epics_signal_rw(
                float,
                read_pv=f"{prefix}energyC2",
                # write_pv=f"{prefix}bragg_dir",
            )
            self.bragg_offset = epics_signal_rw(
                float,
                read_pv=f"{prefix}energyC3",
                write_pv=f"{prefix}bragg_offset",
            )
        # Vertical motor isn't really meant for scanning, so only save configuration
        self.vertical = Motor(vertical_motor)
        self.add_readables(
            [
                self.vertical.user_readback,
                self.vertical.description,
                self.vertical.offset_dir,
                self.vertical.velocity,
                self.vertical.offset,
                self.vertical.motor_egu,
            ],
            StandardReadableFormat.CONFIG_SIGNAL,
        )
        super().__init__(name=name, *args, **kwargs)
