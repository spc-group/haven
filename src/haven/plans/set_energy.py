from typing import Union, Sequence

from bluesky import plan_stubs as bps
from ophyd import Device

from ..instrument.instrument_registry import registry
from ..typing import DetectorList
from .. import exceptions


__all__ = ["set_energy"]


Harmonic = Union[str, int, None]


def auto_harmonic(energy: float, harmonic: Harmonic) -> Harmonic:
    # No harmonic change is requested
    if harmonic is None:
        return harmonic
    # Check for specific harmonics
    try:
        return int(harmonic)
    except ValueError:
        pass
    # Check for auto harmonic selection
    threshold = 11000
    if harmonic == "auto":
        if energy < threshold:
            return 1
        else:
            return 3
    # If we get here, the harmonic was not a valid option
    raise exceptions.InvalidHarmonic(
        f"Insertion device cannot accept harmonic: {harmonic}"
    )


def set_energy(
    energy: float,
    harmonic: Harmonic = None,
    positioners: DetectorList = ["energy"],
    harmonic_positioners: DetectorList = ["undulator_harmonic_value"],
):
    """Set the energy of the beamline, in electron volts.

    Moves both the mono energy, and the undulator energy with a
    calibrated offset.

    The *harmonic* parameter selects a harmonic for the undulator. If
    ``"auto"``, then the harmonic will be selected based on the
    energy. If *harmonic* is ``None``, then the current harmonic is
    used. If *harmonic* is an integer (e.g. 1, 3, 5) then this value
    will be used.

    Parameters
    ==========
    energy
      The target energy of the beamline, in electron-volts.
    harmonic

      Which harmonic to use for the undulator. Can be an integer
      (e.g. 1, 3, 5), ``None``, or ``"auto"``.

    """
    # Prepare arguments for undulator harmonic
    harmonic = auto_harmonic(energy, harmonic)
    if harmonic is not None:
        harmonic_positioners = registry.findall(name=harmonic_positioners)
        hargs = []
        for positioner in harmonic_positioners:
            hargs.extend([positioner, harmonic])
        yield from bps.mv(*hargs)
    # Prepare arguments for energy
    positioners = registry.findall(name=positioners)
    args = []
    for positioner in positioners:
        args.extend([positioner, energy])
    # Execute the plan
    yield from bps.mv(*args)
