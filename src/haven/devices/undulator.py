import asyncio
import logging
import math
import warnings
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import IntEnum
from functools import cached_property
from pathlib import Path
from typing import IO
from typing import Annotated as A
from typing import Sequence

import numpy as np
import numpy.typing as npt
import pandas as pd
from ophyd_async.core import (
    DEFAULT_TIMEOUT,
    Array1D,
    DeviceMock,
    FlyableLogic,
    MovableLogic,
    SignalR,
    SignalRW,
    StandardFlyable,
    StandardMovable,
    StandardReadable,
)
from ophyd_async.core import StandardReadableFormat as Format
from ophyd_async.core import (
    StrictEnum,
    SubsetEnum,
    TimeoutCalculator,
    TriggerableCommand,
    callback_on_mock_put,
    default_mock_class,
    derived_signal_r,
    derived_signal_rw,
    observe_value,
    set_and_wait_for_other_value,
    set_mock_value,
    wait_for_value,
)
from ophyd_async.core._utils import (
    CALCULATE_TIMEOUT,
    CalculatableTimeout,
    ConfinedModel,
)
from ophyd_async.epics.core import (
    EpicsDevice,
)
from ophyd_async.epics.core import PvSuffix as PV
from ophyd_async.epics.core import (
    epics_signal_r,
    epics_signal_rw,
    epics_triggerable_command,
)
from pydantic import Field
from scanspec.core import Path as ScanPath

from haven import exceptions

log = logging.getLogger(__name__)


UM_PER_MM = 1000


class SetupFailed(RuntimeError):
    pass


class DoneStatus(IntEnum):
    MOVING = 0
    DONE = 1


class BusyStatus(IntEnum):
    DONE = 0
    BUSY = 1


class MotorDriveStatus(IntEnum):
    NOT_READY = 0
    READY_TO_MOVE = 1


SCAN_SETUP_RETRIES = 3


class TrajectoryMotorInfo(ConfinedModel):
    """Minimal set of information required to fly a motor."""

    positions: Sequence[int | float] = Field(frozen=True)
    """Absolute positions that the motor should hit."""

    times: Sequence[int | float] = Field(frozen=True)
    """Relative times at which the motor should reach each position."""

    timeout: CalculatableTimeout = Field(frozen=True, default=CALCULATE_TIMEOUT)
    """Maximum time for the complete motor move, including run up and run down.
    Defaults to `time_for_move` + run up and run down times + 10s."""


