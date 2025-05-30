import logging
import math
from enum import IntEnum
from pathlib import Path
from typing import IO

import numpy as np
import pandas as pd
from ophyd_async.core import (
    Signal,
    StandardReadable,
    StandardReadableFormat,
    SubsetEnum,
    derived_signal_r,
    derived_signal_rw,
    soft_signal_rw,
)
from ophyd_async.epics.core import epics_signal_r, epics_signal_rw, epics_signal_x

from ..positioner import Positioner
from .signal import derived_signal_x

log = logging.getLogger(__name__)


class DoneStatus(IntEnum):
    MOVING = 0
    DONE = 1


class BusyStatus(IntEnum):
    DONE = 0
    BUSY = 1


class MotorDriveStatus(IntEnum):
    NOT_READY = 0
    READY_TO_MOVE = 1


class BasePositioner(Positioner):
    done_value: int = BusyStatus.DONE

    def __init__(
        self,
        *,
        prefix: str,
        actuate_signal: Signal,
        stop_signal: Signal,
        done_signal: Signal,
        name: str = "",
    ):
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            self.units = epics_signal_r(str, f"{prefix}SetC.EGU")
            self.precision = epics_signal_r(int, f"{prefix}SetC.PREC")
        self.velocity = soft_signal_rw(
            float, initial_value=1
        )  # Need to figure out what this value is
        # Add control signals that depend on the parent
        if actuate_signal is not None:
            self.actuate = derived_signal_x(
                derived_from={"parent_signal": actuate_signal}
            )
        self.stop_signal = derived_signal_x(derived_from={"parent_signal": stop_signal})
        if done_signal is not None:
            self.done = derived_signal_r(self._done_to_done, done=done_signal)
        super().__init__(name=name)

    @staticmethod
    def _done_to_done(done: bool) -> bool:
        """No-op so we can turn the *done_signal* into a child of this
        device.

        """
        return done


class UndulatorPositioner(BasePositioner):
    def __init__(
        self,
        *,
        prefix: str,
        **kwargs,
    ):
        with self.add_children_as_readables():
            self.readback = epics_signal_rw(float, f"{prefix}M.VAL")
        self.setpoint = epics_signal_rw(float, f"{prefix}SetC.VAL")
        super().__init__(prefix=prefix, **kwargs)


class EnergyPositioner(BasePositioner):
    def __init__(
        self,
        *,
        prefix: str,
        offset_pv: str,
        **kwargs,
    ):

        with self.add_children_as_readables():
            self.dial_readback = epics_signal_rw(float, f"{prefix}M.VAL")
        self.dial_setpoint = epics_signal_rw(float, f"{prefix}SetC.VAL")
        # Derived signals so we can apply offsets and convert units
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            self.offset = epics_signal_rw(float, offset_pv)
        with self.add_children_as_readables():
            self.readback = derived_signal_r(
                _keV_to_energy,
                keV=self.dial_readback,
                offset=self.offset,
                derived_units="eV",
            )
        self.setpoint = derived_signal_rw(
            _keV_to_energy, self._set_raw, keV=self.dial_readback, offset=self.offset
        )
        super().__init__(prefix=prefix, **kwargs)

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


def _energy_to_keV(energy: float, offset: float) -> float:
    return (energy + offset) / 1000


class PlanarUndulator(StandardReadable):
    """APS Planar Undulator

    .. index:: Ophyd Device; PlanarUndulator

    The signals *busy* and *done* convey complementary
    information. *busy* comes from the IOC, while *done* comes
    directly from the controller.

    EXAMPLE::

        undulator = PlanarUndulator("S25ID:USID:", name="undulator")

    """

    _ophyd_labels_ = {"xray_sources", "undulators"}
    _offset_table: IO | str | Path

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
    ):
        self._offset_table = offset_table
        # Signals for moving the undulator
        self.start_button = epics_signal_x(f"{prefix}StartC.VAL")
        self.stop_button = epics_signal_x(f"{prefix}StopC.VAL")
        self.busy = epics_signal_r(bool, f"{prefix}BusyM.VAL")
        self.done = epics_signal_r(bool, f"{prefix}BusyDeviceM.VAL")
        self.motor_drive_status = epics_signal_r(int, f"{prefix}MotorDriveStatusM.VAL")
        # Configuration state for the undulator
        with self.add_children_as_readables():
            self.total_power = epics_signal_r(float, f"{prefix}TotalPowerM.VAL")
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
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
            self.energy = EnergyPositioner(
                prefix=f"{prefix}Energy",
                actuate_signal=self.start_button,
                stop_signal=self.stop_button,
                done_signal=self.busy,
                offset_pv=offset_pv,
            )
            self.energy_taper = UndulatorPositioner(
                prefix=f"{prefix}TaperEnergy",
                actuate_signal=self.start_button,
                stop_signal=self.stop_button,
                done_signal=self.busy,
            )
            self.gap = UndulatorPositioner(
                prefix=f"{prefix}Gap",
                actuate_signal=self.start_button,
                stop_signal=self.stop_button,
                done_signal=self.busy,
            )
            self.gap_taper = UndulatorPositioner(
                prefix=f"{prefix}TaperGap",
                actuate_signal=self.start_button,
                stop_signal=self.stop_button,
                done_signal=self.busy,
            )
        # Miscellaneous control signals
        self.access_mode = epics_signal_r(self.AccessMode, f"{prefix}AccessSecurityC")
        self.message1 = epics_signal_r(str, f"{prefix}Message1M.VAL")
        self.message2 = epics_signal_r(str, f"{prefix}Message2M.VAL")
        super().__init__(name=name)

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
