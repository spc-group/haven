"""A bluesky plan to scan the X-ray energy over an X-ray edge and
capture detector signals.

"""

import logging
from typing import Mapping, Sequence

from bluesky.utils import MsgGenerator

from haven import exceptions
from haven.energy_ranges import EnergyRange, from_tuple, merge_ranges
from haven.plans._energy_scan import energy_scan
from haven.protocols import DetectorList

log = logging.getLogger(__name__)


__all__ = ["xafs_scan"]


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]  # noqa: E203


def xafs_scan(
    detectors: DetectorList,
    *energy_ranges: Sequence[EnergyRange | tuple],
    E0: float | str,
    energy_devices: Sequence = ["monochromators", "undulators"],
    time_signals: Sequence | None = None,
    md: Mapping = {},
) -> MsgGenerator[str]:
    """Collect a spectrum by scanning X-ray energies relative to an
    absorbance edge.

    Used like:

    .. code-block:: python

        xafs_scan(
          [detector1, ...],
          ERange(start, stop, step, exposure),
          E0=8333,
        )

    The parameter *E0* can either be an absolute energy in
    electron-volts, or a string of the form "Ni-K" to be looked up in
    a reference table. If ``E0=0`` is given, energies will be absolute
    and K-space parameters should probably be omitted.

    Positional arguments should be energy ranges, like
    :py:class:`~haven.energy_ranges.ERange` or
    :py:class:`~haven.energy_ranges.KRange`.

    For example, the following invocation will scan three regions
    relative to the Ni K-edge:

    - Pre-edge: from 100 eV below the edge to 30 eV below the edge in
      2 eV steps with 0.5 sec exposure.
    - Edge: from 30 eV below the edge to 50 eV above the edge in 0.1
      eV steps with 1 sec exposure.
    - EXAFS: from 50 eV above the edge to K=8 Å⁻ in 0.2 Å⁻ steps with
      1.5 sec exposure and 0.5 k-weight.

    .. code-block:: python

        xafs_scan(
            [],  # Empty detector list for demo
            ERange(-100, -30, 2, exposure=0.5),
            ERange(-30, 50, 0.1, exposure=1.),
            KRange(3.623, 8, 0.2, exposure=1.5, weight=0.5),
            E0="Ni_K"
        )

    *energy_ranges* can also be tuples like:
    - ("E", -50, 0, 0.25, 1) == ERange(-50, 0, step=0.25, exposure=1)
    - ("k", -50, 0, 0.25, 1.5, 1) == KRange(-50, 0, step=0.25, exposure=1.5, weight=1)

    The calculated exposure times, including k-weights, will be set
    for every signal in *time_signals*. If *time_signals* is ``None``,
    then *time_signals* will be determined automatically from
    *detectors*: for each detector, if it has an attribute/property
    *default_time_signal*, then this signal will be included in
    *time_signals*.

    *energy_signals*, and *time_signals* are mostly useful for
    debugging.

    Parameters
    ==========
    detectors
      Which detectors to measure. Can be a label string
      (e.g. ``"ion_chambers"``), or sequence that includes label
      strings (e.g. ``["ion_chambers", detector1, "area_detectors"]``.
    *energy_ranges
      Energy ranges to scan.
    E0
      An edge energy, in eV, or name of the edge of the form
      "Ni_L3". All energies will be relative to this value.
    energy_devices
      Overrides the list of Ophyd devices used to set energy during
      this scan. Each device must have a child *energy* that is
      movable.
    time_signals
      Overrides the list of Ophyd positioners used to set exposure
      time during this scan. Useful for testing.
    md
      Additional metadata to pass to the run engine.

    """
    # Convert energy ranges to energy list and exposure list
    ranges = [from_tuple(rng) for rng in energy_ranges]
    energies, exposures = merge_ranges(*ranges)
    if len(energies) < 1:
        raise exceptions.NoEnergies("Plan would not produce any energy points.")
    # Execute the energy scan
    md_ = {
        "plan_name": "xafs_scan",
        "plan_args": {
            "detectors": list(map(repr, detectors)),
            "energy_ranges": list(map(repr, ranges)),
            "E0": E0,
            "energy_devices": list(map(repr, energy_devices)),
            "time_signals": (
                list(map(repr, time_signals))
                if time_signals is not None
                else time_signals
            ),
        },
    }
    yield from energy_scan(
        energies=energies,
        exposure=exposures,
        E0=E0,
        detectors=detectors,
        energy_devices=energy_devices,
        time_signals=time_signals,
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