@dataclass
class UndulatorLogic(FlyableLogic[Path, None], MovableLogic[float]):
    setpoint: SignalRW
    readback: SignalR
    deadband: SignalRW
    start_signal: TriggerableCommand
    stop_signal: TriggerableCommand
    undulator: "PlanarUndulator"

    async def stop(self) -> None:
        """Optional hook to add logic on how to stop the motion."""
        await self.stop_signal.trigger()
        # Erase any leftover scanning mode setup
        await asyncio.gather(
            self.undulator.clear_scan_array.set(True),
            self.undulator.scan_mode.set(UndulatorScanMode.NORMAL),
        )

    async def check_move(self, new_position: float) -> None:
        """Optional alidate the move.

        Also checks that the gap deadband is zero, since we can't deal
        with gap deadbands yet

        Should raise an exception if the move is not valid, e.g. if the new
        position is outside soft limits.

        """
        gap_deadband = await self.deadband.get_value()
        if gap_deadband != 0:
            msg = f"This device cannot be set properly if the gap deadband is not zero: {gap_deadband}"
            raise exceptions.InvalidUndulatorDeadband(msg)

    async def calculate_timeout(
        self, old_position: float, new_position: float
    ) -> float | None:
        """Optional hook to calculate valid timeout for a move."""
        return None

    async def move(self, new_position: float, timeout: TimeoutCalculator) -> None:
        """Move the device, waiting for the readback to reach the correct position.

        If a scan-mode has been previously prepared, then this will
        move to the next scan mode position if the new position
        matches the previously set position.

        """
        scan_mode = await self.undulator.scan_mode.get_value()
        is_scanning = scan_mode != UndulatorScanMode.NORMAL
        if not is_scanning:
            await self.setpoint.set(new_position)
            await self.start_signal.trigger()
            await wait_for_value(self.readback, new_position, timeout=timeout())
            return
        next_gap = next(self._gap_iter)
        next_energy = next(self._energy_iter)
        current_index, current_mode = await asyncio.gather(
            self.undulator.scan_current_index.get_value(),
            self.undulator.scan_mode.get_value(),
        )
        is_first_point = current_index == 0 and not getattr(
            self, "scan_has_moved", False
        )
        log.debug(f"Moving to scan point {current_index} ({is_first_point=}).")
        if is_first_point:
            # The scan controls don't actually move the gap to the first position
            # so we have to do it manually
            await self.undulator.scan_mode.set(UndulatorScanMode.NORMAL)
            await self.undulator.gap.set(next_gap, timeout=timeout())
            await self.undulator.scan_mode.set(current_mode)
            self.scan_has_moved = True
            return
        # Use the scanning mode controls
        axis = self.undulator.gap
        target = float(next_gap)
        # Track the gap for completion since the energy precision is
        # not linear
        log.debug(f"Waiting for {axis.readback.name} to move to {target} ({timeout=}).")
        await set_and_wait_for_other_value(
            self.undulator.scan_next_point,
            True,
            axis.readback,
            target,
            timeout=timeout(),
        )

    async def scan_setup_successful(self, timeout):
        gap_ok, energy_ok = await asyncio.gather(
            self.undulator.scan_gap_array_check.get_value(),
            self.undulator.scan_energy_array_check.get_value(),
        )
        if not gap_ok or not energy_ok:
            raise SetupFailed(f"{gap_ok=}, {energy_ok=}")
        # Make sure there are no mismatched arrays
        async for value in observe_value(
            self.undulator.scan_mismatch_count, done_timeout=timeout
        ):
            if value == 0:
                break
        return True

    @asynccontextmanager
    async def prepare_scan_mode(self):
        """Preliminary set up to ensure scanning can be prepared.

        This context manager can be used by concrete sub-classes to
        make sure the undulator controls are in a valid state for
        defining a trajectory.

        """
        await asyncio.gather(
            self.undulator.scan_mode.set(UndulatorScanMode.NORMAL),
            self.undulator.clear_scan_array.set(True),
        )
        async with asyncio.TaskGroup() as tg:
            # Each individual positioner can prepare here
            yield tg
        # Scanning is set up, now get ready for executing the steps
        async with asyncio.TaskGroup() as tg:
            scan_gaps = tg.create_task(self.undulator.scan_gap_array.get_value())
            num_points = tg.create_task(self.undulator.scan_array_length.get_value())
        num_points = int(num_points.result())
        scan_gaps = scan_gaps.result()[:num_points]
        scan_gaps = scan_gaps / UM_PER_MM
        self._gap_iter = iter(scan_gaps)
        await self.undulator.scan_mode.set(UndulatorScanMode.SOFTWARE_RETRIES)


class UndulatorMovable(StandardReadable, StandardMovable[float]):

    def __init__(
        self,
        *,
        prefix: str,
        **kwargs,
    ):
        with self.add_children_as_readables():
            self.readback = epics_signal_rw(float, f"{prefix}M.VAL")
        with self.add_children_as_readables(Format.CONFIG_SIGNAL):
            self.precision = epics_signal_r(int, f"{prefix}M.PREC")
            self.units = epics_signal_r(str, f"{prefix}M.EGU")
        self.setpoint = epics_signal_rw(float, f"{prefix}SetC.VAL")
        super().__init__(**kwargs)

    @cached_property
    def movable_logic(self):
        return UndulatorLogic(
            readback=self.readback,
            setpoint=self.setpoint,
            deadband=self.parent.gap_deadband,
            start_signal=self.parent.start_button,
            stop_signal=self.parent.stop_button,
            undulator=self.parent,
        )


@dataclass
class GapLogic(UndulatorLogic):
    gap_velocity: float = 2.0  # Not measured, just a guess

    async def calculate_timeout(
        self, old_position: float, new_position: float
    ) -> float | None:
        """Optional hook to calculate valid timeout for a move."""
        return abs((new_position - old_position) / self.gap_velocity) + DEFAULT_TIMEOUT


