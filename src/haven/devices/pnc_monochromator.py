import logging
from functools import cached_property

from ophyd_async.core import (
    Device,
    MovableLogic,
    StandardMovable,
    StandardReadable,
)
from ophyd_async.core import StandardReadableFormat as Format
from ophyd_async.core import (
    soft_signal_r_and_setter,
)
from ophyd_async.epics.core import epics_signal_r, epics_signal_rw

from .motor import Motor

log = logging.getLogger(__name__)


class EnergyMovable(StandardMovable, StandardReadable, Device):

    def __init__(self, prefix: str, *, name: str = ""):
        self.setpoint = epics_signal_rw(float, f"{prefix}monoE")
        with self.add_children_as_readables(Format.HINTED_SIGNAL):
            self.readback = epics_signal_r(float, f"{prefix}AtoE")
        super().__init__(name=name)

    @cached_property
    def movable_logic(self) -> MovableLogic:
        return MovableLogic(setpoint=self.setpoint, readback=self.readback)


class PNCMonochromator(StandardReadable, Device):
    _ophyd_labels_ = {"monochromators"}

    def __init__(
        self,
        prefix: str,
        *,
        bragg_motor: str,
        pitch2_motor: str,
        roll2_motor: str,
        xtal2_translation_motor: str,
        name: str = "",
    ):
        with self.add_children_as_readables(Format.CONFIG_SIGNAL):
            self.d_spacing = epics_signal_r(float, f"{prefix}xtal.VAL")
            self.d_spacing_unit, _ = soft_signal_r_and_setter(
                str, initial_value="angstroms"
            )
        with self.add_children_as_readables():
            self.bragg = Motor(bragg_motor)
            self.energy = EnergyMovable(prefix=prefix)
        # We want secondary motors to be readable but not hinted
        self.pitch2 = Motor(pitch2_motor)
        self.roll2 = Motor(roll2_motor)
        self.xtal2_translation = Motor(xtal2_translation_motor)
        self.add_readables(
            [
                self.pitch2.user_readback,
                self.roll2.user_readback,
                self.xtal2_translation.user_readback,
            ]
        )
        self._calibration_energy = epics_signal_rw(float, f"{prefix}")
        super().__init__(name=name)


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2026, UChicago Argonne, LLC
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
