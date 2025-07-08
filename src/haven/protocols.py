"""Protocols for the various kinds of monos at our beamlines."""

from abc import abstractmethod
from typing import (
    Protocol,
    Sequence,
    Union,
    runtime_checkable,
)

from bluesky.protocols import HasName, Locatable, Movable, Readable
from ophyd import Component, Device, Signal
from ophyd_async.epics.motor import Motor

Detector = Union[Device, Component, Signal, str]


DetectorList = Union[str, Sequence[Detector]]


Motor = Union[Device, Component, Signal, str]


class EnergyDevice(Readable, HasName):
    energy: Locatable[float]


class Monochromator(EnergyDevice):
    d_spacing: Readable
    bragg: Motor
    beam_offset: Readable
    vertical: Movable


@runtime_checkable
class Calibratable(Protocol):
    @abstractmethod
    def calibrate(self, truth: float, target: float | None = None): ...


class FixedOffsetMonochromator(Monochromator):
    beam_offset: Movable


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