class GapMovable(UndulatorMovable):
    @cached_property
    def movable_logic(self):
        return GapLogic(
            readback=self.readback,
            setpoint=self.setpoint,
            deadband=self.parent.gap_deadband,
            start_signal=self.parent.start_button,
            stop_signal=self.parent.stop_button,
            undulator=self.parent,
        )


@dataclass
class EnergyLogic(UndulatorLogic):
    """Logic for moving and flying the undulator energy.

    This logic has the special ability to navigate the energy <-> gap
    calculations when necessary (e.g. when calculating timeouts).

    """

    offset: SignalRW
    gap_velocity: float = 2.0  # Not measured, just a guess. In mm/s.
    _offset_table: IO | str | Path = ""

    @property
    def offset_table(self):
        if self._offset_table == "":
            raise ValueError(
                "Cannot create an offset table, please provide *offset_table* parameter to constructor."
            )
        else:
            return pd.read_csv(self._offset_table, sep="\t")

    def auto_offset(self, energy: float) -> float:
        """Calculate an offset for a given energy based on a calibration lookup table."""
        xp, fp = self.offset_table.T.to_numpy()
        new_offset = np.interp(energy, xp, fp, right=float("nan"), left=float("nan"))
        if math.isnan(new_offset):
            raise ValueError(f"Refusing to extrapolate ID offset: {energy}")
        return float(new_offset)

    async def on_prepare(self, value: ScanPath) -> None:
        """Move to the start of the fly scan, set it up, and return its context.

        :param value: the per-scan info for this fly scan.
        """
        path = value
        frames = path.consume()
        energies = np.asarray(frames.midpoints[self.setpoint.parent])
        offset = await self.offset.get_value()
        energies_kev = _energy_to_keV(energies, offset=offset)
        exceptions = []
        async with self.prepare_scan_mode() as tg:
            gap_taper = tg.create_task(self.undulator.gap_taper.readback.get_value())
            for _ in range(SCAN_SETUP_RETRIES):
                await self.undulator.scan_array_length.set(len(energies_kev))
                await self.undulator.scan_energy_array.set(energies_kev)
                try:
                    await self.scan_setup_successful(timeout=DEFAULT_TIMEOUT)
                except (SetupFailed, TimeoutError) as exc:
                    exceptions.append(exc)
                    continue
                else:
                    break
            else:
                raise ExceptionGroup(
                    f"Preparing energy scan mode was not successful after {SCAN_SETUP_RETRIES} attempts.",
                    exceptions,
                )
        # Stash the requested ranges so we can check them later
        self._energy_iter = iter(energies)
        # The energy->gap calcuations in the IOC don't work right with a taper
        if gap_taper.result() != 0:
            warnings.warn("Setting energy array with non-zero taper.")
        self.scan_has_moved = False
        # Wait for the undulator scan controls to be ready
        await wait_for_value(
            self.undulator.scan_current_index, 0, timeout=DEFAULT_TIMEOUT
        )

    async def on_kickoff(self, ctx: None) -> None:
        """Start the fly scan.

        :param ctx: the context returned by `on_prepare`.

        Return the (possibly updated) context to be passed to `on_complete`.
        """

    async def on_complete(self, ctx: None) -> None:
        """Block until the fly scan is done.

        :param ctx: the context returned by `on_kickoff`.
        """

    async def calculate_timeout(
        self, old_position: float, new_position: float
    ) -> float | None:
        """Estimate how long it will take to move to the given energy.

        This is not a simple calculation because we need to know how
        far the gap will need to move. So instead of the doing the
        calculation, we just set the positioner setpoint and see where
        the gap will go, even though we won't move it.

        """
        gap = self.setpoint.parent.parent.gap
        current_gap_setpoint, current_gap_readback, current_energy_setpoint = (
            await asyncio.gather(
                gap.setpoint.get_value(),
                gap.readback.get_value(),
                self.setpoint.get_value(),
            )
        )
        try:
            await self.setpoint.set(new_position)
            new_gap = await gap.setpoint.get_value()
            move_time = abs(new_gap - current_gap_readback) / self.gap_velocity
        finally:
            # Go back to where we started
            await asyncio.gather(
                self.setpoint.set(current_energy_setpoint),
                gap.setpoint.set(current_gap_setpoint),
            )
        return move_time + DEFAULT_TIMEOUT

        return None


