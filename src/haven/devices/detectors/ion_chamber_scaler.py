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
import logging
import re
from collections.abc import AsyncGenerator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
from bluesky.protocols import Reading
from event_model import DataKey
from ophyd_async.core import (
    Array1D,
    AsyncStatus,
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
    epics_signal_rw,
)

from ..srs570 import SRS570PreAmplifier
from .usb_counter import SignalsProvider, USBCounter, USBCounterDriverIO, _reduce_array

log = logging.getLogger("haven")


def remove_dark_current(raw_counts: int, expression: str, clock_ticks: int) -> float:
    """Correct for the previously measured dark current."""
    return raw_counts


class IonChamber(Device):
    """An ion chamber with a preamp and voltmeter."""

    def __init__(
        self,
        prefix: str,
        channel: int,
        preamp_prefix: str,
        *,
        name: str = "",
    ):
        self.channel = channel
        self.preamp = SRS570PreAmplifier(preamp_prefix)
        self.raw_counts_array = epics_signal_r(
            Array1D[np.int32], f"{prefix}MCS:mca{channel}.VAL"
        )
        self.raw_counts = derived_signal_r(_reduce_array, arr=self.raw_counts_array)
        self.calculation_expression = epics_signal_rw(
            str, f"{prefix}scaler1_calc{channel}.CALC"
        )
        super().__init__(name=name)

    @AsyncStatus.wrap
    async def calibrate(self, truth: float, dial: float | None = None):
        """Calibrate ion chamber dark current by setting an offset to the .

        Parameters
        ==========
        truth
          The actual energy when the readback is set to *target*.
        dial
          The counts corresponding for when the
          ion chamber should read *truth*.

        """
        ticks, counts = await asyncio.gather(
            self.parent.parent.clock_ticks.get_value(),
            self.raw_counts.get_value(),
        )
        channel_char = chr(64 + self.channel).upper()
        formula = f"{channel_char} - {counts / ticks} * A"
        await self.calculation_expression.set(formula)


@dataclass
class IonChamberDataLogic(DetectorDataLogic):
    driver: USBCounterDriverIO

    async def prepare_single(self, datakey_name: str) -> ReadableDataProvider:
        return SignalsProvider(
            signals=[
                self.driver.elapsed_time,
                self.driver.current_channel,
                self.driver.clock_ticks,
            ]
        )


@dataclass
class IonChamberDataProvider(SignalsProvider):
    ion_chambers: Sequence[IonChamber]
    clock_signal: SignalR
    calc_re = re.compile(r"^[A-Za-z]\s*\*\s*(\d+)\s*/\s*[A-Za-z]$")

    async def make_datakeys(self) -> dict[str, DataKey]:
        """Return a DataKey for each Readable that produces a Reading.

        Called before the first exposure is taken.
        """
        other_keys = await super().make_datakeys()
        new_keys = {
            f"{ic.name}-counts": {
                "dtype": "float",
                "dtype_numpy": "<f32",
                "shape": [],
            }
            for ic in self.ion_chambers
        }
        return {**other_keys, **new_keys}

    async def make_readings(self) -> dict[str, Reading]:
        coros = [ic.calculation_expression.get_value() for ic in self.ion_chambers]
        coros = [
            super().make_readings(),
            self.clock_signal.get_value(cached=False),
            *coros,
        ]
        readings, clock_ticks, *calc_expressions = await asyncio.gather(*coros)
        for ic, calc_expr in zip(self.ion_chambers, calc_expressions):
            # Apply dark current correction
            reading = readings[ic.raw_counts.name]
            match = self.calc_re.match(calc_expr)
            if match:
                factor = float(match.group(1))
                new_reading = {
                    **reading,
                    "value": reading["value"] * factor / clock_ticks,
                }
            else:
                # Could not parse the calc expression, just return the reading
                log.warning(
                    "Could not parse the calc expression {calc_expr} for {ic.name}."
                )
                new_reading = reading
            readings[f"{ic.name}-counts"] = new_reading
        return readings


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
        return IonChamberDataProvider(
            signals=signals,
            ion_chambers=self.driver.ion_chambers.values(),
            clock_signal=self.driver.clock_ticks,
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
        ion_chamber_logic = IonChamberDataLogic(driver=self.driver)
        fly_logic = FlyDataLogic(driver=self.driver)
        self.add_detector_logics(step_logic, fly_logic, ion_chamber_logic)
        # We want to save data as "I0-counts", not a much longer auto-generated string
        for name, ion_chamber in ion_chambers.items():
            self.driver.ion_chambers[ion_chamber["channel"]].set_name(name)

    async def collect_pages(self) -> AsyncGenerator[Mapping[str, Any], Any]:
        assert False

    @AsyncStatus.wrap
    async def calibrate(self, truth: float, dial: float | None = None):
        """Calibrate ion chamber dark current by setting an offset to the .

        Parameters
        ==========
        truth
          The actual energy when the readback is set to *target*.
        dial
          The counts corresponding for when the
          ion chamber should read *truth*.

        """
        coros = [
            ic.calibrate(truth=truth, dial=dial)
            for ic in self.driver.ion_chambers.values()
        ]
        await asyncio.gather(*coros)


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
