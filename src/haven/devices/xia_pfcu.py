"""Ophyd device support for a set of XIA PFCU-controlled filters.

A PFCUFilterBank controls a set of 4 filters. Optionally, 2 filters in
a filter bank can be used as a shutter.

"""

import asyncio
import logging
from collections.abc import Sequence
from enum import IntEnum
from functools import cached_property
from typing import Literal

from ophyd_async.core import (
    CALCULATE_TIMEOUT,
    AsyncStatus,
    CalculatableTimeout,
    DeviceMock,
    DeviceVector,
    MovableLogic,
    SignalR,
    SignalRW,
    StandardMovable,
    StandardReadable,
    StandardReadableFormat,
    StrictEnum,
    SubsetEnum,
    callback_on_mock_put,
    default_mock_class,
    derived_signal_r,
    derived_signal_rw,
    set_mock_value,
)
from ophyd_async.epics.core import epics_signal_r, epics_signal_rw

from haven.devices.shutter import ShutterState

__all__ = ["PFCUFilterBank", "PFCUFilter", "PFCUShutter"]

log = logging.getLogger(__name__)


class ConfigBits(StrictEnum):
    ZERO = "0000"
    ONE = "0001"
    TWO = "0010"
    THREE = "0011"
    FOUR = "0100"
    FIVE = "0101"
    SIX = "0110"
    SEVEN = "0111"
    EIGHT = "1000"
    NINE = "1001"
    TEN = "1010"
    ELEVEN = "1011"
    TWELVE = "1100"
    THIRTEEN = "1101"
    FOURTEEN = "1110"
    FIFTEEN = "1111"


class FilterState(IntEnum):
    OUT = 0  # 0b000
    IN = 1  # 0b001
    FAULT = 3  # 0b011
    UNKNOWN = 4  # 0b100


class Material(SubsetEnum):
    ALUMINUM = "Al"
    MOLYBDENUM = "Mo"
    TITANIUM = "Ti"
    GLASS = "Glass"
    OTHER = "Other"


def filter_state(bits: int, position: int) -> int:
    """Read the state of the filter at *position* out of a set of bits for multiple filters."""
    mask = 1 << position
    return int(bool(bits & mask))


def update_filter_state(bits: int, position: int, new_state: Literal[0, 1]) -> int:
    """Change *bits* so the filter at *position* is in *new_state*.

    Example:

    ```python
    assert update_filter_state(0b0100, position=1, new_state=1) == 0b0110
    ```

    """
    mask = 1 << position
    if new_state == 1:
        new_bits = bits | mask
    else:
        new_bits = bits & ~mask
    return new_bits


class PFCUFilter(
    StandardMovable[FilterState],
    StandardReadable,
):
    """A single filter in a PFCU filter bank.

    E.g. 25idc:pfcu0:filter1_mat

    """

    def __init__(
        self,
        prefix: str,
        position: int,
        filter_bank_readback: SignalR,
        filter_bank_setpoint: SignalRW,
        *,
        name: str = "",
    ):
        self._ophyd_labels_ = {"attenuators"}
        self._position = position
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            self.material = epics_signal_rw(Material, f"{prefix}_mat")
            self.thick = epics_signal_rw(float, f"{prefix}_thick")
            self.thick_unit = epics_signal_rw(str, f"{prefix}_thick.EGU")
            self.notes = epics_signal_rw(str, f"{prefix}_other")
        # We need a second "private" readback to standardize the types
        self.setpoint = derived_signal_rw(
            self.extract_filter_state, self.set_filter, fb_readback=filter_bank_setpoint
        )
        with self.add_children_as_readables():
            self.readback = derived_signal_r(
                self.extract_filter_state,
                fb_readback=filter_bank_readback,
            )
        super().__init__(name=name)

    def extract_filter_state(self, fb_readback: int) -> int:
        return filter_state(fb_readback, position=self._position)

    async def set_filter(self, new_state: int) -> None:
        old_bits = await self.parent.parent.readback.get_value()
        new_bits = update_filter_state(
            old_bits, position=self._position, new_state=(1 if new_state else 0)
        )
        await self.parent.parent.setpoint.set(new_bits)

    @cached_property
    def movable_logic(self) -> MovableLogic:
        return MovableLogic(setpoint=self.setpoint, readback=self.readback)

    @AsyncStatus.wrap
    async def set(
        self,
        new_position: FilterState,
        timeout: CalculatableTimeout = CALCULATE_TIMEOUT,
    ):
        # Watching an single position movable is a bit silly, this
        # method exists to remove to watchable part of the super class
        # method.
        return await super().set(new_position, timeout)


