"""A bluesky plan to scan the X-ray energy and capture detector signals.

"""

import logging
import warnings
from typing import Sequence, Union, Mapping

from bluesky import plans as bp, utils
import numpy as np

from .. import merge_ranges, exceptions
from .._iconfig import load_config
from ..instrument import registry
from ..constants import edge_energy
from ..typing import DetectorList


__all__ = ["energy_scan"]


log = logging.getLogger(__name__)


def energy_scan(
    energies: Sequence[float],
    exposure: Union[float, Sequence[float]] = 0.1,
    E0: Union[float, str] = 0,
    detectors: DetectorList = "ion_chambers",
    energy_positioners: Sequence = ["energy"],
    time_positioners: Sequence = ["I0_exposure_time"],
    md: Mapping = {},
):
    """Collect a spectrum by scanning X-ray energy.

    For scanning over a pre-defined X-ray absorption edge, try
    :py:func:`~haven.plans.xafs_scan.xafs_scan` instead.

    *exposure* can be either a float, or a sequence of floats. If a
    single value is provided, it will be used for all energies. If a
    sequence is provided, it should be the same length as *energies*
    and the each entry will be used for the corresponding entry in
    *energies*.

    **Usage:**

    The following code will run a scan with 1 eV steps from 13000 to
    13099 eV.

        energies = range(13000, 13100)
        RE(energy_scan(energies, exposure=0.5))

    The preparation of energies is up to the calling function. For
    more sophisticated energy lists, consider using the utility
    functions :py:class:`haven.energy_ranges.ERange` and
    :py:class:`haven.energy_ranges.KRange`:

    .. code-block:: python

        energies = [
          ERange(13000, 13100, E_step=10),
          ERange(13100, 13160, E_step=0.5),
          KRange(13160, k_max=8, k_step=0.2),
        ]
        RE(energy_scan(energies, exposure=0.5))

    The results can also be viewed by passing
    :py:class:`haven.callbacks.live_xafs_plot.LiveXAFSPlot` to the RunEngine:

    .. code-block:: python

        RE(energy_scan(...), LiveXAFSPlot())

    Parameters
    ==========
    energies
      The X-ray energies, in eV, over which to scan.
    exposure
      How long, in seconds, to count at each energy.
    E0
      An edge energy, in eV, or name of the edge of the form
      ``"Ni_L3"``. All energies will be relative to this value.
    detectors
      The detectors to collect X-ray signal from at each energy.
    energy_positioners
      Positioners that will receive the changing energies.
    time_positioners
      Positioners that will receive the exposure time for each scan.
    md
      Additional metadata to pass on the to run engine.

    Yields
    ======
    Bluesky messages to execute the scan.

    """
    # Check that arguments are sensible
    if len(energy_positioners) < 1:
        msg = "Cannot run energy_scan with empty *energy_positioners*."
        log.error(msg)
        raise ValueError(msg)
    # Resolve the detector and positioner list if given by name
    # try:
    #     real_detectors = registry.findall(name=detectors)
    # except exceptions.InvalidComponentLabel:
    #     log.warning(f"*detectors* is not a valid detector label: {detectors}")
    #     real_detectors = detectors
    # except exceptions.ComponentNotFound:
    #     log.debug("No registered detectors found.")
    #     real_detectors = detectors
    # else:
    real_detectors = registry.findall(detectors)
    log.debug(f"Found registered detectors: {real_detectors}")
    energy_positioners = [registry.find(ep) for ep in energy_positioners]
    time_positioners = [registry.find(tp) for tp in time_positioners]
    # Resolve the energy ranges if provided
    merge_ranges(*energies, default_exposure=exposure)
    # Convert an individual exposure time to an array of exposure times
    if not hasattr(exposure, "__iter__"):
        exposure = [exposure] * len(energies)
    # Correct for E0
    if isinstance(E0, str):
        # Look up E0 in the database if e.g. "Ni_K" is given as E0
        E0_str = E0
        E0 = edge_energy(E0)
    else:
        E0_str = None
    energies = np.asarray(energies)
    energies += E0
    # Prepare the positioners list with associated energies and exposures
    msg = "Offset for undulator gap not corrected in energy_scan"
    warnings.warn(msg)
    log.warning(msg)
    scan_args = [(motor, energies) for motor in energy_positioners]
    scan_args += [(motor, exposure) for motor in time_positioners]
    scan_args = [item for items in scan_args for item in items]
    # Do the actual scan
    config = load_config()
    yield from bp.list_scan(
        real_detectors,
        *scan_args,
        md={"edge": E0_str, "E0": E0, **md, **config},
    )
