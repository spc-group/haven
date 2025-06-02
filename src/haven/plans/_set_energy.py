from typing import Literal, Sequence

from bluesky import plan_stubs as bps
from bluesky.protocols import Movable

from ..instrument import beamline
from ..typing import DetectorList

__all__ = ["set_energy"]


Harmonic = str | int | None


def auto_harmonic(
    energy: float, thresholds: Sequence[float | int] = [10000, 20000]
) -> int:
    """Decide which harmonic to use for the undulator at a given energy.

    Parameters
    ==========
    energy
      The energy for deciding which harmonic to use.
    thresholds
      Energies marking the boundaries for switching from one harmonic
      to the next. Should increase monotonically.

    """
    segment = sum([energy > th for th in thresholds])
    harmonic = segment * 2 + 1
    return harmonic


def set_energy(
    energy: float,
    harmonic: int | Literal["auto"] | None = "auto",
    undulator_offset: float | Literal["auto"] | None = "auto",
    undulators: DetectorList = ["undulators"],
    monochromators: DetectorList = ["monochromators"],
):
    """Set the energy of the beamline, in electron volts.

    Moves both the mono energy, and the undulator energy with a
    calibrated offset.

    The *harmonic* parameter selects a harmonic for the undulator. If
    ``"auto"``, then the harmonic will be selected based on the
    energy. If *harmonic* is ``None``, then the current harmonic is
    used. If *harmonic* is an integer (e.g. 1, 3, 5) then this value
    will be used.

    The *undulator_offset* parameter sets the offset applied to any
    undulators. If ``"auto"``, then the offset will be selected from a
    calibration look-up table. If ``None``, then offset will not be
    changed. Otherwise, *id_offset* will be set directly.

    Parameters
    ==========
    energy
      The target energy of the beamline, in electron-volts.
    harmonic
      Which harmonic to use for the undulator. Can be an integer
      (e.g. 1, 3, 5), ``None``, or ``"auto"``.
    undulator_offset
      Offset to apply for the undulators. Can be a float, ``None``, or
      ``"auto"``.

    """
    if undulators:
        undulators = beamline.devices.findall(undulators, allow_none=True)
    if monochromators:
        monochromators = beamline.devices.findall(monochromators, allow_none=True)
    # Prepare arguments for undulator harmonics and offsets
    mv_args: list[Movable | int | float] = []
    if harmonic == "auto":
        harmonic = auto_harmonic(energy)
    if harmonic is not None:
        harmonic_signals = [undulator.harmonic_value for undulator in undulators]
        mv_args.extend(arg for signal in harmonic_signals for arg in (signal, harmonic))
    if undulator_offset == "auto":
        offsets = [undulator.auto_offset(energy) for undulator in undulators]
    elif undulator_offset is not None:
        offsets = [undulator_offset for undulator in undulators]
    else:
        offsets = []
    # Move the undulator harmonics/offsets before setting energy
    for offset, undulator in zip(offsets, undulators):
        if offset is not None:
            mv_args.extend((undulator.energy.offset, offset))
    if len(mv_args) > 0:
        yield from bps.mv(*mv_args)
    # Prepare arguments for moving energy
    energy_devices = [device.energy for device in [*undulators, *monochromators]]
    args = [arg for device in energy_devices for arg in (device, energy)]
    # Execute the plan
    yield from bps.mv(*args)


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