class FilterBankMovableMock(DeviceMock["StandardMovable"]):
    """Mock behaviour that instantly moves readback to setpoint."""

    async def connect(self, device: StandardMovable) -> None:
        """Mock signals to do an instant move on setpoint write."""

        def _instant_move(value):
            set_mock_value(device.raw_readback, value)  # Arrive instantly

        callback_on_mock_put(device.raw_setpoint, _instant_move)

        # Preserve derived signal behavior
        derived_signals = [
            device.setpoint,
            device.readback,
            *[shutter.setpoint for shutter in device.shutters.values()],
            *[shutter.readback for shutter in device.shutters.values()],
            *[shutter.setpoint for shutter in device.filters.values()],
            *[shutter.readback for shutter in device.filters.values()],
        ]
        coros = [sig.connect(mock=False) for sig in derived_signals]
        await asyncio.gather(*coros)


@default_mock_class(FilterBankMovableMock)
class PFCUFilterBank(StandardMovable[ConfigBits], StandardReadable):
    """A XIA PFCU4 bank of four filters and/or shutters.

    Filters are indexed from 0, even though the EPICS support indexes
    from 1.

    Parameters
    ==========
    shutters
      Sets of filter numbers to use as shutters. Each entry in
      *shutters* should be a tuple like (top, bottom) where the first
      filter (top) is open when the filter is set to "out".

    """

    num_slots: int

    def __init__(
        self,
        prefix: str,
        *,
        name: str = "",
        num_slots: int = 4,
        shutters: Sequence[tuple[int, int]] = [],
    ):
        shutter_indexes = [v for shutter in shutters for v in shutter]
        is_in_bounds = [0 < shtr < num_slots for shtr in shutter_indexes]
        if not all(is_in_bounds):
            raise ValueError(
                f"Shutter indices {shutters} for filterbank {name=} must be in the range (0, {num_slots})."
            )
        self.num_slots = num_slots
        # Positioner signals
        with self.add_children_as_readables():
            self.raw_readback = epics_signal_r(ConfigBits, f"{prefix}config_RBV")
            self.readback = derived_signal_r(
                self.enum_to_int, bits_enum=self.raw_readback
            )
        self.raw_setpoint = epics_signal_rw(ConfigBits, f"{prefix}config")
        self.setpoint = derived_signal_rw(
            self.enum_to_int, self.set_enum, bits_enum=self.raw_setpoint
        )
        # Sort out filters vs shutters
        filter_indexes = [idx for idx in range(num_slots) if idx not in shutter_indexes]
        with self.add_children_as_readables():
            # Create shutters
            self.shutters = DeviceVector(
                {
                    idx: PFCUShutter(
                        prefix=prefix,
                        top_filter=top,
                        bottom_filter=btm,
                        filter_bank=self,
                    )
                    for idx, (top, btm) in enumerate(shutters)
                }
            )
            # Create filters
            self.filters = DeviceVector(
                {
                    idx: PFCUFilter(
                        prefix=f"{prefix}filter{idx+1}",
                        position=idx,
                        filter_bank_readback=self.readback,
                        filter_bank_setpoint=self.setpoint,
                    )
                    for idx in filter_indexes
                }
            )
        super().__init__(name=name)

    async def set_enum(self, bits_int: int) -> None:
        msb_first_str = f"{bits_int:0b}".zfill(self.num_slots)
        bits_str = msb_first_str[::-1]
        await self.raw_setpoint.set(bits_str)

    def enum_to_int(self, bits_enum: ConfigBits) -> int:
        lsb_first_str = str(bits_enum)[::-1]
        return int(lsb_first_str, 2)

    @cached_property
    def movable_logic(self) -> MovableLogic:
        return MovableLogic(setpoint=self.setpoint, readback=self.readback)

    @AsyncStatus.wrap
    async def set(
        self, new_position: int, timeout: CalculatableTimeout = CALCULATE_TIMEOUT
    ):
        # Watching an single position movable is a bit silly, this
        # method exists to remove to watchable part of the super class
        # method.
        return await super().set(new_position, timeout)


