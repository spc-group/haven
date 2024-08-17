import logging
import warnings
from collections import OrderedDict
from typing import Dict, Generator

import numpy as np
from ophyd import Component as Cpt
from ophyd import Device, Kind, Signal, get_cl
from ophyd.flyers import FlyerInterface
from ophyd.status import Status
from scipy.interpolate import CubicSpline

log = logging.getLogger()


warnings.warn(
    DeprecationWarning(
        "Motor flyer will be removed in a future release. Please replace with the ophyd-async Motor for fly-scan support"
    )
)


class MotorFlyer(FlyerInterface, Device):
    # Desired fly parameters
    flyer_start_position = Cpt(Signal, name="start_position", value=0, kind=Kind.config)
    flyer_end_position = Cpt(Signal, name="end_position", value=1, kind=Kind.config)
    # step_size = Cpt(Signal, name="step_size", value=1, kind=Kind.config)
    flyer_num_points = Cpt(Signal, value=2, kind=Kind.config)
    flyer_dwell_time = Cpt(Signal, value=1, kind=Kind.config)

    # Calculated fly parameters
    flyer_slew_speed = Cpt(Signal, value=1, kind=Kind.config)
    flyer_taxi_start = Cpt(Signal, kind=Kind.config)
    flyer_taxi_end = Cpt(Signal, kind=Kind.config)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._kickoff_thread = None
        self._complete_thread = None
        self._fly_model = None
        self.cl = get_cl()
        # Set up auto-calculations for the flyer
        self.motor_egu.subscribe(self._update_fly_params)
        self.acceleration.subscribe(self._update_fly_params)
        self.flyer_start_position.subscribe(self._update_fly_params)
        self.flyer_end_position.subscribe(self._update_fly_params)
        self.flyer_num_points.subscribe(self._update_fly_params)
        self.flyer_dwell_time.subscribe(self._update_fly_params)

    def kickoff(self):
        """Start the motor as a flyer.

        The status object return is marked as done once flying
        is ready.

        Returns
        -------
        kickoff_status : StatusBase
            Indicate when flying is ready.

        """
        self.log.debug(f"Kicking off {self}")

        def kickoff_thread():
            try:
                self.move(self.flyer_taxi_start.get(), wait=True)
                self.velocity.put(self.flyer_slew_speed.get())
            except Exception as exc:
                st.set_exception(exc)
            else:
                self.log.debug(f"{self} kickoff succeeded")
                st.set_finished()
            finally:
                # keep a local reference to avoid any GC shenanigans
                th = self._kickoff_thread
                # these two must be in this order to avoid a race condition
                self._kickoff_thread = None
                del th

        if self._kickoff_thread is not None:
            raise RuntimeError(
                "Another kickoff() call is still in progress " f"for {self.name}"
            )

        st = Status(self)
        self._status = st
        self._kickoff_thread = self.cl.thread_class(target=kickoff_thread)
        self._kickoff_thread.daemon = True
        self._kickoff_thread.start()
        return self._status

    def complete(self):
        """Start the motor flying and wait for it to complete.

        Returns
        -------
        complete_status : StatusBase
            Indicate when flying has completed

        """
        self.log.debug(f"Comleting {self}")

        def complete_thread():
            try:
                # Record real motor positions for later evaluation
                self._fly_data = []
                self._fly_model = None
                cid = self.user_readback.subscribe(self.record_datum, run=False)
                self.move(self.flyer_taxi_end.get(), wait=True)
                self.user_readback.unsubscribe(cid)
            except Exception as exc:
                st.set_exception(exc)
            else:
                self.log.debug(f"{self} complete succeeded")
                st.set_finished()
            finally:
                # keep a local reference to avoid any GC shenanigans
                th = self._complete_thread
                # these two must be in this order to avoid a race condition
                self._complete_thread = None
                del th

        if self._complete_thread is not None:
            raise RuntimeError(
                f"Another complete() call is still in progress for {self.name}"
            )

        st = Status(self)
        self._status = st
        self._complete_thread = self.cl.thread_class(target=complete_thread)
        self._complete_thread.daemon = True
        self._complete_thread.start()
        return self._status

    def record_datum(self, *, old_value, value, timestamp, **kwargs):
        """Record a fly-scan data point so we can report it later."""
        self._fly_data.append((timestamp, value))

    def collect(self) -> Generator[Dict, None, None]:
        """Retrieve data from the flyer as proto-events

        Yields
        ------
        event_data : dict
            Must have the keys {'time', 'timestamps', 'data'}.

        """
        # Create the data objects
        for time, position in self._fly_data:
            yield {
                "time": time,
                "timestamps": {
                    self.user_readback.name: time,
                    self.user_setpoint.name: time,
                },
                "data": {
                    self.user_readback.name: position,
                    self.user_setpoint.name: position,
                },
            }

    def predict(self, timestamp: float) -> Dict:
        """Predict where the motor was at *timestamp* during most recent fly
        scan.

        Parameters
        ==========
        timestamp
          The unix timestamp to use for interpolating the measured data.

        Returns
        =======
        datum
          A data event for this timestamp similar to those provided by
          the ``collect()`` method.

        """
        # Prepare an interpolation model for fly scan data
        if self._fly_model is None:
            times, positions = np.asarray(self._fly_data).transpose()
            self._fly_model = CubicSpline(times, positions, bc_type="clamped")
        model = self._fly_model
        # Interpolate the data value based on timestamp
        position = float(model(timestamp))
        setpoint = self.pixel_positions[
            np.argmin(np.abs(self.pixel_positions - position))
        ]
        datum = {
            "time": timestamp,
            "timestamps": {
                self.user_readback.name: timestamp,
                self.user_setpoint.name: timestamp,
            },
            "data": {
                self.user_readback.name: position,
                self.user_setpoint.name: setpoint,
            },
        }
        return datum

    def describe_collect(self):
        """Describe details for the collect() method"""
        desc = OrderedDict()
        desc.update(self.describe())
        return {self.user_readback.name: desc}

    def _update_fly_params(self, *args, **kwargs):
        """Calculate new fly-scan parameters based on signal values.

        Computes several parameters describing the fly scan motion.
        These include the actual start position of the motor, the
        actual distance between points, and the end position of the
        motor.

        Several fields are set in the class:

        direction
          1 if we are moving positive in user coordinates, −1 if
          negative
        taxi_start
          The starting point for motor movement during flying, accounts
          for needed acceleration of the motor.
        taxi_end
          The target point for motor movement during flying, accounts
          for needed acceleration of the motor.
        pixel_positions
          array of places where pixels are, should occur calculated from
          encoder counts then translated to motor positions

        """
        # Grab any neccessary signals for calculation
        start_position = self.flyer_start_position.get()
        end_position = self.flyer_end_position.get()
        dwell_time = self.flyer_dwell_time.get()
        num_points = self.flyer_num_points.get()
        accel_time = self.acceleration.get()
        # Check for sane values
        if dwell_time == 0:
            log.warning(
                f"{self} dwell_time is zero. Could not update fly scan parameters."
            )
            return
        if accel_time <= 0:
            log.warning(
                f"{self} acceleration is non-positive. Could not update fly scan"
                " parameters."
            )
            return
        # Determine the desired direction of travel:
        # +1 when moving in + encoder direction, -1 if else
        direction = 1 if start_position < end_position else -1
        # Determine taxi distance to accelerate to req speed, v^2/(2*a) = d
        # x1.5 for safety margin
        step_size = abs((start_position - end_position) / (num_points - 1))
        if step_size <= 0:
            log.warning(
                f"{self} step_size is non-positive. Could not update fly scan"
                " parameters."
            )
            return
        slew_speed = step_size / dwell_time
        motor_accel = slew_speed / accel_time
        taxi_dist = slew_speed**2 / (2 * motor_accel) * 1.5 + step_size / 2
        taxi_start = start_position - (direction * taxi_dist)
        taxi_end = end_position + (direction * taxi_dist)
        # Tranforms from pulse positions to pixel centers
        pixel_positions = np.linspace(start_position, end_position, num=num_points)
        # Set all the calculated variables
        self.flyer_slew_speed.put(slew_speed)
        self.flyer_taxi_start.put(taxi_start)
        self.flyer_taxi_end.put(taxi_end)
        self.pixel_positions = pixel_positions
