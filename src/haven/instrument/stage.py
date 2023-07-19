import threading
import time
import logging

from ophyd import (
    Device,
    FormattedComponent as FCpt,
    EpicsMotor,
    Component as Cpt,
    Signal,
    SignalRO,
    Kind,
    EpicsSignal,
    flyers,
)
from ophyd.status import SubscriptionStatus
from apstools.synApps.asyn import AsynRecord
import pint
import numpy as np

from .instrument_registry import registry
from .._iconfig import load_config


log = logging.getLogger()


ureg = pint.UnitRegistry()


class AerotechAsyn(AsynRecord):
    binary_output = Cpt(EpicsSignal, ".BOUT", kind="normal", string=True)


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


class AerotechFlyer(EpicsMotor, flyers.FlyerInterface):
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

    axis: str
    pso_positions: np.ndarray = None
    # Internal encoder in the Ensemble to track for flying
    encoder: int
    encoder_direction: int = 1

    # Extra motor record components
    encoder_resolution = Cpt(EpicsSignal, ".ERES", kind=Kind.config)

    # Desired fly parameters
    start_position = Cpt(Signal, name="start_position", kind=Kind.config)
    end_position = Cpt(Signal, name="end_position", kind=Kind.config)
    step_size = Cpt(Signal, name="step_size", value=1, kind=Kind.config)
    dwell_time = Cpt(Signal, name="dwell_time", value=1, kind=Kind.config)

    # Calculated signals
    slew_speed = Cpt(Signal, value=1, kind=Kind.config)
    taxi_start = Cpt(Signal, kind=Kind.config)
    taxi_end = Cpt(Signal, kind=Kind.config)
    encoder_step_size = Cpt(Signal, kind=Kind.config)
    encoder_window_start = Cpt(Signal, kind=Kind.config)
    encoder_window_end = Cpt(Signal, kind=Kind.config)

    # Status signals
    is_flying = Cpt(Signal, kind=Kind.omitted)

    def __init__(self, *args, axis: str, encoder: int, **kwargs):
        super().__init__(*args, **kwargs)
        self.axis = axis
        self.encoder = encoder
        # Set up auto-calculations for the flyer
        self.start_position.subscribe(self._update_fly_params)
        self.end_position.subscribe(self._update_fly_params)
        self.step_size.subscribe(self._update_fly_params)
        self.dwell_time.subscribe(self._update_fly_params)

    def kickoff(self):
        """Start a flyer

        The status object return is marked as done once flying
        has started.

        Returns
        -------
        kickoff_status : StatusBase
            Indicate when flying has started.

        """

        def check_flying(*args, old_value, value, **kwargs) -> bool:
            "Check if taxiing is complete and flying has begun."
            return not bool(old_value) and bool(value)

        # Status object is complete when flying has started
        status = SubscriptionStatus(self.is_flying, check_flying)
        # Start the flying process
        th = threading.Thread(target=self.fly)
        th.start()
        # Save thread to avoid garbage-collection
        self.th = th
        return status

    def complete(self):
        """Wait for flying to be complete.

        This can either be a question ("are you done yet") or a
        command ("please wrap up") to accommodate flyers that have a
        fixed trajectory (ex. high-speed raster scans) or that are
        passive collectors (ex MAIA or a hardware buffer).

        In either case, the returned status object should indicate when
        the device is actually finished flying.

        Returns
        -------
        complete_status : StatusBase
            Indicate when flying has completed
        """

        # Prepare a callback to check when the motor has stopped moving
        def check_flying(*args, old_value, value, **kwargs) -> bool:
            "Check if flying is complete."
            return not bool(value)

        # Status object is complete when flying has started
        status = SubscriptionStatus(self.is_flying, check_flying)
        return status

    def fly(self):
        self.taxi()
        # Start the trajectory
        flight_status = self.move(self.taxi_end.get())
        self.is_flying.set(True).wait()
        # Wait for the landing
        flight_status.wait()
        self.is_flying.set(False).wait()
        self.disable_pso()

    def taxi(self):
        # Move motor to the scan start point
        motor_move = self.move(self.start_position.get(), wait=False)
        # Initalize the PSO
        self.enable_pso()
        # Arm the PSO
        motor_move.wait()
        self.arm_pso()
        # Move the motor to the taxi position
        self.move(self.taxi_start.get())
        # Set the speed on the motor
        self.velocity.set(self.slew_speed.get()).wait()

    def stage(self, *args, **kwargs):
        self.old_velocity = self.velocity.get()
        super().stage(*args, **kwargs)

    def unstage(self, *args, **kwargs):
        self.velocity.set(self.old_velocity).wait()
        return super().unstage(*args, **kwargs)

    @property
    def motor_egu_pint(self):
        egu = ureg(self.motor_egu.get())
        return egu

    def _update_fly_params(self, *args, **kwargs):
        """Calculate new fly-scan parameters based on signal values.

        Implementation courtesy of Alan Kastengren.

        Computes several parameters describing the fly scan motion.
        These include the actual start position of the motor, the
        actual distance (in encoder counts and distance) between PSO
        pulses, the end position of the motor, and where PSO pulses
        are expected to occcur.  This code ensures that each PSO delta
        is an integer number of encoder counts, since this is how the
        PSO triggering works in hardware.

        These calculations are for MCS scans, where for N bins we need
        N+1 pulses.

        Several fields are set in the class:

        direction
          1 if we are moving positive in user coordinates, −1 if
          negative
        overall_sense
          is our fly motion + or - with respect to encoder counts
        delta_encoder_counts
          integer number of encoder counts per PSO delta
        delta_egu
          delta_encoder_counts in engineering units.  May not = delta
        motor_start
          where motor will be to start motion.  Accounts for accel
          distance
        motor_end
          where motor will stop motion.  Accounts for decel distance
        actual_end
          center of last data point.  May not = req_end due to integer
          delta_encoder_counts
        PSO_positions
          array of places where PSO pulses should occur

        """
        window_buffer = 5
        # Grab any neccessary signals For calculation
        start_position = self.start_position.get()
        end_position = self.end_position.get()
        dwell_time = self.dwell_time.get()
        step_size = self.step_size.get()
        encoder_resolution = self.encoder_resolution.get()
        motor_accel = self.acceleration.get()
        egu = self.motor_egu.get()
        # Check for sane values
        if dwell_time == 0:
            log.warning(f'{self} dwell_time is zero. Could not update fly scan parameters.')
            return
        if encoder_resolution == 0:
            log.warning(f'{self} encoder resolution is zero. Could not update fly scan parameters.')
            return
        if motor_accel <= 0:
            log.warning(f'{self} acceleration is non-positive. Could not update fly scan parameters.')
            return
        # Determine the desired direction of travel and overal sense
        # +1 when moving in +1 encoder direction, -1 if else
        direction = 1 if start_position < end_position else -1
        overall_sense = direction * self.encoder_direction
		# Calculate the step size in encoder steps
        encoder_step_size = round(step_size / encoder_resolution)
        self.encoder_step_size.set(encoder_step_size).wait()
        delta_egu = egu * encoder_step_size
        slew_speed = (step_size / dwell_time)
        # Determine taxi distance to accelerate to req speed, v^2/(2*a) = d
        # x3 for margin of error
        taxi_dist = slew_speed ** 2 / (2 * motor_accel) * 3
        taxi_start =  start_position - (direction * taxi_dist)
        taxi_end =  end_position + (direction * taxi_dist)
        # Calculate encoder counts within the requested window of the scan
        encoder_window_start = taxi_dist / encoder_step_size
        encoder_window_end = (taxi_dist + abs(end_position - start_position)) / encoder_step_size
        #Create a list of PSO positions and grab the end to find end of scan
        self.pso_positions = list(np.arange(start_position, end_position, (direction*step_size)))
        actual_end = self.pso_positions[-1]
        # Set all the calculated variables
        self.slew_speed.set(slew_speed).wait()
        self.taxi_start.set(taxi_start).wait()
        self.taxi_end.set(taxi_end).wait()
        self.encoder_window_start.set(encoder_window_start).wait()
        self.encoder_window_end.set(encoder_window_end).wait()
        #self.pso_positions.set(pso_positions).wait()

    def send_command(self, cmd: str):
        """Send commands directly to the aerotech ensemble controller.

        Returns
        =======
        status
          The Ophyd status object for this write.

        """
        status = self.parent.asyn.ascii_output.set(cmd, settle_time=0.1)
        status.wait()
        return status

    def disable_pso(self):
        self.send_command(f"PSOCONTROL {self.axis} OFF")

    def enable_pso(self):
        num_axis = 1
        # Make sure the PSO control is off
        self.send_command(f"PSOCONTROL {self.axis} RESET")
        # Set the output to occur from the I/O terminal on the
        # controller
        self.send_command(f"PSOOUTPUT {self.axis} CONTROL {num_axis}")
        # Set a pulse 10 us long, 20 us total duration, so 10 us
        # on, 10 us off
        self.send_command(f"PSOPULSE {self.axis} TIME 20,10")
        # Set the pulses to only occur in a specific window
        self.send_command(f"PSOOUTPUT {self.axis} PULSE WINDOW MASK")
        # Set which encoder we will use.  3 = the MXH (encoder
        # multiplier) input. For Ensemble lab, 6 is horizontal encoder
        self.send_command(f"PSOTRACK {self.axis} INPUT {self.encoder}")
        # Set the distance between pulses in encoder counts
        self.send_command(
            f"PSODISTANCE {self.axis} FIXED {self.encoder_step_size.get()}"
        )
        # Which encoder is being used to calculate whether we are
        # in the window.
        self.send_command(f"PSOWINDOW {self.axis} {num_axis} INPUT {self.encoder}")
        # Calculate window function parameters. Must be in encoder
        # counts, and is referenced from the stage location where
        # we arm the PSO
        self.send_command(
            f"PSOWINDOW {self.axis} {num_axis} RANGE "
            f"{self.encoder_window_start.get()},{self.encoder_window_end.get()}"
        )

    def arm_pso(self):
        self.send_command(f"PSOCONTROL {self.axis} ARM")


class AerotechFlyStage(XYStage):
    """An XY stage for an Aerotech stage with fly-scanning capabilities.

    Parameters
    ==========

    pv_vert
      The suffix to the PV for the vertical motor.
    pv_horiz
      The suffix to the PV for the horizontal motor.
    """
    horiz = FCpt(
        AerotechFlyer,
        "{prefix}{pv_horiz}",
        axis="@0",
        encoder=6,
        labels={"motors", "flyers"},
    )
    vert = FCpt(
        AerotechFlyer,
        "{prefix}{pv_vert}",
        axis="@1",
        encoder=7,
        labels={"motors", "flyers"},
    )
    asyn = Cpt(AerotechAsyn, ":asynEns", name="async", labels={"asyns"})


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
