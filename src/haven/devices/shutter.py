"""A personnelle safety system (PSS) shutter as an ophyd-async
device.

"""

import asyncio
import logging
from dataclasses import dataclass
from enum import IntEnum, unique
from functools import cached_property

from ophyd.utils.errors import ReadOnlyError
from ophyd_async.core import (
    DeviceMock,
    MovableLogic,
    SignalR,
    SignalRW,
    StandardMovable,
    StandardReadable,
    TimeoutCalculator,
    callback_on_mock_put,
    default_mock_class,
    set_and_wait_for_other_value,
    set_mock_value,
)
from ophyd_async.epics.core import epics_signal_r, epics_signal_rw

__all__ = ["PssShutter", "ShutterState"]


log = logging.getLogger(__name__)


@unique
class ShutterState(IntEnum):
    OPEN = 0  # 0b000
    CLOSED = 1  # 0b001
    FAULT = 3  # 0b011
    UNKNOWN = 4  # 0b100


@dataclass
class ShutterMovableLogic:
    """Determines if the shutter can be opened/closed based on various permission signals."""

    allow_open: bool
    allow_close: bool
    readback: SignalR[ShutterState]
    open: SignalRW[bool]
    close: SignalRW[bool]
    hutch_search: SignalR[bool]
    aps_key: SignalR[bool]
    user_key: SignalR[bool]

    async def stop(self) -> None:
        """Optional hook to add logic on how to stop the motion."""
        pass

    async def check_move(self, new_position: ShutterState) -> None:
        """Optional hook to validate the move.

        Should raise an exception if the move is not valid, e.g. if the new
        position is outside soft limits.
        """
        if new_position not in (ShutterState.OPEN, ShutterState.CLOSED):
            raise ValueError(new_position)
        if new_position == ShutterState.OPEN and not (await self.open_allowed()):
            raise ReadOnlyError(
                f"Shutter {self.readback.parent.name} is not permitted to be opened. "
                "Set `allow_open` for this shutter or wait for APS permit."
            )
        if new_position == ShutterState.CLOSED and not (await self.close_allowed()):
            raise ReadOnlyError(
                f"Shutter {self.readback.parent.name} is not permitted to be closed. "
                "Set `allow_close` for this shutter."
            )

    async def open_allowed(self) -> bool:
        searched, aps_key, user_key = await asyncio.gather(
            self.hutch_search.get_value(),
            self.aps_key.get_value(),
            self.user_key.get_value(),
        )
        print(all([searched, aps_key, user_key]))
        return all([searched, aps_key, user_key, self.allow_open])

    async def close_allowed(self) -> bool:
        return self.allow_close

    async def calculate_timeout(
        self, old_position: ShutterState, new_position: ShutterState
    ) -> float | None:
        """Optional hook to calculate valid timeout for a move."""
        return None

    async def get_units_precision(self) -> tuple[str | None, int | None]:
        """Optional hook to return the units and precision."""
        datakey = (await self.readback.describe())[self.readback.name]
        return datakey.get("units"), datakey.get("precision")

    async def move(
        self, new_position: ShutterState, timeout: TimeoutCalculator
    ) -> None:
        """Move the device, waiting for the readback to reach the correct position.

        ```{note}
        The default implementation waits for the readback to be **exactly**
        equal to `new_position`. For floating-point positions this may never
        be satisfied; override this method to use an appropriate tolerance
        check (e.g. `np.isclose`).
        ```
        """
        if new_position == ShutterState.OPEN:
            actuator = self.open
        elif new_position == ShutterState.CLOSED:
            actuator = self.close
        else:
            actuator = None
        await set_and_wait_for_other_value(
            actuator,
            True,
            self.readback,
            new_position,
            timeout=timeout(),
        )


class ShutterMovableMock(DeviceMock["StandardMovable"]):
    """Mock behaviour that instantly moves readback to setpoint."""

    async def connect(self, device: "StandardMovable") -> None:
        """Mock signals to do an instant move on setpoint write."""

        def _instant_open(value):
            set_mock_value(
                device.movable_logic.readback, ShutterState.OPEN
            )  # Arrive instantly

        def _instant_close(value):
            set_mock_value(
                device.movable_logic.readback, ShutterState.CLOSED
            )  # Arrive instantly

        callback_on_mock_put(device.movable_logic.open, _instant_open)
        callback_on_mock_put(device.movable_logic.close, _instant_close)


@default_mock_class(ShutterMovableMock)
class PssShutter(StandardMovable[ShutterState], StandardReadable):
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
        allow_open: bool = True,
        allow_close: bool = True,
        labels={"shutters"},
        **kwargs,
    ):
        self._allow_open = allow_open
        self._allow_close = allow_close
        # Actuators for opening/closing the shutter
        self.open = epics_signal_rw(bool, f"{prefix}OpenEPICSC")
        self.close = epics_signal_rw(bool, f"{prefix}CloseEPICSC")
        # Positioner signals for moving the shutter
        with self.add_children_as_readables():
            self.readback = epics_signal_r(bool, f"{prefix}BeamBlockingM.VAL")
        # Extra signals for checking open/close permissions
        self.hutch_searched = epics_signal_r(bool, f"{hutch_prefix}SecureM")
        self.aps_key = epics_signal_r(bool, f"{hutch_prefix}APSKeyM")
        self.user_key = epics_signal_r(bool, f"{hutch_prefix}UserKeyM")
        super().__init__(name=name, **kwargs)

    @cached_property
    def movable_logic(self) -> MovableLogic:
        return ShutterMovableLogic(
            readback=self.readback,
            allow_open=self._allow_open,
            allow_close=self._allow_close,
            open=self.open,
            close=self.close,
            hutch_search=self.hutch_searched,
            aps_key=self.aps_key,
            user_key=self.user_key,
        )


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
