"""Support for a set of ion chambers driven by a scaler/counter.

Expected TOML configuration.

[[ ion_chamber_scaler ]]
name = "upstream_ion_chambers"
prefix = "25idcVME:"

[ ion_chamber_scaler.ion_chambers.I0 ]
channel=2
preamp_prefix="255idc:SR02"

"""

import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from bluesky.protocols import Reading
from ophyd_async.core import (
    DetectorDataLogic,
    ReadableDataProvider,
)
from ophyd_async.epics.core import (
    EpicsDevice,
)

from .usb_counter import SignalsProvider, USBCounter, USBCounterDriverIO


class IonChamber(EpicsDevice):
    """An ion chamber with a preamp and voltmeter."""

    pass


class IonChamberProvider(SignalsProvider):
    async def make_readings(self) -> dict[str, Reading]:
        array_coros = [sig.read() for sig in self.array_signals]
        readings, array_readings = await asyncio.gather(
            super().make_readings(),
            *array_coros,
        )
        return readings


@dataclass
class StepDataLogic(DetectorDataLogic):
    driver: USBCounterDriverIO

    async def prepare_single(self, datakey_name: str) -> ReadableDataProvider:
        return IonChamberProvider(
            signals=[
                self.driver.current_channel,
                self.driver.clock_ticks,
            ],
            array_signals=[mca.counts for mca in self.mcas],
        )


class IonChamberDriver(USBCounterDriverIO):
    def __init__(self, prefix: str, channels: Sequence[int], name: str = ""):
        super().__init__(prefix, name=name, channels=channels)


class IonChamberScaler(USBCounter):
    """A set of ion chambers connected to a scaler/counter, preamps, and
    voltmeters.

    """

    def __init__(
        self, prefix: str, ion_chambers: Mapping[str, Mapping], *, name: str = ""
    ):
        super().__init__(name=name, prefix=prefix)
        step_logic = StepDataLogic(driver=self.driver)
        self.add_detector_logics(step_logic)


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
