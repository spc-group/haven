import logging
import warnings
from enum import IntEnum, unique

from ophyd import Component as Cpt
from ophyd import EpicsSignal, EpicsSignalRO
from ophyd.pv_positioner import PVPositionerIsClose
from ophyd.utils.errors import ReadOnlyError
from pcdsdevices.signal import MultiDerivedSignal
from pcdsdevices.type_hints import SignalToValue

# from apstools.devices.shutters import ApsPssShutterWithStatus as Shutter


log = logging.getLogger(__name__)


@unique
class ShutterState(IntEnum):
    OPEN = 0  # 0b000
    CLOSED = 1  # 0b001
    FAULT = 3  # 0b011
    UNKNOWN = 4  # 0b100


class PssShutter(PVPositionerIsClose):
    _last_setpoint: int = ShutterState.UNKNOWN
    allow_open: bool
    allow_close: bool

    def __init__(
        self,
        prefix: str,
        name: str,
        allow_open: bool = True,
        allow_close: bool = True,
        labels={"shutters"},
        **kwargs,
    ):
        self.allow_open = allow_open
        self.allow_close = allow_close
        super().__init__(prefix=prefix, name=name, labels=labels, **kwargs)

    def check_value(self, pos):
        """Check that the shutter has the right permissions."""
        if pos == ShutterState.CLOSED and not self.allow_close:
            raise ReadOnlyError(
                f"Shutter {self.name} is not permitted to be closed. Set `allow_close` for this shutter."
            )
        if pos == ShutterState.OPEN and not self.allow_open:
            raise ReadOnlyError(
                f"Shutter {self.name} is not permitted to be opened per iconfig.toml. Set `allow_open` for this shutter."
            )

    def _actuate_shutter(self, mds: MultiDerivedSignal, value: int) -> SignalToValue:
        """Open/close the shutter using derived-from signals."""
        if value == ShutterState.OPEN:
            items = {self.open_signal: 1}
        elif value == ShutterState.CLOSED:
            items = {self.close_signal: 1}
        else:
            raise ValueError(f"Invalid shutter state for {self}")
        return items

    def _shutter_setpoint(self, mds: MultiDerivedSignal, items: SignalToValue) -> int:
        """Determine whether the shutter was last opened or closed."""
        do_open = items[self.open_signal]
        do_close = items[self.close_signal]
        if do_open and do_close:
            # Shutter is both opening and closing??
            warnings.warn("Unknown shutter setpoint")
            self._last_setpoint = ShutterState.UNKNOWN
        elif do_open:
            self._last_setpoint = ShutterState.OPEN
        elif do_close:
            self._last_setpoint = ShutterState.CLOSED
        return self._last_setpoint

    readback = Cpt(EpicsSignalRO, "BeamBlockingM.VAL")
    setpoint = Cpt(
        MultiDerivedSignal,
        attrs=["open_signal", "close_signal"],
        calculate_on_put=_actuate_shutter,
        calculate_on_get=_shutter_setpoint,
    )
    open_signal = Cpt(EpicsSignal, "OpenEPICSC", kind="omitted")
    close_signal = Cpt(EpicsSignal, "CloseEPICSC", kind="omitted")


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
