import logging

from ophyd_async.core import StandardReadable, StandardReadableFormat, StrictEnum
from ophyd_async.epics.core import epics_signal_rw

from .motor import Motor

log = logging.getLogger(__name__)


class Monochromator(StandardReadable):
    _ophyd_labels_ = {"monochromators"}

    class Mode(StrictEnum):
        FIXED_OFFSET = "Si(111) Fixed Offset"
        CHANNEL_CUT = "Si(111) Channel-cut"
        ML48 = "Multi-layer 4.8nm"
        ML24 = "Multi-layer 2.4nm"

    def __init__(self, prefix: str, name: str = ""):
        with self.add_children_as_readables():
            # Virtual motors
            self.energy = Motor(f"{prefix}Energy")
            self.offset = Motor(f"{prefix}Offset")
            # ACS Motors
            self.bragg = Motor(f"{prefix}ACS:m3")
            self.gap = Motor(f"{prefix}ACS:m4")
            self.horiz = Motor(f"{prefix}ACS:m1")
            self.vert = Motor(f"{prefix}ACS:m2")
            self.roll2 = Motor(f"{prefix}ACS:m5")
            self.pitch2 = Motor(f"{prefix}ACS:m6")
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            # Transform constants, etc.
            self.id_tracking = epics_signal_rw(bool, f"{prefix}ID_tracking")
            self.id_offset = epics_signal_rw(float, f"{prefix}ID_offset")
            self.d_spacing = epics_signal_rw(float, f"{prefix}dspacing")
            self.d_spacing_unit = epics_signal_rw(str, f"{prefix}dspacing.EGU")
            self.mode = epics_signal_rw(self.Mode, f"{prefix}mode")
            self.energy_constant1 = epics_signal_rw(float, f"{prefix}EnergyC1.VAL")
            self.energy_constant2 = epics_signal_rw(float, f"{prefix}EnergyC2.VAL")
            self.energy_constant3 = epics_signal_rw(float, f"{prefix}EnergyC3.VAL")
            # Interferomters
            # self.roll_int = Motor(f"{prefix}ACS:m7")
            # self.pi_int = Motor(f"{prefix}ACS:m8")
        super().__init__(name=name)


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
