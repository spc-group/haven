from ophyd_async.core import StandardReadable
from ophyd_async.core import StandardReadableFormat as Format
from ophyd_async.epics.core import epics_signal_r, epics_signal_rw, epics_signal_rw_rbv

from haven.devices.synApps import ScanInterval


class PTC10ThermocoupleChannel(StandardReadable):
    """
    SRS PTC10 Tc (thermocouple) module channel
    """

    def __init__(self, prefix: str, *, name: str = ""):
        with self.add_children_as_readables(Format.HINTED_SIGNAL):
            self.temperature = epics_signal_r(float, f"{prefix}temperature")
        with self.add_children_as_readables(Format.CONFIG_SIGNAL):
            self.update_rate = epics_signal_rw(
                ScanInterval, f"{prefix}temperature.SCAN"
            )
            self.sensor = epics_signal_r(str, f"{prefix}sensor_RBV")
            self.description = epics_signal_rw(str, f"{prefix}name_RBV")
        super().__init__(name=name)


class PTC10OutputChannel(StandardReadable):
    """
    SRS PTC10 analog I/O channel
    """

    def __init__(self, prefix: str, *, name: str = ""):
        with self.add_children_as_readables():
            self.voltage = epics_signal_rw_rbv(float, f"{prefix}output")
            self.setpoint = epics_signal_rw_rbv(float, f"{prefix}setPoint")
            self.ramp_temperature = epics_signal_r(float, f"{prefix}rampTemp_RBV")
        with self.add_children_as_readables(Format.CONFIG_SIGNAL):
            self.high_limit = epics_signal_rw_rbv(float, f"{prefix}highLimit")
            self.low_limit = epics_signal_rw_rbv(float, f"{prefix}lowLimit")
            self.io_type = epics_signal_rw_rbv(str, f"{prefix}ioType")
            self.ramp_rate = epics_signal_rw_rbv(float, f"{prefix}rampRate")
            self.pid_enabled = epics_signal_rw(bool, f"{prefix}pid:mode")
            self.pid_mode = epics_signal_rw_rbv(str, f"{prefix}pid:mode")
            self.P = epics_signal_rw_rbv(float, f"{prefix}pid:P")
            self.I = epics_signal_rw_rbv(float, f"{prefix}pid:I")
            self.D = epics_signal_rw_rbv(float, f"{prefix}pid:D")
            self.input_choice = epics_signal_rw_rbv(str, f"{prefix}pid:input")
            self.tune_lag = epics_signal_rw_rbv(float, f"{prefix}tune:lag")
            self.tune_lag_step = epics_signal_rw_rbv(float, f"{prefix}tune:step")
            self.tune_mode = epics_signal_rw_rbv(str, f"{prefix}tune:mode")
            self.tune_type = epics_signal_rw_rbv(str, f"{prefix}tune:type")
        super().__init__(name=name)


class PTC10RTDChannel(StandardReadable):
    """
    SRS PTC10 RTD module channel
    """

    def __init__(self, prefix: str, *, name: str = ""):
        with self.add_children_as_readables(Format.HINTED_SIGNAL):
            self.temperature = epics_signal_r(float, f"{prefix}temperature")
        with self.add_children_as_readables(Format.CONFIG_SIGNAL):
            self.units = epics_signal_r(str, f"{prefix}units_RBV")
            self.sensor = epics_signal_rw_rbv(str, f"{prefix}sensor")
            self.range = epics_signal_rw_rbv(str, f"{prefix}range")
            self.current = epics_signal_rw_rbv(str, f"{prefix}current")
            self.power = epics_signal_rw_rbv(str, f"{prefix}power")
            self.update_rate = epics_signal_rw(
                ScanInterval, f"{prefix}temperature.SCAN"
            )
        super().__init__(name=name)


class PTC10Controller(StandardReadable):
    """An SRS PTC10 that can be used as a (temperature) positioner."""

    def __init__(self, prefix: str, *, name: str = ""):
        # self.done = Component(Signal, value=True, kind="omitted")
        # self.done_value = True

        # for computation of soft `done` signal
        # default +/- 1 degree for "at temperature"
        # self.tolerance = Component(Signal, value=1, kind="config")

        # For logging when temperature is reached after a move.
        # self.report_dmov_changes = Component(Signal, value=True, kind="omitted")
        with self.add_children_as_readables(Format.CONFIG_SIGNAL):
            self.output_enable = epics_signal_rw_rbv(bool, f"{prefix}outputEnable")
        super().__init__(name=name)


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2025, UChicago Argonne, LLC
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
