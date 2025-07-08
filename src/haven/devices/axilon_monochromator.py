import asyncio
import logging

import numpy as np
from ophyd_async.core import (
    AsyncStatus,
    StandardReadable,
    StandardReadableFormat,
    StrictEnum,
)
from ophyd_async.epics.core import epics_signal_rw
from pint import Quantity, UnitRegistry
from scipy import constants

from .motor import Motor

log = logging.getLogger(__name__)

ureg = UnitRegistry()

h = (
    constants.physical_constants["Planck constant in eV/Hz"][0]
    * ureg.electron_volt
    / ureg.hertz
)
c = constants.c * ureg.meter / ureg.second


def energy_to_bragg(energy: Quantity, *, d_spacing: Quantity) -> Quantity:
    bragg = np.arcsin(h * c / 2 / d_spacing / energy)
    return bragg


class EnergyMotor(Motor):
    @AsyncStatus.wrap
    async def calibrate(
        self, truth: float, dial: float | None = None, relative: bool = False
    ):
        """Calibrate mono energy by applying an offset to the Bragg motor.

        Parameters
        ==========
        truth
          The actual energy when the readback is set to *target*.
        dial
          The readback/setpoint position corresponding for when the
          motor is actually at *truth*.
        relative
          If true, the offset will be added to any previous offsets,
          otherwise previous offsets will be overwritten (default).

        """
        # Target the current position if none provided
        if dial is None:
            dial = await self.user_readback.get_value()
        # Get some additional data
        energy_unit, bragg_unit, d_val, d_unit, last_offset = await asyncio.gather(
            self.motor_egu.get_value(),
            self.parent.bragg.motor_egu.get_value(),
            self.parent.d_spacing.get_value(),
            self.parent.d_spacing_unit.get_value(),
            self.parent.transform_offset.get_value(),
        )
        d = d_val * ureg(d_unit.lower())
        # Convert from energy to bragg angle
        bragg_truth = energy_to_bragg(truth * ureg(energy_unit), d_spacing=d)
        bragg_dial = energy_to_bragg(dial * ureg(energy_unit), d_spacing=d)
        offset = bragg_truth - bragg_dial
        # Set the offset PV
        offset_val = offset.to(ureg(bragg_unit)).magnitude
        if relative:
            offset_val += last_offset
        await self.parent.transform_offset.set(offset_val)


class AxilonMonochromator(StandardReadable):
    _ophyd_labels_ = {"monochromators"}

    class Mode(StrictEnum):
        FIXED_OFFSET = "Si(111) Fixed Offset"
        CHANNEL_CUT = "Si(111) Channel-cut"
        ML48 = "Multi-layer 4.8nm"
        ML24 = "Multi-layer 2.4nm"

    def __init__(self, prefix: str, name: str = ""):
        # Full (hinted) motors
        with self.add_children_as_readables():
            # Virtual motors
            self.energy = EnergyMotor(f"{prefix}Energy")
            self.bragg = Motor(f"{prefix}ACS:m3")
        # Non-hinted motors need to be added deliberately
        self.beam_offset = Motor(f"{prefix}Offset")
        # ACS Motors
        self.gap = Motor(f"{prefix}ACS:m4")
        self.horizontal = Motor(f"{prefix}ACS:m1")
        self.vertical = Motor(f"{prefix}ACS:m2")
        self.roll2 = Motor(f"{prefix}ACS:m5")
        self.pitch2 = Motor(f"{prefix}ACS:m6")
        extra_motors = [
            self.beam_offset,
            self.gap,
            self.horizontal,
            self.vertical,
            self.roll2,
            self.pitch2,
        ]
        self.add_readables([m.user_readback for m in extra_motors])
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            # Transform constants, etc.
            self.id_tracking = epics_signal_rw(bool, f"{prefix}ID_tracking")
            self.id_offset = epics_signal_rw(float, f"{prefix}ID_offset")
            self.d_spacing = epics_signal_rw(float, f"{prefix}dspacing")
            self.d_spacing_unit = epics_signal_rw(str, f"{prefix}dspacing.EGU")
            self.mode = epics_signal_rw(self.Mode, f"{prefix}mode")
            self.transform_d_spacing = epics_signal_rw(float, f"{prefix}EnergyC1.VAL")
            self.transform_direction = epics_signal_rw(float, f"{prefix}EnergyC2.VAL")
            self.transform_offset = epics_signal_rw(float, f"{prefix}EnergyC3.VAL")
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