class EnergyMovableMock(DeviceMock["EnergyMovable"]):
    """Mock behaviour that instantly moves readback to setpoint."""

    async def connect(self, device: "EnergyMovable") -> None:
        """Mock signals to do an instant move on setpoint write."""

        def _instant_move(value):
            offset = 0  # To-do figure out how to read the offset PV without await
            set_mock_value(
                device.dial_readback, (value - offset) / 1000
            )  # Arrive instantly

        callback_on_mock_put(device.movable_logic.setpoint, _instant_move)


@default_mock_class(EnergyMovableMock)
class EnergyMovable(StandardReadable, StandardFlyable, StandardMovable[float]):
    def __init__(
        self,
        *,
        prefix: str,
        offset_pv: str,
        **kwargs,
    ):
        with self.add_children_as_readables():
            self.dial_readback = epics_signal_rw(float, f"{prefix}M.VAL")
        with self.add_children_as_readables(Format.CONFIG_SIGNAL):
            self.units = epics_signal_r(str, f"{prefix}SetC.EGU")
            self.dial_precision = epics_signal_r(int, f"{prefix}M.PREC")
            self.precision = derived_signal_r(
                _keV_to_energy_precision,
                keV_precision=self.dial_precision,
            )

        self.dial_setpoint = epics_signal_rw(float, f"{prefix}SetC.VAL")
        # Derived signals so we can apply offsets and convert units
        with self.add_children_as_readables(Format.CONFIG_SIGNAL):
            self.offset = epics_signal_rw(float, offset_pv)
        with self.add_children_as_readables(Format.HINTED_SIGNAL):
            self.readback = derived_signal_r(
                _keV_to_energy,
                keV=self.dial_readback,
                offset=self.offset,
                derived_units="eV",
            )
        self.setpoint = derived_signal_rw(
            _keV_to_energy, self._set_raw, keV=self.dial_setpoint, offset=self.offset
        )
        super().__init__(**kwargs)

    @cached_property
    def _movable_flyable_logic(self):
        return EnergyLogic(
            readback=self.readback,
            setpoint=self.setpoint,
            deadband=self.parent.gap_deadband,
            start_signal=self.parent.start_button,
            stop_signal=self.parent.stop_button,
            offset=self.offset,
            undulator=self.parent,
        )

    @property
    def movable_logic(self):
        return self._movable_flyable_logic

    @property
    def flyable_logic(self):
        return self._movable_flyable_logic

    async def _set_raw(self, value: float):
        """Set the dial value based on the user setpoint, converting units and
        applying offsets.

        """
        offset = await self.offset.get_value()
        raw = _energy_to_keV(value, offset=offset)
        await self.dial_setpoint.set(raw)


def _keV_to_energy(keV: float, offset: float) -> float:
    energy = keV * 1000 - offset
    return energy


def _keV_to_energy_precision(keV_precision: int) -> int:
    return keV_precision - 3


def _energy_to_keV[T: (float, npt.NDArray)](energy: T, offset: T) -> T:
    return (energy + offset) / 1000.0


class UndulatorScanMode(StrictEnum):
    NORMAL = "NormalMode"
    INTERNAL = "ScanMode1"
    EDGE_TRIGGER = "ScanMode2"
    SOFTWARE = "ScanMode3"
    SOFTWARE_RETRIES = "ScanMode4"


