from typing import Generator, Any

from bluesky import Msg, plan_stubs as bps
from ophyd_async.core import Device
from pint import UnitRegistry

from haven.typing import Calibratable

ureg = UnitRegistry()


def calibrate(device: Calibratable, truth: float, target: float | None = None) -> Generator[Msg, Any, None]:
    """A Bluesky plan to calibrate a monochromator to a known energy.

    monochromator
      The ophyd-async monochromator device that will be calibrated
    setpoint_energy
      The uncalibrated setpoint to calibrate. For example, the
      observed edge position in a XANES scan.
    actual_energy
      The known calibrated energy that should correspond to
      *setpoint_energy*. For example, the known edge position from a
      literature reference.

    """
    # Get recent d_spacing (w/ units)
    yield Msg("calibrate", device, truth=truth, target=target)
