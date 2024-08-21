from enum import Enum, IntEnum

from ophyd_async.core import ConfigSignal, DeviceVector, HintedSignal, StandardReadable
from ophyd_async.epics.signal import epics_signal_r, epics_signal_rw, epics_signal_x

from .._iconfig import load_config
from .device import connect_devices
from .instrument_registry import InstrumentRegistry
from .instrument_registry import registry as default_registry


def num_to_char(num):
    char = chr(65 + num)
    return char


class CountMode(str, Enum):
    ONE_SHOT = "OneShot"
    AUTO_COUNT = "N"


class ScalerModel(str, Enum):
    SIS_3801 = "SIS3801"
    SIS_3820 = "SIS3820"


class OutputLED(str, Enum):
    LOW = "Low/Off"
    HIGH = "High/On"


class ChannelAdvanceSource(str, Enum):
    INTERNAL = "Internal"
    EXTERNAL = "External"


class NoYes(str, Enum):
    NO = "No"
    YES = "Yes"


class Channel1Source(str, Enum):
    INTERNAL_CLOCK = "Int. Clock"
    EXTERNAL = "External"


class AcquireMode(str, Enum):
    MCS = "MCS"
    SCALER = "Scaler"


class SNLConnected(str, Enum):
    NOT_CONNECTED = "Not connected"
    CONNECTED = "Connected"


class Polarity(str, Enum):
    NORMAL = "Normal"
    INVERTED = "Inverted"


class OutputMode(str, Enum):
    MODE_0 = "Mode 0"
    MODE_1 = "Mode 1"
    MODE_2 = "Mode 2"
    MODE_3 = "Mode 3"


class InputMode(str, Enum):
    MODE_0 = "Mode 0"
    MODE_1 = "Mode 1"
    MODE_2 = "Mode 2"
    MODE_3 = "Mode 3"
    MODE_4 = "Mode 4"
    MODE_5 = "Mode 5"
    MODE_6 = "Mode 6"


class LNEStretcher(str, Enum):
    DISABLE = "Disable"
    ENABLE = "Enable"


class ScalerChannel(StandardReadable):
    def __init__(self, prefix, channel_num, name=""):
        epics_ch_num = channel_num + 1  # EPICS is 1-indexed
        # Hinted signals
        with self.add_children_as_readables(HintedSignal):
            net_suffix = (
                f"_net{num_to_char((channel_num // 12))}"
                f".{num_to_char(channel_num % 12)}"
            )
            self.net_count = epics_signal_r(int, f"{prefix}{net_suffix}")
        # Regular readable signals
        with self.add_children_as_readables():
            self.raw_count = epics_signal_r(int, f"{prefix}.S{epics_ch_num}")
        # Configuration signals
        with self.add_children_as_readables(ConfigSignal):
            self.description = epics_signal_rw(str, f"{prefix}.NM{epics_ch_num}")
            self.is_gate = epics_signal_rw(str, f"{prefix}.G{epics_ch_num}")
            self.preset_count = epics_signal_rw(str, f"{prefix}.PR{epics_ch_num}")
            offset_suffix = f"_offset{channel_num // 4}.{num_to_char(channel_num % 4)}"
            self.offset_rate = epics_signal_rw(int, f"{prefix}{offset_suffix}")
        super().__init__(name=name)


class MCA(StandardReadable):
    def __init__(self, prefix, name=""):
        # Signals
        with self.add_children_as_readables(HintedSignal):
            self.spectrum = epics_signal_r(int, f"{prefix}.VAL")
        self.background = epics_signal_r(int, f"{prefix}.BG")
        with self.add_children_as_readables(ConfigSignal):
            self.mode = epics_signal_rw(str, f"{prefix}.MODE")
        super().__init__(name=name)


