"""Ophyd device support for a set of XIA PFCU-controlled filters.

A PFCUFilterBank controls a set of 4 filters. Optionally, 2 filters in
a filter bank can be used as a shutter.

"""

from enum import IntEnum
from typing import Sequence
import logging

from ophyd_async.core import StrictEnum, StandardReadable, StandardReadableFormat, DeviceVector, SubsetEnum, SignalR, SignalRW, T
from ophyd_async.epics.core import epics_signal_r, epics_signal_rw

from ophyd import Component as Cpt
from ophyd import DynamicDeviceComponent as DCpt
from ophyd import EpicsSignal, EpicsSignalRO
from ophyd import FormattedComponent as FCpt
from ophyd import PVPositionerIsClose
from ophyd.signal import DerivedSignal

from haven.devices.shutter import ShutterState
from haven.positioner import Positioner
from haven.devices.signal import DerivedSignalBackend, derived_signal_r, derived_signal_rw


log = logging.getLogger(__name__)


class FilterPosition(StrictEnum):
    OUT = "Out"
    IN = "In"
    SHORT_CIRCUIT = "Short Circuit"
    OPEN_CIRCUIT = "Open Circuit"


class Material(SubsetEnum):
    ALUMINUM = "Al"
    MOLYBDENUM = "Mo"
    TITANIUM = "Ti"
    GLASS = "Glass"
    OTHER = "Other"


class PFCUFilter(Positioner):
    """A single filter in a PFCU filter bank.

    E.g. 25idc:pfcu0:filter1_mat
    """
    _ophyd_labels_ = {"filters"}
    def __init__(self, prefix: str, *, name: str = ""):
        with self.add_children_as_readables("config"):
            self.material = epics_signal_rw(Material, f"{prefix}_mat")
            self.thick = epics_signal_rw(str, f"{prefix}_think")
            self.thick_unit = epics_signal_rw(str, f"{prefix}_think.EGU")
            self.notes = epics_signal_rw(str, f"{prefix}_other")
        with self.add_children_as_readables():
            self.readback = epics_signal_r(FilterPosition, f"{prefix}_RBV")
            self.setpoint = epics_signal_rw(FilterPosition, prefix)
        super().__init__(name=name)


shutter_state_map = {
    # (top filter, bottom filter): state
    (ShutterState.OPEN, ShutterState.CLOSED): ShutterState.OPEN,
    (ShutterState.CLOSED, ShutterState.OPEN): ShutterState.CLOSED,
    (ShutterState.OPEN, ShutterState.OPEN): ShutterState.FAULT,
    (ShutterState.CLOSED, ShutterState.CLOSED): ShutterState.FAULT,
}


class PFCUFilterBank(StandardReadable):
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

    def __init__(self, prefix: str, *, name: str = "", num_slots: int = 4, shutters: Sequence[tuple[int, int]] = []):
        self.num_slots = num_slots
        # Positioner signals
        self.setpoint = epics_signal_rw(int, f"{prefix}config")
        self.readback = epics_signal_r(int, f"{prefix}config_RBV")
        # Sort out filters vs shutters
        all_shutters = [v for shutter in shutters for v in shutter]
        filters = [
            idx for idx in range(num_slots) if idx not in all_shutters
        ]
        # Create shutters
        self.shutters = DeviceVector({
            idx: PFCUShutter(prefix=prefix, top_filter=top, bottom_filter=btm, filter_bank=self)
            for idx, (top, btm) in enumerate(shutters)
        })
        # Create filters
        self.filters = DeviceVector({idx: PFCUFilter(prefix=f"{prefix}filter{idx+1}") for idx in filters})
        super().__init__(name=name)

    # readback = Cpt(EpicsSignalRO, "config_RBV", kind="normal")
    # setpoint = Cpt(EpicsSignal, "config", kind="normal")

    # def __new__(cls, prefix: str, name: str, shutters=[], **kwargs):
    #     # Determine which filters to use as filters vs shutters
    #     all_shutters = [v for shutter in shutters for v in shutter]
    #     filters = [
    #         idx for idx in range(1, cls.num_slots + 1) if idx not in all_shutters
    #     ]
    #     # Create device components for filters and shutters
    #     comps = {
    #         "shutters": DCpt(
    #             {
    #                 f"shutter_{idx}": (
    #                     PFCUShutter,
    #                     "",
    #                     {
    #                         "top_filter": top,
    #                         "bottom_filter": bottom,
    #                         "labels": {"shutters"},
    #                     },
    #                 )
    #                 for idx, (top, bottom) in enumerate(shutters)
    #             }
    #         ),
    #         "filters": DCpt(
    #             {
    #                 f"filter{idx}": (
    #                     PFCUFilter,
    #                     f"filter{idx}",
    #                     {"labels": {"filters"}},
    #                 )
    #                 for idx in filters
    #             }
    #         ),
    #     }
    #     # Create any new child class with shutters and filters
    #     new_cls = type(cls.__name__, (PFCUFilterBank,), comps)
    #     return super().__new__(new_cls)

    # def __init__(
    #     self,
    #     prefix: str = "",
    #     *,
    #     name: str,
    #     shutters: Sequence = [],
    #     labels: str = {"filter_banks"},
    #     **kwargs,
    # ):
    #     super().__init__(prefix=prefix, name=name, labels=labels, **kwargs)


