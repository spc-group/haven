import asyncio
from collections.abc import Sequence
from dataclasses import dataclass

from bluesky.protocols import Reading
from event_model import DataKey
from ophyd_async.core import (
    DetectorDataLogic,
    Device,
    ReadableDataProvider,
    SignalDataProvider,
    SignalR,
    StrictEnum,
)
from ophyd_async.epics.core import epics_signal_r, epics_signal_rw

from .tetramm import BaseTetrAmmDetector


class Precision(StrictEnum):
    ZERO = "0"
    ONE = "1"
    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"
    SIX = "6"
    SEVEN = "7"
    EIGHT = "8"
    NINE = "9"


@dataclass()
class SplitIonChamberDataProvider(ReadableDataProvider):
    ion_chamber: Device

    async def make_datakeys(self) -> dict[str, DataKey]:
        return await self.ion_chamber.describe()

    async def make_readings(self) -> dict[str, Reading]:
        readings = await asyncio.gather(
            self.ion_chamber.current.read(cached=False),
            self.ion_chamber.difference.read(cached=False),
            self.ion_chamber.position.read(cached=False),
            self.ion_chamber.positive_plate.current.read(cached=False),
            self.ion_chamber.negative_plate.current.read(cached=False),
        )
        return {key: val for reading in readings for key, val in reading.items()}


@dataclass()
class SplitIonChamberDataLogic(DetectorDataLogic):
    ion_chamber: Device

    async def prepare_single(self, datakey_name: str) -> ReadableDataProvider:
        """Provider can only work for a single event."""
        return SplitIonChamberDataProvider(self.ion_chamber)


@dataclass
class SignalDataLogic(DetectorDataLogic):
    signal: SignalR
    hinted: bool = True

    async def prepare_single(self, datakey_name: str) -> SignalDataProvider:
        return SignalDataProvider(self.signal)

    def get_hinted_fields(self, datakey_name: str) -> Sequence[str]:
        return [self.signal.name] if self.hinted else []


class SplitIonChamber(Device):
    def __init__(
        self,
        prefix: str,
        axis: str,
        positive_channel: int,
        negative_channel: int,
        name: str = "",
    ):
        self.current = epics_signal_r(float, f"{prefix}Current{axis}:MeanValue_RBV")
        self.difference = epics_signal_r(float, f"{prefix}Diff{axis}:MeanValue_RBV")
        self.position = epics_signal_r(float, f"{prefix}Pos{axis}:MeanValue_RBV")
        self.positive_plate = SplitIonChamberPlate(prefix, channel_num=positive_channel)
        self.negative_plate = SplitIonChamberPlate(prefix, channel_num=negative_channel)
        self.position_offset = epics_signal_rw(float, f"{prefix}PositionOffset{axis}")
        self.position_scale = epics_signal_rw(float, f"{prefix}PositionScale{axis}")
        self.precision = epics_signal_rw(Precision, f"{prefix}PositionPrec{axis}")
        self.config_sigs = [
            self.position_offset,
            self.position_scale,
            self.precision,
            *self.positive_plate.config_sigs,
            *self.negative_plate.config_sigs,
        ]
        super().__init__(name=name)


class SplitIonChamberPlate(Device):
    def __init__(self, prefix: str, channel_num: int, name: str = ""):
        self.current = epics_signal_r(
            float, f"{prefix}Current{channel_num}:MeanValue_RBV"
        )
        self.offset = epics_signal_rw(int, f"{prefix}CurrentOffset{channel_num}")
        self.scale = epics_signal_rw(int, f"{prefix}CurrentScale{channel_num}")
        self.precision = epics_signal_rw(Precision, f"{prefix}CurrentPrec{channel_num}")
        self.config_sigs = [self.offset, self.scale, self.precision]
        super().__init__(name=name)


class SplitIonChamberSet(BaseTetrAmmDetector):
    def __init__(self, *args, prefix, **kwargs):
        self.horizontal = SplitIonChamber(
            prefix, axis="Y", negative_channel=1, positive_channel=2
        )
        self.vertical = SplitIonChamber(
            prefix, axis="X", negative_channel=3, positive_channel=4
        )
        self.current = epics_signal_r(float, "SumAll:MeanValue_RBV")
        # Build configuration signals
        config_sigs = [
            *self.vertical.config_sigs,
            *self.horizontal.config_sigs,
        ]
        super().__init__(*args, prefix=prefix, config_sigs=config_sigs, **kwargs)
        self.add_detector_logics(
            SplitIonChamberDataLogic(ion_chamber=self.vertical),
            SplitIonChamberDataLogic(ion_chamber=self.horizontal),
            SignalDataLogic(signal=self.current, hinted=True),
        )


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
