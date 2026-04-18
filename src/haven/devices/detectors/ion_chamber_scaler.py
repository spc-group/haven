"""Support for a set of ion chambers driven by a scaler/counter.

Expected TOML configuration.

[[ ion_chamber_scaler ]]
name = "upstream_ion_chambers"
prefix = "25idcVME:"

[ ion_chamber_scaler.ion_chambers.I0 ]
channel=2
preamp_prefix="255idc:SR02"

"""

from collections.abc import AsyncGenerator, Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
from event_model import DataKey
from ophyd_async.core import (
    Array1D,
    DetectorDataLogic,
    Device,
    DeviceVector,
    ReadableDataProvider,
    SignalR,
    StreamableDataProvider,
    derived_signal_r,
)
from ophyd_async.epics.core import (
    epics_signal_r,
)

from .usb_counter import SignalsProvider, USBCounter, USBCounterDriverIO, _reduce_array


class IonChamber(Device):
    """An ion chamber with a preamp and voltmeter."""

    def __init__(self, prefix: str, channel: int, name: str = ""):
        self.raw_counts_array = epics_signal_r(
            Array1D[np.int32], f"{prefix}mca{channel}.VAL"
        )
        self.raw_counts = derived_signal_r(_reduce_array, arr=self.raw_counts_array)
        super().__init__(name=name)


@dataclass
class StepDataLogic(DetectorDataLogic):
    driver: USBCounterDriverIO

    async def prepare_single(self, datakey_name: str) -> ReadableDataProvider:
        child_signals = [
            [chamber.raw_counts] for chamber in self.driver.ion_chambers.values()
        ]
        signals = [
            self.driver.current_channel,
            self.driver.clock_ticks,
            # Include all the flattened child signals
            *[sig for signals in child_signals for sig in signals],
        ]
        return SignalsProvider(
            signals=signals,
        )


@dataclass
class NullProvider(StreamableDataProvider):
    collections_written_signal: SignalR[int]

    async def make_datakeys(self, collections_per_event: int) -> dict[str, DataKey]:
        """Return a DataKey for each Readable that produces a Reading.

        Called before the first exposure is taken.
        """
        return {}


@dataclass
class FlyDataLogic(DetectorDataLogic):
    driver: USBCounterDriverIO

    async def prepare_unbounded(self, datakey_name: str):
        return NullProvider(self.driver.current_channel)


class IonChamberDriver(USBCounterDriverIO):
    def __init__(self, prefix: str, ion_chambers, name: str = ""):
        self.ion_chambers = DeviceVector(
            {
                params["channel"]: IonChamber(prefix=prefix, **params, name=name)
                for name, params in ion_chambers.items()
            }
        )
        super().__init__(prefix, name=name, channels=())


class IonChamberScaler(USBCounter):
    """A set of ion chambers connected to a scaler/counter, preamps, and
    voltmeters.

    """

    def __init__(
        self, prefix: str, ion_chambers: Mapping[str, Mapping], *, name: str = ""
    ):
        super().__init__(
            driver=IonChamberDriver(prefix, ion_chambers=ion_chambers, name=name),
            name=name,
            prefix=prefix,
        )
        step_logic = StepDataLogic(driver=self.driver)
        fly_logic = FlyDataLogic(driver=self.driver)
        self.add_detector_logics(step_logic, fly_logic)
        # We want to save data as "I0-counts", not a much longer auto-generated string
        for name, ion_chamber in ion_chambers.items():
            self.driver.ion_chambers[ion_chamber["channel"]].set_name(name)

    async def collect_pages(self) -> AsyncGenerator[Mapping[str, Any], Any]:
        assert False


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
