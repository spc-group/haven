"""A bluesky plan to scan the X-ray energy and capture detector signals.

"""

import logging
import warnings
from typing import Sequence, Union

from bluesky import plans as bp

from ..detectors import ion_chambers
from haven import merge_ranges


__all__ = ["energy_scan"]


log = logging.getLogger(__name__)


def energy_scan(
    energies: Sequence[float],
    exposure: Union[float, Sequence[float]] = 0.1,
    detectors: Sequence = ion_chambers,
    energy_positioners: Sequence = [],
    time_positioners: Sequence = [],
    E0: float = 0,
):
    """Collect a spectrum by scanning X-ray energy.

    *exposure* can be either a float, or a sequence of floats. If a
    single value is provided, it will be used for all energies. If a
    sequence is provided, it should be the same length as *energies*
    and the each entry will be used for the corresponding entry in
    *energies*.

    Usage
    =====

    The following code will run a scan with 1 eV steps from 13000 to
    13099 eV.

        energies = range(13000, 13100)
        RE(energy_scan(energies, exposure=0.5))

    The preparation of energies is up to the calling
    function. Consider using the utility functions
    ``haven.energy_ranges.ERange`` and ``haven.energy_ranges.KRange``
    to prepare more sophisticated energy lists:

        energies = [
          ERange(13000, 13100, E_step=10),
          ERange(13100, 13160, E_step=0.5),
          KRange(13160, k_max=8, k_step=0.2),
        ]
        RE(energy_scan(energies, exposure=0.5))

    The results can also be viewed by passing
    ``haven.callbacks.live_xafs_plot.LiveXAFSPlot`` to the RunEngine:

        RE(energy_scan(...), LiveXAFSPlot())

    Parameters
    ==========
    energies
      The X-ray energies, in eV, over which to scan.
    exposure
      How long, in seconds, to count at each energy.
    detectors
      The detectors to collect X-ray signal from at each energy.
    energy_positioners
      Positioners that will receive the changing energies.
    time_positioners
      Positioners that will receive the exposure time for each scan.
    E0
      Take values in *energy* as relative to the edge energy *E0*. The
      default (0) just takes the energies as is.

    Yields
    ======
    Bluesky messages to execute the scan.

    """
    # Check that arguments are sensible
    if len(energy_positioners) < 1:
        msg = "Cannot run energy_scan with empty *energy_positioners*."
        log.error(msg)
        raise ValueError(msg)
    # Resolve the energy ranges if provided
    merge_ranges(*energies, default_exposure=exposure)
    # Convert an individual exposure time to an array of exposure times
    if not hasattr(exposure, "__iter__"):
        exposure = [exposure] * len(energies)
    # Apply E0 correction
    energies += E0
    # Prepare the positioners list with associated energies and exposures
    msg = "Offset for undulator gap not corrected in energy_scan"
    warnings.warn(msg)
    log.warning(msg)
    scan_args = [(motor, energies) for motor in energy_positioners]
    scan_args += [(motor, exposure) for motor in time_positioners]
    scan_args = [item for items in scan_args for item in items]
    # Do the actual scan
    yield from bp.list_scan(
        detectors,
        *scan_args,
    )
