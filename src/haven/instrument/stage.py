from ophyd import (
    Device,
    FormattedComponent as FCpt,
    EpicsMotor,
    Component as Cpt,
    Signal,
    SignalRO,
    Kind,
    EpicsSignal,
)
from apstools.synApps.asyn import AsynRecord

from .instrument_registry import registry
from .._iconfig import load_config


@registry.register
class XYStage(Device):
    """An XY stage with two motors operating in orthogonal directions.

    Vertical and horizontal are somewhat arbitrary, but are expected
    to align with the orientation of a camera monitoring the stage.

    Parameters
    ==========

    pv_vert
      The suffix to the PV for the vertical motor.
    pv_horiz
      The suffix to the PV for the horizontal motor.
    """

    vert = FCpt(EpicsMotor, "{prefix}{pv_vert}", labels={"motors"})
    horiz = FCpt(EpicsMotor, "{prefix}{pv_horiz}", labels={"motors"})

    def __init__(
        self,
        prefix: str,
        pv_vert: str,
        pv_horiz: str,
        labels={"stages"},
        *args,
        **kwargs,
    ):
        self.pv_vert = pv_vert
        self.pv_horiz = pv_horiz
        super().__init__(prefix, labels=labels, *args, **kwargs)


def load_stages(config=None):
    if config is None:
        config = load_config()
    for name, stage_data in config.get("stage", {}).items():
        XYStage(
            name=name,
            prefix=stage_data["prefix"],
            pv_vert=stage_data["pv_vert"],
            pv_horiz=stage_data["pv_horiz"],
        )


class AerotechFlyer(EpicsMotor):
    """Allow an Aerotech stage to fly-scan via the Ophyd FlyerInterface.

    Set *start_position*, *stop_position*, and *step_size* in units of
    the motor record (.EGU), and *dwell_time* in seconds. Then the
    remaining components will be calculated accordingly.

    All position or distance components are assumed to be in motor
    record engineering units, unless preceded with "encoder_", in
    which case they are in units of encoder pulses based on the
    encoder resolution.

    Parameters
    ==========
    axis
      The label used by the aerotech controller to refer to this
      axis. Examples include "@0" or "X".
    encoder
      The number of the encoder to track when fly-scanning with this
      device.

    Components
    ==========
    start_position
      Where the fly scan begins
    stop_position
      Where the fly scan ends
    step_size
      How much space desired between points. Note this is not
      guaranteed and may be adjusted to match the encoder resolution
      of the stage.
    dwell_time
      How long to take, in seconds, moving between points.
    slew_speed
      How fast to move the stage. Calculated from the remaining
      components.

    """

    # Internal encoder in the Ensemble to track for flying
    encoder: int

    # Desired fly parameters
    start_position = Cpt(Signal, name="start_position", kind=Kind.config)
    end_position = Cpt(Signal, name="end_position", kind=Kind.config)
    step_size = Cpt(Signal, name="step_size", kind=Kind.config)
    dwell_time = Cpt(Signal, name="dwell_time", kind=Kind.config)

    # Calculated signals
    slew_speed = Cpt(Signal, kind=Kind.config)
    taxi_start = Cpt(Signal, kind=Kind.config)
    taxi_end = Cpt(Signal, kind=Kind.config)
    encoder_step_size = Cpt(Signal, kind=Kind.config)

    def __init__(self, *args, axis: str, encoder: int, **kwargs):
        super().__init__(*args, **kwargs)
        self.axis = axis
        self.encoder = encoder
        # Set up auto-calculations for the flyer
        self.start_position.subscribe(self._update_fly_params)

    def _update_fly_params(self, *args, **kwargs):
        """Calculate new fly-scan parameters based on signal values."""
        print("To-do: calculate fly-scanning parameters.")

    def send_command(self, cmd: str):
        """Send commands directly to the aerotech ensemble controller.

        Returns
        =======
        status
          The Ophyd status object for this write.

        """
        status = self.parent.asyn.ascii_output.set(cmd)
        return status

    def enable_pso(self):
        num_axis = 1
        statuses = [
            # Make sure the PSO control is off
            self.send_command(f"PSOCONTROL {self.axis} RESET"),
            # Set the output to occur from the I/O terminal on the
            # controller
            self.send_command(f"PSOOUTPUT {self.axis} CONTROL {num_axis}"),
            # Set a pulse 10 us long, 20 us total duration, so 10 us
            # on, 10 us off
            self.send_command(f"PSOPULSE {self.axis} TIME 20,10"),
            # Set the pulses to only occur in a specific window
            self.send_command(f"PSOOUTPUT {self.axis} PULSE WINDOW MASK"),
            # Set which encoder we will use.  3 = the MXH (encoder
            # multiplier) input. For Ensemble lab, 6 is horizontal encoder
            self.send_command(f"PSOTRACK {self.axis} INPUT {self.encoder}"),
            # Set the distance between pulses in encoder counts
            self.send_command(f"PSODISTANCE {self.axis} FIXED {self.encoder_step_size.get()}"),
            # Which encoder is being used to calculate whether we are
            # in the window.
            self.send_command(f"PSOWINDOW {self.axis} {num_axis} INPUT {self.encoder}"),
            # Calculate window function parameters. Must be in encoder
            # counts, and is referenced from the stage location where
            # we arm the PSO
            self.send_command(
                f"PSOWINDOW {self.axis} {num_axis} RANGE "
                f"{self.taxi_start.get()},{self.taxi_end.get()}"
            ),
        ]

        for status in statuses:
            status.wait()


class AerotechFlyStage(XYStage):
    """An XY stage for an Aerotech stage with fly-scanning capabilities.

    Parameters
    ==========

    pv_vert
      The suffix to the PV for the vertical motor.
    pv_horiz
      The suffix to the PV for the horizontal motor.
    """

    vert = FCpt(
        AerotechFlyer,
        "{prefix}{pv_vert}",
        axis="@1",
        encoder=6,
        labels={"motors", "flyers"},
    )
    horiz = FCpt(
        AerotechFlyer,
        "{prefix}{pv_horiz}",
        axis="@0",
        encoder=7,
        labels={"motors", "flyers"},
    )
    asyn = Cpt(AsynRecord, ":asynEns", name="async", labels={"asyns"})
