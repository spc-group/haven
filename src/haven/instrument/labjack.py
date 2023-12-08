from apstools.synApps import EpicsRecordDeviceCommonAll, EpicsRecordInputFields
from ophyd import Device, EpicsSignal
from ophyd import FormattedComponent as FCpt
from strenum import StrEnum


class AnalogInput(EpicsRecordInputFields, EpicsRecordDeviceCommonAll):
    class DiffStates(StrEnum):
        single_ended = "Single-Ended"
        differential = "Differential"

    differential = FCpt(
        EpicsSignal, "{self.base_prefix}Diff{self.ch_num}", kind="config"
    )
    high = FCpt(EpicsSignal, "{self.base_prefix}HOPR{self.ch_num}", kind="config")
    low = FCpt(EpicsSignal, "{self.base_prefix}LOPR{self.ch_num}", kind="config")
    temperature_units = FCpt(
        EpicsSignal,
        "{self.base_prefix}TempUnits{self.ch_num}",
        kind="config",
    )
    resolution = FCpt(
        EpicsSignal, "{self.base_prefix}Resolution{self.ch_num}", kind="config"
    )
    range = FCpt(
        EpicsSignal,
        "{self.base_prefix}Range{self.ch_num}",
        kind="config",
    )
    mode = FCpt(EpicsSignal, "{self.base_prefix}Mode{self.ch_num}", kind="config")
    enable = FCpt(EpicsSignal, "{self.base_prefix}Enable{self.ch_num}")

    @property
    def base_prefix(self):
        return self.prefix.rstrip("0123456789")

    @property
    def ch_num(self):
        return self.prefix[len(self.base_prefix) :]


class LabJackT7(Device):
    """A labjack T7 data acquisition unit (DAQ)."""

    ...


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