class MultiChannelScaler(StandardReadable):
    """A SIS3820 or MeasComp counter.

    Devices
    =======
    scaler
      The scaler-like device for counting channels once.
    mcas
      The multi-channel analyzers for measuring the channels
      repeatedly.

    """

    _ophyd_labels_ = {"scalers"}

    def __init__(self, prefix, channels: list[int], name=""):
        # Controls
        self.start_all = epics_signal_x(f"{prefix}StartAll")
        self.stop_all = epics_signal_x(f"{prefix}StopAll")
        self.erase_all = epics_signal_x(f"{prefix}EraseAll")
        self.erase_start = epics_signal_x(f"{prefix}EraseStart")
        self.software_channel_advance = epics_signal_x(f"{prefix}SoftwareChannelAdvance")
        # Transient states
        self.acquiring = epics_signal_r(int, f"{prefix}Acquiring")
        self.user_led = epics_signal_rw(OutputLED, f"{prefix}UserLED")
        # Config signals
        with self.add_children_as_readables(ConfigSignal):
            self.preset_time = epics_signal_rw(float, f"{prefix}PresetReal")
            self.dwell_time = epics_signal_rw(float, f"{prefix}Dwell")
            self.prescale = epics_signal_rw(int, f"{prefix}Prescale")
            self.channel_advance_source = epics_signal_rw(
                ChannelAdvanceSource,
                f"{prefix}ChannelAdvance"
            )
            self.count_on_start = epics_signal_rw(NoYes, f"{prefix}CountOnStart")
            self.channel_1_source = epics_signal_rw(Channel1Source, f"{prefix}Channel1Source")
            self.mux_output = epics_signal_rw(int, f"{prefix}MuxOutput")
            self.acquire_mode = epics_signal_rw(AcquireMode, f"{prefix}AcquireMode")
            self.input_mode = epics_signal_rw(InputMode, f"{prefix}InputMode")
            self.input_polarity = epics_signal_rw(Polarity, f"{prefix}InputPolarity")
            self.output_mode = epics_signal_rw(OutputMode, f"{prefix}OutputMode")
            self.output_polarity = epics_signal_rw(Polarity, f"{prefix}OutputPolarity")
            self.lne_output_stretcher = epics_signal_rw(LNEStretcher, f"{prefix}LNEStretcherEnabled")
            self.lne_output_polarity = epics_signal_rw(Polarity, f"{prefix}LNEOutputPolarity")
            self.lne_output_delay = epics_signal_rw(float, f"{prefix}LNEOutputDelay")
            self.lne_output_width = epics_signal_rw(float, f"{prefix}LNEOutputWidth")
            self.num_channels_max = epics_signal_r(int, f"{prefix}MaxChannels")
            self.num_channels = epics_signal_rw(int, f"{prefix}NuseAll")
            self.snl_connected = epics_signal_r(SNLConnected, f"{prefix}SNL_Connected")
            self.model = epics_signal_r(ScalerModel, f"{prefix}Model")
            self.firmware = epics_signal_r(int, f"{prefix}Firmware")
        # Read signals
        with self.add_children_as_readables():
            self.elapsed_time = epics_signal_r(float, f"{prefix}ElapsedReal")
            self.current_channel = epics_signal_r(int, f"{prefix}CurrentChannel")
        # Child-devices
        self.scaler = Scaler(f"{prefix}scaler1", channels=channels)
        with self.add_children_as_readables():
            self.mcas = DeviceVector(
                {i: MCA(f"{prefix}mca{i+1}") for i in channels}
            )
        super().__init__(name=name)


class Scaler(StandardReadable):
    """A scaler device that has one or more ion chambers.

    The individual channels are each an ion chamber. Only those ion
    chambers that have

    """
    def __init__(self, prefix, channels: list[int], name=""):
        # Add invidiaul scaler channels
        with self.add_children_as_readables():
            # Add individual channels
            self.channels = DeviceVector(
                {
                    ch_num: ScalerChannel(f"{prefix}", channel_num=ch_num)
                    for ch_num in channels
                }
            )
        # Scaler-specific signals
        with self.add_children_as_readables():
            self.elapsed_time = epics_signal_r(float, f"{prefix}.T")
        with self.add_children_as_readables(ConfigSignal):
            self.delay = epics_signal_rw(float, f"{prefix}.DLY")
            self.clock_frequency = epics_signal_rw(float, f"{prefix}.FREQ")
            self.count_mode = epics_signal_rw(CountMode, f"{prefix}.CONT")
            self.preset_time = epics_signal_rw(float, f"{prefix}.TP")
        self.count = epics_signal_x(f"{prefix}.CNT")
        self.record_dark_current = epics_signal_x(f"{prefix}_offset_start.PROC")
        self.auto_count_delay = epics_signal_rw(float, f"{prefix}.DLY1")
        self.auto_count_time = epics_signal_rw(float, f"{prefix}.TP1")
        self.dark_current_time = epics_signal_rw(
            float, f"{prefix}_offset_time.VAL"
        )
        super().__init__(name=name)


async def load_scalers(
    config=None, connect=True, registry: InstrumentRegistry = default_registry
):
    """Load counting scaler devices."""
    if config is None:
        config = load_config()
    # Create the scaler devices
    devices = []
    for name, cfg in config.get("scaler", {}).items():
        channels = range(cfg['num_channels'])
        devices.append(MultiChannelScaler(prefix=cfg["prefix"], channels=channels, name=name))
    # Connect to devices
    if connect:
        devices = await connect_devices(
            devices, mock=not config["beamline"]["is_connected"], registry=registry
        )
    return


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
