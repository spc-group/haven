import asyncio
import logging
import warnings
from collections import OrderedDict
from typing import Mapping, Sequence, Generator, Dict

from scipy.interpolate import CubicSpline
import numpy as np
from apstools.utils.misc import safe_ophyd_name
from ophyd import Component as Cpt
from ophyd import EpicsMotor, EpicsSignal, EpicsSignalRO, Signal, Kind
from ophyd.flyers import FlyerInterface

from .._iconfig import load_config
from .device import make_device, resolve_device_names
from .instrument_registry import InstrumentRegistry
from .instrument_registry import registry as default_registry

log = logging.getLogger(__name__)


class HavenMotor(FlyerInterface, EpicsMotor):
    """The default motor for haven movement.

    This motor also implements the flyer interface and so can be used
    in a fly scan, though no hardware trigger is supported.

    Returns to the previous value when being unstaged.

    """
    # Extra motor record components
    encoder_resolution = Cpt(EpicsSignal, ".ERES", kind=Kind.config)
    description = Cpt(EpicsSignal, ".DESC", kind="omitted")
    tweak_value = Cpt(EpicsSignal, ".TWV", kind="omitted")
    tweak_forward = Cpt(EpicsSignal, ".TWF", kind="omitted", tolerance=2)
    tweak_reverse = Cpt(EpicsSignal, ".TWR", kind="omitted", tolerance=2)
    motor_stop = Cpt(EpicsSignal, ".STOP", kind="omitted", tolerance=2)
    soft_limit_violation = Cpt(EpicsSignalRO, ".LVIO", kind="omitted")

    # Desired fly parameters
    start_position = Cpt(Signal, name="start_position", value=0, kind=Kind.config)
    end_position = Cpt(Signal, name="end_position", value=1, kind=Kind.config)
    # step_size = Cpt(Signal, name="step_size", value=1, kind=Kind.config)
    num_points = Cpt(Signal, name="num_points", value=2, kind=Kind.config)
    dwell_time = Cpt(Signal, name="dwell_time", value=1, kind=Kind.config)

    # Calculated fly parameters
    slew_speed = Cpt(Signal, value=1, kind=Kind.config)
    taxi_start = Cpt(Signal, kind=Kind.config)
    taxi_end = Cpt(Signal, kind=Kind.config)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set up auto-calculations for the flyer
        self.motor_egu.subscribe(self._update_fly_params)
        self.start_position.subscribe(self._update_fly_params)
        self.end_position.subscribe(self._update_fly_params)
        self.num_points.subscribe(self._update_fly_params)
        self.dwell_time.subscribe(self._update_fly_params)
        self.acceleration.subscribe(self._update_fly_params)

    def stage(self):
        # Override some additional staged signals
        self._original_vals.setdefault(self.user_setpoint, self.user_readback.get())
        self._original_vals.setdefault(self.velocity, self.velocity.get())

    def kickoff(self):
        """Start the motor as a flyer.

        The status object return is marked as done once flying
        is ready.

        Returns
        -------
        kickoff_status : StatusBase
            Indicate when flying is ready.

        """
        self.move(self.taxi_start.get(), wait=True)
        st = self.velocity.set(self.slew_speed.get())
        return st

    def complete(self):
        """Start the motor flying and wait for it to complete.

        Returns
        -------
        complete_status : StatusBase
            Indicate when flying has completed

        """
        # Record real motor positions for later evaluation
        self._fly_data = []
        cid = self.user_readback.subscribe(self.record_datum, run=False)
        st = self.move(self.taxi_end.get(), wait=True)
        self.user_readback.unsubscribe(cid)
        return st

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
        times, positions = np.asarray(self._fly_data).transpose()
        model = CubicSpline(positions, times, bc_type="clamped")
        # Create the data objects
        for position in self.pixel_positions:
            timestamp = float(model(position))
            yield {
                "time": timestamp,
                "timestamps": {
                    self.user_readback.name: timestamp,
                    self.user_setpoint.name: timestamp,
                },
                "data": {
                    self.user_readback.name: position,
                    self.user_setpoint.name: position,
                },
            }

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
        egu = self.motor_egu.get()
        start_position = self.start_position.get()
        end_position = self.end_position.get()
        dwell_time = self.dwell_time.get()
        num_points = self.num_points.get()
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
        step_size = abs((start_position - end_position) / (num_points-1))
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
        [
            status.wait()
            for status in [
                self.slew_speed.set(slew_speed),
                self.taxi_start.set(taxi_start),
                self.taxi_end.set(taxi_end),
            ]
        ]
        self.pixel_positions = pixel_positions



def load_motors(
    config: Mapping = None, registry: InstrumentRegistry = default_registry
) -> Sequence:
    """Load generic hardware motors from IOCs.

    This loader will skip motor prefixes that already exist in the
    registry *registry*, so it is a good idea to run this loader after
    other devices have been created that might potentially use some of
    these motors (e.g. mirrors, tables, etc.).

    Parameters
    ==========
    config
      The beamline configuration. If omitted, will use the config
      provided by :py:func:`haven._iconfig.load_config()`.
    registry
      The instrument registry to check for existing motors. Existing
      motors will not be duplicated.

    Returns
    =======
    devices
      The newly create EpicsMotor devices.

    """
    if config is None:
        config = load_config()
    # Build up definitions of motors to load
    defns = []
    for section_name, config in config.get("motor", {}).items():
        prefix = config["prefix"]
        num_motors = config["num_motors"]
        log.info(
            f"Preparing {num_motors} motors from IOC: " f"{section_name} ({prefix})"
        )
        for idx in range(num_motors):
            motor_prefix = f"{prefix}m{idx+1}"
            defns.append(
                {
                    "prefix": motor_prefix,
                    "desc_pv": f"{motor_prefix}.DESC",
                    "ioc_name": section_name,
                }
            )
    # Check that we're not duplicating a motor somewhere else (e.g. KB mirrors)
    existing_pvs = []
    for m in registry.findall(label="motors", allow_none=True):
        if hasattr(m, "prefix"):
            existing_pvs.append(m.prefix)
    defns = [defn for defn in defns if defn["prefix"] not in existing_pvs]
    duplicates = [defn for defn in defns if defn["prefix"] in existing_pvs]
    if len(duplicates) > 0:
        log.info(
            "The following motors already exist and will not be duplicated: ",
            ", ".join([m["prefix"] for m in duplicates]),
        )
    else:
        log.debug(f"No duplicated motors detected out of {len(defns)}")
    # Resolve the scaler channels into ion chamber names
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No loop, so make a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.run_until_complete(resolve_device_names(defns))
    # Create the devices
    devices = []
    missing_channels = []
    unnamed_channels = []
    for defn in defns:
        # Check for motor without a name
        if defn["name"] == "":
            unnamed_channels.append(defn["prefix"])
        elif defn["name"] is None:
            missing_channels.append(defn["prefix"])
        else:
            # Create the device
            labels = {"motors", "extra_motors", "baseline", defn["ioc_name"]}
            name = safe_ophyd_name(defn["name"])
            devices.append(
                make_device(HavenMotor, prefix=defn["prefix"], name=name, labels=labels)
            )
    # Notify about motors that have no name
    if len(missing_channels) > 0:
        msg = "Skipping unavailable motors: "
        msg += ", ".join([prefix for prefix in missing_channels])
        warnings.warn(msg)
        log.warning(msg)
    if len(unnamed_channels) > 0:
        msg = "Skipping unnamed motors: "
        msg += ", ".join([prefix for prefix in unnamed_channels])
        warnings.warn(msg)
        log.warning(msg)
    return devices


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
