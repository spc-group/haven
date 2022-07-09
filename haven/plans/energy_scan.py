"""A bluesky plan to scan the X-ray energy and capture detector signals.

"""

import logging
from typing import Sequence

from bluesky import plans as bp


__all__ = ["energy_scan"]


log = logging.getLogger(__name__)


def energy_scan(energies: Sequence, exposure: float, detectors: Sequence = []):
    """Collect a spectrum by scanning X-ray energy.

    Usage
    =====
    energies = range(13000, 13100)
    RE(energy_scan(energies, exposure=0.5))

    Parameters
    ==========
    energies
      The X-ray energies, in eV, over which to scan.
    exposure
      How long, in seconds, to count at each energy.
    detectors
      The detectors to collect X-ray signal from at each energy.

    Yields
    ======
    Bluesky messages to execute the scan.
    """
    raise NotImplementedError
    # This could be the simple way of doing it in bluesky
    energy_motor = None
    yield from bp.list_scan(energy_motor, energies)