class PlanarUndulator(StandardReadable, EpicsDevice):
    """APS Planar Undulator

    .. index:: Ophyd Device; PlanarUndulator

    The signals *busy* and *done* convey complementary
    information. *busy* comes from the IOC, while *done* comes
    directly from the controller.

    EXAMPLE::

        undulator = PlanarUndulator("S25ID:USID:", name="undulator")

    Parameters
    ==========
    prefix
      The IOC prefix for this undulator, e.g. `"S255ID:"`.
    offset_pv
      PV for keeping track of the offset between ID and mono. At
      25-ID-C this lives on the mono IOC.
    name
      The device name used for generating data keys
    offset_table
      File containing a table between ID energy and offset to apply.
    minimum_move: float | int = 0
      Energy moves smaller than this value (in eV) will not actually
      move the undulator. This can solve issues where the undulator is
      not able to make small-enough steps.

    """

    _ophyd_labels_ = {"xray_sources", "undulators"}

    gap_device_setpoint: A[SignalRW[float], PV("GapSetDeviceC")]

    # Signals for ID scanning mode
    scan_array_length: A[SignalRW[float], PV("GapArrayLenC"), Format.CONFIG_SIGNAL]
    clear_scan_array: A[SignalRW[float], PV("GapArraySetClearC")]
    scan_mode: A[SignalRW[UndulatorScanMode], PV("GapScanModeSetC")]
    scan_next_point: A[SignalRW[bool], PV("MoveToNextGapC")]
    scan_energy_array: A[SignalRW[Array1D[np.float64]], PV("EnergyArraySetC.VAL")]
    scan_gap_array: A[SignalRW[Array1D[np.int32]], PV("GapArraySetC")]
    scan_mismatch_count: A[SignalRW[int], PV("MismatchCountM")]
    scan_gap_array_check: A[SignalRW[bool], PV("GapArrayCheckM")]
    scan_energy_array_check: A[SignalRW[bool], PV("EnergyArrayCheckM")]
    scan_current_index: A[SignalR[int], PV("ScanIndexM")]

    class AccessMode(SubsetEnum):
        USER = "User"
        OPERATOR = "Operator"
        MACHINE_PHYSICS = "Machine Physics"
        SYSTEM_MANAGER = "System Manager"

    def __init__(
        self,
        prefix: str,
        offset_pv: str,
        name: str = "",
        offset_table: IO | str | Path = "",
        minimum_move: float | int = 0,
    ):
        self._offset_table = offset_table
        # Signals for moving the undulator
        self.start_button = epics_triggerable_command(f"{prefix}StartC.VAL")
        self.stop_button = epics_triggerable_command(f"{prefix}StopC.VAL")
        self.busy = epics_signal_r(bool, f"{prefix}BusyM.VAL")
        self.done = epics_signal_r(bool, f"{prefix}BusyDeviceM.VAL")
        self.motor_drive_status = epics_signal_r(int, f"{prefix}MotorDriveStatusM.VAL")
        # Configuration state for the undulator
        with self.add_children_as_readables():
            self.total_power = epics_signal_r(float, f"{prefix}TotalPowerM.VAL")
        with self.add_children_as_readables(Format.CONFIG_SIGNAL):
            self.harmonic_value = epics_signal_rw(int, f"{prefix}HarmonicValueC")
            self.gap_deadband = epics_signal_rw(int, f"{prefix}DeadbandGapC")
            self.device_limit = epics_signal_rw(float, f"{prefix}DeviceLimitM.VAL")
            self.device = epics_signal_r(str, f"{prefix}DeviceM")
            self.magnet = epics_signal_r(str, f"{prefix}DeviceMagnetM")
            self.location = epics_signal_r(str, f"{prefix}LocationM")
            self.version_plc = epics_signal_r(float, f"{prefix}PLCVersionM.VAL")
            self.version_hpmu = epics_signal_r(str, f"{prefix}HPMUVersionM.VAL")
        # X-ray spectrum positioners
        with self.add_children_as_readables():
            self.energy = EnergyMovable(
                prefix=f"{prefix}Energy",
                offset_pv=offset_pv,
            )
            self.energy_taper = UndulatorMovable(
                prefix=f"{prefix}TaperEnergy",
            )
            self.gap = GapMovable(
                prefix=f"{prefix}Gap",
            )
            self.gap_taper = UndulatorMovable(
                prefix=f"{prefix}TaperGap",
            )
        # Miscellaneous control signals
        self.access_mode = epics_signal_r(self.AccessMode, f"{prefix}AccessSecurityC")
        self.message1 = epics_signal_r(str, f"{prefix}Message1M.VAL")
        self.message2 = epics_signal_r(str, f"{prefix}Message2M.VAL")
        super().__init__(prefix=prefix, name=name)


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
