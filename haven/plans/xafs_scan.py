"""A bluesky plan to scan the X-ray energy over an X-ray edge and
capture detector signals.

"""

from typing import Union, Sequence, Optional, Mapping

import numpy as np

from ..energy_ranges import ERange
from .energy_scan import energy_scan
from ..typing import DetectorList


__all__ = ["xafs_scan"]


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]  # noqa: E203


def xafs_scan(
    E_min: float,
    *E_params: Sequence[float],
    k_step: Optional[float] = None,
    k_exposure: Optional[float] = None,
    k_max: Optional[float] = None,
    k_weight: float = 0.0,
    E0: Union[float, str] = 0,
    detectors: DetectorList = "ion_chambers",
    energy_positioners: Sequence = ["energy"],
    time_positioners: Sequence = ["I0_exposure_time"],
    md: Mapping = {},
):
    """Collect a spectrum by scanning X-ray energies relative to an
    absorbance edge.

    Used like:

    .. code-block:: python

        xafs_scan(energy, step, exposure, energy, step, exposure energy, ...)

    The optional parameter *E0* can either be an absolute energy in
    electron-volts, or a string of the form "Ni_K" to be looked up in
    a reference table. If omitted, energies will be absolute and
    K-space parameters should be omitted.

    If *E0* is given, then energies should then be given relative to
    this edge in groups of ``(min, step, exposure, max)``. More than
    one range can be specified by giving additional groups of ``(step,
    exposure, max)`` since the maximum energy of the previous range
    will be the minimum energy of the subsequent range.

    For example, the following invocation will scan three regions
    relative to the Ni K-edge:

    - Pre-edge: from 100 eV below the edge to 30 eV below the edge in
      2 eV steps with 0.5 sec exposure.
    - Edge: from 30 eV below the edge to 50 eV above the edge in 0.1
      eV steps with 1 sec exposure.
    - EXAFS: from 50 eV above the edge to K=8 Å⁻ in 0.2 Å⁻ steps with
      1.5 sec exposure.

    .. code-block:: python

        xafs_scan(-100, 2, 0.5, -30, 0.1, 1., 50,
                  k_step=0.2, k_exposure=1.5, k_max=8,
                  E0="Ni_K")

    For measuring the extended structure (EXAFS) *k_step*, *k_max*,
    and *k_exposure* can be given instead of the equivalent
    energies. *k_weights* will apply longer exposure times to higher K
    values.

    *detectors*, *energy_positioners*, and *time_positioners* are
     mostly useful for debugging.

    Parameters
    ==========
    E_min
      The starting energy for the first energy range, in eV.
    E_params
      Should be any number of parameters of the form ``energy_step,
      exposure, energy, energy_step, exposure, energy, ...``. Energies
      should be in eV and *exposure* in seconds.
    k_step
      Wavenumber (k) step for the EXAFS region, in Å⁻.
    k_exposure
      Base exposure time for the EXAFS region, in seconds.
    k_max
      Last energy for the EXAFS region, in eV.
    k_weight
      Weighting factor for exposure time at higher energies in the
      EXAFS region. Default (0) results in constant exposure.
    E0
      An edge energy, in eV, or name of the edge of the form
      "Ni_L3". All energies will be relative to this value.
    detectors
      Overrides the list of Ophyd signals to record during this
      scan. Useful for testing.
    energy_positioners
      Overrides the list of Ophyd positioners used to set energy
      during this scan. Useful for testing.
    time_positioners
      Overrides the list of Ophyd positioners used to set exposure
      time during this scan. Useful for testing.

    """
    # Make sure the right number of energies have been given
    # Turn the energies in energy ranges
    curr_E_min = E_min
    energy_ranges = []
    for E_step, E_exposure, E_max in chunks(E_params, 3):
        energy_ranges.append(ERange(curr_E_min, E_max, E_step, exposure=E_exposure))
        curr_E_min = E_max
    # Convert energy ranges to energy list and exposure list
    energies = []
    exposures = []
    for rng in energy_ranges:
        energies.extend(rng.energies())
        exposures.extend(rng.exposures())
    energies = np.asarray(energies, dtype="float64")
    exposures = np.asarray(exposures, dtype="float64")
    # Execute the energy scan
    yield from energy_scan(
        energies=energies,
        exposure=exposures,
        E0=E0,
        detectors=detectors,
        energy_positioners=energy_positioners,
        time_positioners=time_positioners,
        md=md,
    )
