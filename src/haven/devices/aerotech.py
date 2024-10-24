import logging

import numpy as np
import pint
from ophyd_async.core import Device

from .motor import Motor

log = logging.getLogger(__name__)

ureg = pint.UnitRegistry()


class AerotechMotor(Motor):
    """Allow an Aerotech stage to fly-scan via the Ophyd FlyerInterface.

    Set *start_position*, *end_position*, and *step_size* in units of
    the motor record (.EGU), and *dwell_time* in seconds. Then the
    remaining components will be calculated accordingly.

    All position or distance components are assumed to be in motor
    record engineering units, unless preceded with "encoder_", in
    which case they are in units of encoder pulses based on the
    encoder resolution.

    The following diagram describes how the various components relate
    to each other. Distances are not to scale::

                 ┌─ encoder_window_start         ┌─ encoder_window_stop
                 │                               │
                 │ |┄┄┄| *step_size*             │
                 │ │   │ encoder_step_size       │
                 │ │   │                         │
      Window:    ├┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┤

      Pulses: ┄┄┄┄┄╨───╨───╨───╨───╨───╨───╨───╨┄┄┄┄┄
               │   │ │                       │ │   └─ taxi_end
               │   │ └─ *start_position*     │ └─ pso_end
               │   └─ pso_start              └─ *end position*
               └─ taxi_start

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
      User-requested center of the first scan pixel.
    end_position
      User-requested center of the last scan pixel. This is not
      guaranteed and may be adjusted to match the encoder resolution
      of the stage.
    step_size
      How much space desired between points. This is not guaranteed
      and may be adjusted to match the encoder resolution of the
      stage.
    dwell_time
      How long to take, in seconds, moving between points.
    slew_speed
      How fast to move the stage. Calculated from the remaining
      components.
    taxi_start
      The starting point for motor movement during flying, accounts
      for needed acceleration of the motor.
    taxi_end
      The target point for motor movement during flying, accounts
      for needed acceleration of the motor.
    pso_start
      The motor position corresponding to the first PSO pulse.
    pso_end
      The motor position corresponding to the last PSO pulse.
    encoder_step_size
      The number of encoder counts for each pixel.
    encoder_window_start
      The start of the window within which PSO pulses may be emitted,
      in encoder counts. Should be slightly wider than the actual PSO
      range.
    encoder_window_end
      The end of the window within which PSO pulses may be emitted,
      in encoder counts. Should be slightly wider than the actual PSO
      range.

    """

    axis: str
    pixel_positions: np.ndarray = None
    # Internal encoder in the Ensemble to track for flying
    encoder: int
    encoder_direction: int = 1
    encoder_window_min: int = -8388607
    encoder_window_max: int = 8388607

    # Calculated fly-scan signals
    # pso_start = Cpt(Signal, kind=Kind.config)
    # pso_end = Cpt(Signal, kind=Kind.config)
    # encoder_step_size = Cpt(Signal, kind=Kind.config)
    # encoder_window_start = Cpt(Signal, kind=Kind.config)
    # encoder_window_end = Cpt(Signal, kind=Kind.config)
    # disable_window = Cpt(Signal, value=False, kind=Kind.config)
    # encoder_use_window = Cpt(Signal, value=False, kind=Kind.config)

    # # Status signals
    # flying_complete = Cpt(Signal, kind=Kind.omitted)
    # ready_to_fly = Cpt(Signal, kind=Kind.omitted)

    def __init__(
        self, *args, axis: str | None = None, encoder: int | None = None, **kwargs
    ):
        super().__init__(*args, **kwargs)
        # Set up extra calculations for the flyer
        # self.encoder_resolution.subscribe(self._update_fly_params)
        # self.disable_window.subscribe(self._update_fly_params)
        # Save needed axis/encoder values
        self.axis = axis
        self.encoder = encoder

    # def kickoff(self):
    #     """Start a flyer

    #     The status object return is marked as done once flying
    #     has started.

    #     Returns
    #     -------
    #     kickoff_status : StatusBase
    #         Indicate when flying has started.

    #     """

    #     def flight_check(*args, old_value, value, **kwargs) -> bool:
    #         return not bool(old_value) and bool(value)

    #     # Status object is complete when flying has started
    #     self.ready_to_fly.set(False).wait()
    #     status = SubscriptionStatus(self.ready_to_fly, flight_check)
    #     # Taxi the motor
    #     th = threading.Thread(target=self.taxi)
    #     th.daemon = True
    #     th.start()
    #     # Record time of fly start of scan
    #     self.starttime = time.time()
    #     self._taxi_thread = th  # Prevents garbage collection
    #     return status

    # def complete(self):
    #     """Wait for flying to be complete.

    #     This can either be a question ("are you done yet") or a
    #     command ("please wrap up") to accommodate flyers that have a
    #     fixed trajectory (ex. high-speed raster scans) or that are
    #     passive collectors (ex MAIA or a hardware buffer).

    #     In either case, the returned status object should indicate when
    #     the device is actually finished flying.

    #     Returns
    #     -------
    #     complete_status : StatusBase
    #         Indicate when flying has completed
    #     """

    #     # Prepare a callback to check when the motor has stopped moving
    #     def check_flying(*args, old_value, value, **kwargs) -> bool:
    #         "Check if flying is complete."
    #         return bool(value)

    #     # Status object is complete when flying has started
    #     self.flying_complete.set(False).wait()
    #     status = SubscriptionStatus(self.flying_complete, check_flying)
    #     # Iniate the fly scan
    #     th = threading.Thread(target=self.fly)
    #     th.start()
    #     self._fly_thread = th  # Prevents garbage collection
    #     return status

    # def collect(self) -> Generator[Dict, None, None]:
    #     """Retrieve data from the flyer as proto-events
    #     Yields
    #     ------
    #     event_data : dict
    #         Must have the keys {'time', 'timestamps', 'data'}.

    #     """
    #     # np array of pixel location
    #     pixels = self.pixel_positions
    #     # time of scans start taken at Kickoff
    #     starttime = self.starttime
    #     # time of scans at movement stop
    #     endtime = self.endtime
    #     # grab necessary for calculation
    #     accel_time = self.acceleration.get()
    #     dwell_time = self.flyer_dwell_time.get()
    #     step_size = self.flyer_step_size()
    #     slew_speed = step_size / dwell_time
    #     motor_accel = slew_speed / accel_time
    #     # Calculate the time it takes for taxi to reach first pixel
    #     extrataxi = ((0.5 * ((slew_speed**2) / (2 * motor_accel))) / slew_speed) + (
    #         dwell_time / 2
    #     )
    #     taxi_time = accel_time + extrataxi
    #     # Create np array of times for each pixel in seconds since epoch
    #     startpixeltime = starttime + taxi_time
    #     endpixeltime = endtime - taxi_time
    #     scan_time = endpixeltime - startpixeltime
    #     timestamps1 = np.linspace(
    #         startpixeltime, startpixeltime + scan_time, num=len(pixels)
    #     )
    #     timestamps = [round(ts, 8) for ts in timestamps1]
    #     for value, ts in zip(pixels, timestamps):
    #         yield {
    #             "data": {self.name: value, self.user_setpoint.name: value},
    #             "timestamps": {self.name: ts, self.user_setpoint.name: ts},
    #             "time": ts,
    #         }

    # def describe_collect(self):
    #     """Describe details for the collect() method"""
    #     desc = OrderedDict()
    #     desc.update(self.describe())
    #     return {"positions": desc}

    # def fly(self):
    #     # Start the trajectory
    #     destination = self.flyer_taxi_end.get()
    #     log.debug(f"Flying to {destination}.")
    #     self.move(destination, wait=True)
    #     # Wait for the landing
    #     self.disable_pso()
    #     self.flying_complete.set(True).wait()
    #     # Record end time of flight
    #     self.endtime = time.time()

    # def taxi(self):
    #     # import pdb; pdb.set_trace()
    #     self.disable_pso()
    #     # Initalize the PSO
    #     # Move motor to the scan start point
    #     self.move(self.pso_start.get(), wait=True)
    #     # Arm the PSO
    #     self.enable_pso()
    #     self.arm_pso()
    #     # Move the motor to the taxi position
    #     taxi_start = self.flyer_taxi_start.get()
    #     log.debug(f"Taxiing to {taxi_start}.")
    #     self.move(taxi_start, wait=True)
    #     # Set the speed on the motor
    #     self.velocity.set(self.flyer_slew_speed.get()).wait()
    #     # Set timing on the delay for triggering detectors, etc
    #     self.parent.delay.channel_C.delay.put(0)
    #     self.parent.delay.output_CD.polarity.put(self.parent.delay.polarities.NEGATIVE)
    #     # Count-down timer
    #     # for i in range(10, 0, -1):
    #     #     print(f"{i}...", end="", flush=True)
    #     #     time.sleep(1)
    #     # print("Go!")
    #     self.ready_to_fly.set(True)

    # def stage(self, *args, **kwargs):
    #     self.ready_to_fly.set(False).wait()
    #     self.flying_complete.set(False).wait()
    #     self.starttime = None
    #     self.endtime = None
    #     # Save old veolcity to be restored after flying
    #     self.old_velocity = self.velocity.get()
    #     super().stage(*args, **kwargs)

    # def unstage(self, *args, **kwargs):
    #     self.velocity.set(self.old_velocity).wait()
    #     return super().unstage(*args, **kwargs)

    # def move(self, position, wait=True, *args, **kwargs):
    #     motor_status = super().move(position, wait=wait, *args, **kwargs)

    #     def check_readback(*args, old_value, value, **kwargs) -> bool:
    #         "Check if taxiing is complete and flying has begun."
    #         has_arrived = np.isclose(value, position, atol=0.001)
    #         log.debug(
    #             f"Checking readback: {value=}, target: {position}, {has_arrived=}"
    #         )
    #         return has_arrived

    #     # Status object is complete motor reaches target value
    #     readback_status = SubscriptionStatus(self.user_readback, check_readback)
    #     # Prepare the combined status object
    #     status = motor_status & readback_status
    #     if wait:
    #         status.wait()
    #     return readback_status

    # @property
    # def motor_egu_pint(self):
    #     egu = ureg(self.motor_egu.get())
    #     return egu

    # def flyer_step_size(self):
    #     """Calculate the size of each step in a fly scan."""
    #     start_position = self.flyer_start_position.get()
    #     end_position = self.flyer_end_position.get()
    #     num_points = self.flyer_num_points.get()
    #     step_size = abs(start_position - end_position) / (num_points - 1)
    #     return step_size

    # def _update_fly_params(self, *args, **kwargs):
    #     """Calculate new fly-scan parameters based on signal values.

    #     Implementation courtesy of Alan Kastengren.

    #     Computes several parameters describing the fly scan motion.
    #     These include the actual start position of the motor, the
    #     actual distance (in encoder counts and distance) between PSO
    #     pulses, the end position of the motor, and where PSO pulses
    #     are expected to occcur.  This code ensures that each PSO delta
    #     is an integer number of encoder counts, since this is how the
    #     PSO triggering works in hardware.

    #     These calculations are for MCS scans, where for N bins we need
    #     N+1 pulses.

    #     Several fields are set in the class:

    #     direction
    #       1 if we are moving positive in user coordinates, −1 if
    #       negative
    #     overall_sense
    #       is our fly motion + or - with respect to encoder counts
    #     taxi_start
    #       The starting point for motor movement during flying, accounts
    #       for needed acceleration of the motor.
    #     taxi_end
    #       The target point for motor movement during flying, accounts
    #       for needed acceleration of the motor.
    #     pso_start
    #       The motor position corresponding to the first PSO pulse.
    #     pso_end
    #        The motor position corresponding to the last PSO pulse.
    #     pso_zero
    #        The motor position where the PSO counter is set to zero.
    #     encoder_step_size
    #       The number of encoder counts for each pixel.
    #     encoder_window_start
    #       The start of the window within which PSO pulses may be emitted,
    #       in encoder counts. Should be slightly wider than the actual PSO
    #       range.
    #     encoder_window_end
    #       The end of the window within which PSO pulses may be emitted,
    #       in encoder counts. Should be slightly wider than the actual PSO
    #     pixel_positions
    #       array of places where pixels are, should occur calculated from
    #       encoder counts then translated to motor positions
    #     """
    #     window_buffer = 5
    #     # Grab any neccessary signals for calculation
    #     start_position = self.flyer_start_position.get()
    #     end_position = self.flyer_end_position.get()
    #     dwell_time = self.flyer_dwell_time.get()
    #     step_size = self.flyer_step_size()
    #     encoder_resolution = self.encoder_resolution.get()
    #     accel_time = self.acceleration.get()
    #     # Check for sane values
    #     if dwell_time == 0:
    #         log.warning(
    #             f"{self} dwell_time is zero. Could not update fly scan parameters."
    #         )
    #         return
    #     if encoder_resolution == 0:
    #         log.warning(
    #             f"{self} encoder resolution is zero. Could not update fly scan"
    #             " parameters."
    #         )
    #         return
    #     if accel_time <= 0:
    #         log.warning(
    #             f"{self} acceleration is non-positive. Could not update fly scan"
    #             " parameters."
    #         )
    #         return
    #     # Determine the desired direction of travel and overall sense
    #     # +1 when moving in + encoder direction, -1 if else
    #     direction = 1 if start_position < end_position else -1
    #     overall_sense = direction * self.encoder_direction
    #     # Calculate the step size in encoder steps
    #     encoder_step_size = round(step_size / encoder_resolution)
    #     # PSO start/end should be located to where req. start/end are
    #     # in between steps. Also doubles as the location where slew
    #     # speed must be met.
    #     pso_start = start_position - (direction * (step_size / 2))
    #     pso_end = end_position + (direction * (step_size / 2))
    #     # Determine taxi distance to accelerate to req speed, v^2/(2*a) = d
    #     # x1.5 for safety margin
    #     slew_speed = step_size / dwell_time
    #     motor_accel = slew_speed / accel_time
    #     taxi_dist = slew_speed**2 / (2 * motor_accel) * 1.5
    #     taxi_start = pso_start - (direction * taxi_dist)
    #     taxi_end = pso_end + (direction * taxi_dist)
    #     # Actually taxi to the first PSO position before the taxi position
    #     encoder_taxi_start = (taxi_start - pso_start) / encoder_resolution
    #     if overall_sense > 0:
    #         rounder = math.floor
    #     else:
    #         rounder = math.ceil
    #     encoder_taxi_start = (
    #         rounder(encoder_taxi_start / encoder_step_size) * encoder_step_size
    #     )
    #     taxi_start = pso_start + encoder_taxi_start * encoder_resolution
    #     # Calculate encoder counts within the requested window of the scan
    #     encoder_window_start = 0  # round(pso_start / encoder_resolution)
    #     encoder_distance = (pso_end - pso_start) / encoder_resolution
    #     encoder_window_end = round(encoder_window_start + encoder_distance)
    #     # Widen the bound a little to make sure we capture the pulse
    #     encoder_window_start -= overall_sense * window_buffer
    #     encoder_window_end += overall_sense * window_buffer

    #     # Check for values outside of the window range for this controller
    #     def is_valid_window(value):
    #         window_in_range = self.encoder_window_min < value < self.encoder_window_max
    #         return window_in_range

    #     window_range = [encoder_window_start, encoder_window_end]
    #     encoder_use_window = all([is_valid_window(v) for v in window_range])
    #     encoder_use_window = encoder_use_window and not self.disable_window.get()
    #     # Create np array of PSO positions in encoder counts
    #     _pso_step = encoder_step_size * overall_sense
    #     _pso_end = encoder_distance + 0.5 * _pso_step
    #     encoder_pso_positions = np.arange(0, _pso_end, _pso_step)
    #     # Transform from PSO positions from encoder counts to engineering units
    #     pso_positions = (encoder_pso_positions * encoder_resolution) + pso_start
    #     # Tranforms from pulse positions to pixel centers
    #     pixel_positions = (pso_positions[1:] + pso_positions[:-1]) / 2
    #     # Set all the calculated variables
    #     [
    #         stat.wait()
    #         for stat in [
    #             self.encoder_step_size.set(encoder_step_size),
    #             self.pso_start.set(pso_start),
    #             self.pso_end.set(pso_end),
    #             self.flyer_slew_speed.set(slew_speed),
    #             self.flyer_taxi_start.set(taxi_start),
    #             self.flyer_taxi_end.set(taxi_end),
    #             self.encoder_window_start.set(encoder_window_start),
    #             self.encoder_window_end.set(encoder_window_end),
    #             self.encoder_use_window.set(encoder_use_window),
    #         ]
    #     ]
    #     self.encoder_pso_positions = encoder_pso_positions
    #     self.pso_positions = pso_positions
    #     self.pixel_positions = pixel_positions

    # def send_command(self, cmd: str):
    #     """Send commands directly to the aerotech ensemble controller.

    #     Returns
    #     =======
    #     status
    #       The Ophyd status object for this write.

    #     """
    #     status = self.parent.asyn.ascii_output.set(cmd, settle_time=0.1)
    #     status.wait()
    #     return status

    # def disable_pso(self):
    #     for axis in range(2):
    #         self.send_command(f"PSOCONTROL @{axis} OFF")

    # def check_flyscan_bounds(self):
    #     """Check that the fly-scan params are sane at the scan start and end.

    #     This checks to make sure no spurious pulses are expected from taxiing.

    #     """
    #     end_points = [
    #         (self.flyer_taxi_start, self.pso_start),
    #         (self.flyer_taxi_end, self.pso_end),
    #     ]
    #     step_size = self.flyer_step_size()
    #     for taxi, pso in end_points:
    #         # Make sure we're not going to have extra pulses
    #         taxi_distance = abs(taxi.get() - pso.get())
    #         if taxi_distance > (1.1 * step_size):
    #             raise InvalidScanParameters(
    #                 f"Scan parameters for {taxi}, {pso}, {self.flyer_step_size} would produce"
    #                 " extra pulses without a window."
    #             )

    # def enable_pso(self):
    #     num_axis = 1
    #     use_window = self.encoder_use_window.get()
    #     if not use_window:
    #         self.check_flyscan_bounds()
    #     # Erase any previous PSO control
    #     self.send_command(f"PSOCONTROL {self.axis} RESET")
    #     # Set the output to occur from the I/O terminal on the
    #     # controller
    #     self.send_command(f"PSOOUTPUT {self.axis} CONTROL {num_axis}")
    #     # Set a pulse 10 us long, 20 us total duration, so 10 us
    #     # on, 10 us off
    #     self.send_command(f"PSOPULSE {self.axis} TIME 20, 10")
    #     # Set the pulses to only occur in a specific window
    #     if use_window:
    #         self.send_command(f"PSOOUTPUT {self.axis} PULSE WINDOW MASK")
    #     else:
    #         self.send_command(f"PSOOUTPUT {self.axis} PULSE")
    #     # Set which encoder we will use.  3 = the MXH (encoder
    #     # multiplier) input. For Ensemble lab, 6 is horizontal encoder
    #     self.send_command(f"PSOTRACK {self.axis} INPUT {self.encoder}")
    #     # Set the distance between pulses in encoder counts
    #     self.send_command(
    #         f"PSODISTANCE {self.axis} FIXED {self.encoder_step_size.get()}"
    #     )
    #     # Which encoder is being used to calculate whether we are
    #     # in the window.
    #     if use_window:
    #         self.send_command(f"PSOWINDOW {self.axis} {num_axis} INPUT {self.encoder}")
    #         # Calculate window function parameters. Must be in encoder
    #         # counts, and is referenced from the stage location where
    #         # we arm the PSO
    #         window_range = (
    #             self.encoder_window_start.get(),
    #             self.encoder_window_end.get(),
    #         )
    #         self.send_command(
    #             f"PSOWINDOW {self.axis} {num_axis} RANGE "
    #             f"{min(window_range)},{max(window_range)}"
    #         )

    # def arm_pso(self):
    #     self.send_command(f"PSOCONTROL {self.axis} ARM")


class AerotechStage(Device):
    """An XY stage for an Aerotech stage with fly-scanning capabilities.

    Parameters
    ==========

    vertical_prefix
      The prefix for the PV of the vertical motor.
    horizontal_prefix
      The prefix to the PV of the horizontal motor.
    delay_prefix
      The prefix to the PVs associated with the pulse delay generator

    """

    _ophyd_labels_ = {"stages"}

    def __init__(
        self,
        vertical_prefix: str,
        horizontal_prefix: str,
        delay_prefix: str | None = None,
        name: str = "",
    ):
        # Axes devices
        self.vert = AerotechMotor(vertical_prefix)
        self.horiz = AerotechMotor(horizontal_prefix)
        # Extra devices for operating the stage
        # asyn = Cpt(AsynRecord, ":asynEns", name="async", labels={"asyns"})
        # A digital delay generator for providing a gate signal
        # delay = FCpt(DG645Delay, "{delay_prefix}:", kind=Kind.config)
        super().__init__(name=name)


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2023, UChicago Argonne, LLC
#
# Distributed under the terms of the 3-Clause BSD License
#
# The full license is in the file LICENSE, distributed with this software.
#
# DISCLAIMER
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# -----------------------------------------------------------------------------
