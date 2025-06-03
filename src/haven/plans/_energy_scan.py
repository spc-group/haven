"""A bluesky plan to scan the X-ray energy and capture detector signals."""

import logging
from typing import Mapping, Sequence

from bluesky import plan_stubs as bps
from bluesky import plans as bp
from typing_extensions import NotRequired, TypedDict

from ..constants import edge_energy
from ..instrument import beamline
from ..preprocessors import baseline_decorator
from ..typing import DetectorList

__all__ = ["energy_scan"]


log = logging.getLogger(__name__)


class Metadata(TypedDict):
    edge: NotRequired[str]
    E0: float
    plan_name: str
    d_spacing: NotRequired[float | dict[str, float] | None]


# @shutter_suspend_decorator()
@baseline_decorator()
def energy_scan(
    energies: Sequence[float],
    exposure: float | Sequence[float] = 0.1,
    E0: float | str = 0,
    detectors: DetectorList = "ion_chambers",
    energy_devices: Sequence = ["monochromators", "undulators"],
    time_signals: Sequence | None = None,
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

    The calculated exposure times will be set for every signal in
    *time_signals*. If *time_signals* is ``None``, then
    *time_signals* will be determined automatically from
    *detectors*: for each detector, if it has an attribute/property
    *default_time_signal*, then this signal will be included in
    *time_signals*.

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

    **Metadata:**

    Several key pieces of metadata will be extract from the run. Any
    device in *energy_devices* that has a *d_spacing* attribute will
    be read for the ``"d_spacing"`` metadata entry.

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
    energy_devices
      Overrides the list of Ophyd devices used to set energy during
      this scan. Each device must have a child *energy* that is
      movable.
    time_signals
      Positioners that will receive the exposure time for each scan.
    md
      Additional metadata to pass on the to run engine.

    Yields
    ======
    Bluesky messages to execute the scan.

    """
    # Check that arguments are sensible
    if len(energy_devices) < 1:
        msg = "Cannot run energy_scan with empty *energy_devices*."
        log.error(msg)
        raise ValueError(msg)
    # Resolve the detector and positioner list if given by name
    if isinstance(detectors, str):
        detectors = beamline.devices.findall(detectors)
    real_detectors = []
    for det in detectors:
        real_detectors.extend(beamline.devices.findall(det))
    log.debug(f"Found registered detectors: {real_detectors}")
    energy_devices = beamline.devices.findall(energy_devices, allow_none=True)
    # Figure out which time positioners to use
    if time_signals is None:
        time_signals = [
            det.default_time_signal
            for det in detectors
            if hasattr(det, "default_time_signal")
        ]
    else:
        time_signals = [beamline.devices[tp] for tp in time_signals]
    # Convert an individual exposure time to an array of exposure times
    if not hasattr(exposure, "__iter__"):
        exposure = [exposure] * len(energies)
    # Correct for E0
    if isinstance(E0, str):
        # Look up E0 in the database if e.g. "Ni_K" is given as E0
        E0_str = E0
        E0_val = edge_energy(E0)
    else:
        E0_str = ""
        E0_val = float(E0)
    energies = [energy + E0_val for energy in energies]
    # Todo: sort the energies and exposure times by the energy
    # Prepare the positioners list with associated energies and exposures
    exposure = list(exposure)
    energy_movers = [device.energy for device in energy_devices]
    _args = [(mover, energies) for mover in energy_movers]
    _args += [(motor, exposure) for motor in time_signals]
    scan_args = [item for items in _args for item in items]
    # Add some extra metadata
    md_: Metadata = {"E0": E0_val, "plan_name": "energy_scan"}
    if E0_str != "":
        md_["edge"] = E0_str
    d_spacings = {}
    for device in energy_devices:
        if not hasattr(device, "d_spacing"):
            continue
        reading = yield from bps.read(device.d_spacing)
        if reading is None:
            log.warning(f"Did not receive reading for {device.name} d-spacing.")
            continue
        d_spacings[device.d_spacing.name] = reading[device.d_spacing.name]["value"]
    if len(d_spacings) == 1:
        # Only 1 mono, so just include the 1-and-only d-spacing
        md_["d_spacing"] = tuple(d_spacings.values())[0]
    elif len(d_spacings) > 1:
        # More than 1 mono, so include all d-spacings
        md_["d_spacing"] = d_spacings
    # Do the actual scan
    yield from bp.list_scan(
        [*real_detectors, *energy_devices],
        *scan_args,
        md={**md_, **md},
    )


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
