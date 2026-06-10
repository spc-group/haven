"""A bluesky plan to scan the X-ray energy over an X-ray edge and
capture detector signals.

"""

import logging
from dataclasses import dataclass
from functools import reduce
from typing import Mapping, Sequence

from bluesky.utils import MsgGenerator
from scanspec.specs import Concat, Zip

from haven.energy_ranges import EnergyRange
from haven.instrument import beamline
from haven.plans._energy_scan import energy_scan_from_scanspec, resolve_E0
from haven.protocols import DetectorList, EnergyDevice
from haven.specs import Axis, EnergyRegion, KWeighted, Spec, WavenumberRegion

log = logging.getLogger(__name__)


__all__ = ["xafs_scan"]


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]  # noqa: E203


@dataclass()
class XAFSRegion:
    domain: str
    start: float
    stop: float
    num: int
    exposure: float | None = None
    k_weight: float = 0


def regions_to_scanspec(
    regions: Sequence[XAFSRegion | EnergyRange | tuple], E0: float, axes: Sequence[Axis]
) -> Spec:
    """Accept a set of region defitions and produce a scan spec to
    scan over them.

    """
    segments = []
    last_stop = None
    line_types = {"e": EnergyRegion, "k": WavenumberRegion}
    for region_ in regions:
        if isinstance(region_, EnergyRange):
            raise TypeError("Cannot use EnergyRange objects with scanspec.")
        elif isinstance(region_, XAFSRegion):
            region = region_
        else:
            region = XAFSRegion(*region_)
        # Build each energy region as a trajectory of lines
        Line = line_types[region.domain.lower()]
        start, stop, num = region.start, region.stop, region.num
        if start == last_stop:
            # Adjacent regions are connected, remove duplicated start value
            start += (stop - start) / (num - 1)
            num -= 1
        lines = [Line(axis, start, stop, num, E0=E0) for axis in axes]
        line_spec = reduce(Zip, lines)
        # Apply exposure times weighted by wavenumber
        if region.exposure is not None:
            line_spec = KWeighted(
                spec=line_spec,
                E0=E0,
                base_duration=region.exposure,
                k_weight=region.k_weight,
            )
        segments.append(line_spec)
        last_stop = stop
    spec = reduce(Concat, segments)
    return spec


def xafs_scan(
    detectors: DetectorList,
    *energy_ranges: EnergyRange | XAFSRegion | tuple,
    E0: float | str,
    energy_devices: Sequence[EnergyDevice | str] = ["monochromators", "undulators"],
    md: Mapping = {},
) -> MsgGenerator[str]:
    """Collect a spectrum by scanning X-ray energies relative to an
    absorbance edge.

    Used like:

    .. code-block:: python

        xafs_scan(
          [vortex_me4, …],
          XAFSRegion("E", start=…, stop=…, num=…, exposure=…),
          XAFSRegion("E", start=…, stop=…, num=…),
          XAFSRegion("k", start=…, stop=…, num=…, exposure=…, k_weight=…),
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
            [vortex_me4, …],
            XAFSRegion("E", -100, -30, 46, exposure=0.5),
            XAFSRegion("E", -30, 50, 161, exposure=1.),
            XAFSRegion("k", 3.623, 8, 51, exposure=1.5, weight=0.5),
            E0="Ni_K"
        )

    *energy_ranges* can also be tuples like:

    .. code-block:: python

        xafs_scan(
            [vortex_me4, …],
            ("E", -100, -30, 46, 0.5),
            ("E", -30, 50, 161, 1.),
            ("k", 3.623, 8, 51, 1.5, 0.5),
            E0="Ni_K"
        )

    Detectors will be ``prepare()``'d at each step to ensure they have
    the correct exposure time.

    *energy_devices* is mostly useful for
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
    md
      Additional metadata to pass to the run engine.

    """
    # Resolve energy devices into the actual positioners
    energy_devices = beamline.devices.findall(energy_devices, allow_none=True)
    energy_movers = [
        device.energy if isinstance(device, EnergyDevice) else device
        for device in energy_devices
    ]
    E0_val, E0_str = resolve_E0(E0)
    # Build up the energy scan specification
    md_ = {
        "E0": E0_val,
        "plan_name": "xafs_scan",
        "plan_args": {
            "detectors": list(map(repr, detectors)),
            "E0": E0,
            "energy_ranges": list(energy_ranges),
            "energy_devices": list(map(repr, energy_devices)),
        },
    }
    if E0_str != "":
        md_["edge"] = E0_str
    # Execute the energy scan
    md_.update(md)
    spec = regions_to_scanspec(energy_ranges, E0=E0_val, axes=energy_movers)
    # md_["scanspec"] = spec.serialize()
    yield from energy_scan_from_scanspec(
        detectors=detectors,
        spec=spec,
        md=md_,
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
