from typing import Generator, Any

from bluesky import Msg, plan_stubs as bps
from ophyd_async.core import Device
from pint import UnitRegistry

from haven.typing import Calibratable

ureg = UnitRegistry()


def calibrate(device: Calibratable, truth: float, dial: float | None = None, relative: bool = False) -> Generator[Msg, Any, None]:
    """A Bluesky plan to calibrate a monochromator to a known energy.

    device
      The calibratable device that will be calibrated.
    truth
      The known calibrated energy that should correspond to
      *setpoint_energy*. For example, the known edge position from a
      literature reference.
    dial
      The uncalibrated setpoint/readback to calibrate. For example,
      the observed edge position in a XANES scan.
    relative
      If true, compound the new calibration with previous
      calibrations.

    """
    # Get recent d_spacing (w/ units)
    yield Msg("calibrate", device, truth=truth, dial=dial, relative=relative)
