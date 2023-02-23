from typing import Union, Sequence

from bluesky import plan_stubs as bps
from ophyd import Device

from ..instrument.instrument_registry import registry


def set_energy(energy: float, positioners: Sequence[Union[Device, str]] = ["energy"]):
    """Set the energy of the beamline, in electron volts.

    Moves both the mono energy, and the undulator energy with a
    calibrated offset.

    """
    # Resolve the devices
    positioners = registry.findall(name=positioners)
    # Prepare arguments
    args = []
    for pos in positioners:
        args.extend([pos, energy])
    # Execute the plan
    yield from bps.mv(*args)
