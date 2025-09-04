"""A personnelle safety system shutter as an ophyd-async device."""

import asyncio
import logging
import warnings
from enum import IntEnum, unique
from typing import Literal, Mapping

from ophyd.utils.errors import ReadOnlyError
from ophyd_async.core import derived_signal_r, soft_signal_rw
from ophyd_async.epics.core import epics_signal_r

from ..positioner import Positioner
from .signal import derived_signal_rw, epics_signal_xval

__all__ = ["PssShutter", "ShutterState"]


log = logging.getLogger(__name__)


@unique
class ShutterState(IntEnum):
    OPEN = 0  # 0b000
    CLOSED = 1  # 0b001
    FAULT = 3  # 0b011
    UNKNOWN = 4  # 0b100


class PssShutter(Positioner):
    """A personnelle safety system shutter.

    Parameters
    ==========
    allow_open
      Determines whether this shutter can be opened. If "auto"
      (default) then the determination will be made based on the hutch
      search state and shutter permit.
    allow_close
      Determines whether this shutter can be opened or shut.

    """

    _ophyd_labels_ = {"shutters"}
    _last_setpoint: int = ShutterState.UNKNOWN

    def __init__(
        self,
        prefix: str,
        name: str,
        hutch_prefix: str,
        *,
        allow_open: bool | Literal["auto"] = "auto",
        allow_close: bool = True,
        labels={"shutters"},
        **kwargs,
    ):
        self._allow_open = allow_open
        self._allow_close = allow_close
        # Actuators for opening/closing the shutter
        self.open_signal = epics_signal_xval(f"{prefix}OpenEPICSC")
        self.close_signal = epics_signal_xval(f"{prefix}CloseEPICSC")
        # Just use convenient values for these since there's no real position
        self.velocity = soft_signal_rw(float, initial_value=0.5)
        self.units = soft_signal_rw(str, initial_value="")
        self.precision = soft_signal_rw(int, initial_value=5)
        # Positioner signals for moving the shutter
        with self.add_children_as_readables():
            self.readback = epics_signal_r(bool, f"{prefix}BeamBlockingM.VAL")
        self.setpoint = derived_signal_rw(
            int,
            derived_from={
                "open_signal": self.open_signal,
                "close_signal": self.close_signal,
            },
            forward=self._actuate_shutter,
            inverse=self._shutter_setpoint,
        )
        # Extra signals for checking open/close permissions
        # C-hutch searched: S25ID-PSS:StaC:SecureM
        # C-hutch APS key: S25ID-PSS:StaC:APSKeyM
        # C-hutch user key: S25ID-PSS:StaC:UserKeyM
        self.hutch_searched = epics_signal_r(bool, f"{hutch_prefix}SecureM")
        self.aps_key = epics_signal_r(bool, f"{hutch_prefix}APSKeyM")
        self.user_key = epics_signal_r(bool, f"{hutch_prefix}UserKeyM")
        self.open_allowed = derived_signal_r(
            self._open_permission,
            searched=self.hutch_searched,
            aps_key=self.aps_key,
            user_key=self.user_key,
        )
        self.close_allowed = derived_signal_r(
            self._close_permission,
            searched=self.hutch_searched,
            aps_key=self.aps_key,
            user_key=self.user_key,
        )
        super().__init__(name=name, **kwargs)

    async def check_permissions(self, value: ShutterState) -> ShutterState:
        """Check that the shutter has the right permissions to reach *value*."""
        # Get current permit values from the PSS system, etc
        async with asyncio.TaskGroup() as tg:
            allow_close = tg.create_task(self.close_allowed.get_value())
            allow_open = tg.create_task(self.open_allowed.get_value())
        # Logic for deciding whether we can open/close the shutter
        if value == ShutterState.CLOSED and not allow_close.result():
            raise ReadOnlyError(
                f"Shutter {self.name} is not permitted to be closed. "
                "Set `allow_close` for this shutter or wait for APS permit."
            )
        if value == ShutterState.OPEN and not allow_open.result():
            raise ReadOnlyError(
                f"Shutter {self.name} is not permitted to be opened "
                "per iconfig.toml. Set `allow_open` for this shutter."
            )
        return value

    def _open_permission(self, searched: bool, aps_key: bool, user_key: bool) -> bool:
        return all([self._allow_open, searched, aps_key, user_key])

    def _close_permission(self, searched: bool, aps_key: bool, user_key: bool) -> bool:
        return all([self._allow_close, searched, aps_key, user_key])

    async def _actuate_shutter(
        self, value: ShutterState, open_signal, close_signal
    ) -> Mapping:
        """Open/close the shutter using derived-from signals."""
        await self.check_permissions(value)
        if value == ShutterState.OPEN:
            items = {open_signal: 1}
        elif value == ShutterState.CLOSED:
            items = {close_signal: 1}
        else:
            raise ValueError(f"Invalid shutter state for {self}")
        return items

    def _shutter_setpoint(self, values: Mapping, open_signal, close_signal) -> int:
        """Determine whether the shutter was last opened or closed."""
        do_open = values[open_signal]
        do_close = values[close_signal]
        if do_open and do_close:
            # Shutter is both opening and closing??
            warnings.warn("Unknown shutter setpoint")
            self._last_setpoint = ShutterState.UNKNOWN
        elif do_open:
            self._last_setpoint = ShutterState.OPEN
        elif do_close:
            self._last_setpoint = ShutterState.CLOSED
        return self._last_setpoint


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