class PFCUShutter(StandardMovable[ShutterState], StandardReadable):
    """A shutter made of two PFCU4 filters.

    For faster operation, both filters will be moved at the same
    time. That means this shutter must be a sub-component of a
    :py:class:`PFCUFilterBank`.

    Parameters
    ==========
    top_filter
      The index of the filter that is open when the filter is set to
      "out".
    bottom_filter
      The index of the filter that is open when the filter is set to
      "in".
    filter_bank
      The parent filter bank that this shutter is a part of. This
      *filter_bank*'s *setpoint* and *readback* signals will be used
      for actuating both shutter blades together.

    """

    _ophyd_labels_ = {"shutters", "fast_shutters"}

    def __init__(
        self,
        prefix: str,
        *,
        name: str = "",
        top_filter: int,
        bottom_filter: int,
        filter_bank: PFCUFilterBank,
    ):
        self._top_filter_idx = top_filter
        self._bottom_filter_idx = bottom_filter
        with self.add_children_as_readables():
            self.bottom_filter = PFCUFilter(
                prefix=f"{prefix}filter{bottom_filter+1}",
                position=bottom_filter,
                filter_bank_readback=filter_bank.readback,
                filter_bank_setpoint=filter_bank.setpoint,
            )
            self.top_filter = PFCUFilter(
                prefix=f"{prefix}filter{top_filter+1}",
                position=top_filter,
                filter_bank_readback=filter_bank.readback,
                filter_bank_setpoint=filter_bank.setpoint,
            )
        self.bottom_filter._ophyd_labels_.remove("attenuators")
        self.top_filter._ophyd_labels_.remove("attenuators")
        # Set up the positioner signals

        self.setpoint = derived_signal_rw(
            self.state_from_filters, self.set_filters, fb_readback=filter_bank.setpoint
        )
        with self.add_children_as_readables():
            self.readback = derived_signal_r(
                self.state_from_filters,
                fb_readback=filter_bank.readback,
            )
        super().__init__(name=name)

    @cached_property
    def movable_logic(self) -> MovableLogic:
        return MovableLogic(
            setpoint=self.setpoint,
            readback=self.readback,
        )

    @AsyncStatus.wrap
    async def set(
        self,
        new_position: ShutterState,
        timeout: CalculatableTimeout = CALCULATE_TIMEOUT,
    ):
        # Watching an single position movable is a bit silly, this
        # method exists to remove to watchable part of the super class
        # method.
        return await super().set(new_position, timeout)

    async def set_filters(self, new_position: int) -> None:
        if new_position == ShutterState.OPEN:
            top_state, bottom_state = (FilterState.OUT, FilterState.IN)
        else:
            top_state, bottom_state = (FilterState.IN, FilterState.OUT)
        bits = await self.parent.parent.readback.get_value()
        bits = update_filter_state(
            bits, position=self._top_filter_idx, new_state=(1 if top_state else 0)
        )
        bits = update_filter_state(
            bits, position=self._bottom_filter_idx, new_state=(1 if bottom_state else 0)
        )
        await self.parent.parent.setpoint.set(bits)

    def state_from_filters(self, fb_readback: int) -> int:
        """Convert filter bank state to shutter state."""
        top_filter = filter_state(fb_readback, self._top_filter_idx)
        bottom_filter = filter_state(fb_readback, self._bottom_filter_idx)
        # Determine which filters are open and closed
        match top_filter, bottom_filter:
            case FilterState.OUT, FilterState.IN:
                return ShutterState.OPEN.value
            case FilterState.IN, FilterState.OUT:
                return ShutterState.CLOSED.value
            case _:
                return ShutterState.FAULT.value


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2024, UChicago Argonne, LLC
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