# class PFCUShutterBackend(DerivedSignalBackend):
#     def _mask(self, pos):
#         num_filters = 4
#         return 1 << (num_filters - pos)

#     def top_mask(self):
#         return self._mask(self.parent._top_filter)

#     def bottom_mask(self):
#         return self._mask(self.parent._bottom_filter)

#     def forward(self, value):
#         """Convert shutter state to filter bank state."""
#         # Bit masking to set both blades together
#         old_bits = self.derived_from.parent.readback.get(as_string=False)
#         if value == ShutterState.OPEN:
#             open_bits = self.bottom_mask()
#             close_bits = self.top_mask()
#         elif value == ShutterState.CLOSED:
#             close_bits = self.bottom_mask()
#             open_bits = self.top_mask()
#         else:
#             raise ValueError(bin(value))
#         new_bits = (old_bits | open_bits) & (0b1111 - close_bits)
#         return new_bits

#     def inverse(self, value, signal: SignalR):
#         """Convert filter bank state to shutter state."""
#         # Determine which filters are open and closed
#         top_position = int(bool(value & self.top_mask()))
#         bottom_position = int(bool(value & self.bottom_mask()))
#         result = shutter_state_map[(top_position, bottom_position)]
#         return result


# def pfcu_shutter_signal_rw(
#     *,
#     name: str = "",
#     derived_from: Sequence,
# ) -> SignalRW[T]:
#     backend = PFCUShutterBackend(
#         datatype=int,
#         derived_from=derived_from,
#     )
#     signal = SignalRW(backend, name=name)
#     return signal


# def pfcu_shutter_signal_r(
#     *,
#     name: str = "",
#     derived_from: Sequence,
# ) -> SignalR[T]:
#     backend = PFCUShutterBackend(
#         datatype=int,
#         derived_from=derived_from,
#     )
#     signal = SignalR(backend, name=name)
#     return signal


class PFCUShutter(Positioner):
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

    # readback = Cpt(PFCUShutterSignal, derived_from="parent.parent.readback")
    # setpoint = Cpt(PFCUShutterSignal, derived_from="parent.parent.setpoint")

    def __init__(
        self,
        prefix: str,
        *,
        name: str = "",
        top_filter: int,
        bottom_filter: int,
        filter_bank: PFCUFilterBank,
        **kwargs,
    ):
        self._top_filter_idx = top_filter
        self.top_filter = PFCUFilter(prefix=f"{prefix}filter{top_filter+1}")
        self._bottom_filter_idx = bottom_filter
        self.bottom_filter = PFCUFilter(prefix=f"{prefix}filter{bottom_filter+1}")
        # Set up the positioner signals
        parent_signals = {"setpoint": filter_bank.setpoint,
                        "readback": filter_bank.readback}
        self.setpoint = derived_signal_rw(int, derived_from=parent_signals, forward=self.forward, inverse=self.inverse)
        with self.add_children_as_readables():
            self.readback = derived_signal_r(int, derived_from=parent_signals, inverse=self.inverse)
        super().__init__(
            name=name,
            **kwargs,
        )
        # Make the default alias for the readback the name of the
        # shutter itself.
        # self.readback.name = self.name

    async def forward(self, value, setpoint, readback):
        """Convert shutter state to filter bank state."""
        # Bit masking to set both blades together
        old_bits = await readback.get_value()
        if value == ShutterState.OPEN:
            open_bits = self.bottom_mask()
            close_bits = self.top_mask()
        elif value == ShutterState.CLOSED:
            close_bits = self.bottom_mask()
            open_bits = self.top_mask()
        else:
            raise ValueError(bin(value))
        new_bits = (old_bits | open_bits) & (0b1111 - close_bits)
        log.debug(f"{old_bits=:b}, {open_bits=:b}, {close_bits=:b}, {new_bits=:b}")
        return {setpoint: new_bits}

    def inverse(self, values, readback, **kwargs):
        """Convert filter bank state to shutter state."""
        bits = values[readback]
        # Determine which filters are open and closed
        top_position = int(bool(bits & self.top_mask()))
        bottom_position = int(bool(bits & self.bottom_mask()))
        result = shutter_state_map[(top_position, bottom_position)]
        return result

    def _mask(self, pos):
        num_filters = 4
        return 1 << (num_filters - pos - 1)

    def top_mask(self):
        return self._mask(self._top_filter_idx)

    def bottom_mask(self):
        return self._mask(self._bottom_filter_idx)
        



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
