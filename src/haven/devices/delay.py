"""Tools for changing the shape of a trigger pulse, mostly meant for fly scanning.

These devices will be prepared from a bluesky fly scan plan.

"""

import asyncio
from collections.abc import Sequence

from bluesky.protocols import Preparable
from ophyd_async.core import (
    DEFAULT_TIMEOUT,
    AsyncStatus,
    DetectorTrigger,
    SignalDatatypeT,
    SignalRW,
    StandardReadable,
    StandardReadableFormat,
    StrictEnum,
    SubsetEnum,
    TriggerInfo,
)
from ophyd_async.epics.core import epics_signal_r, epics_signal_rw, epics_signal_x, EpicsDevice

from haven.devices import soft_glue
from haven.devices.soft_glue import SoftGlueSignal as SGSig


def epics_signal_io(
    datatype: type[SignalDatatypeT],
    prefix: str,
    name: str = "",
    timeout: float = DEFAULT_TIMEOUT,
) -> SignalRW[SignalDatatypeT]:
    """Create a `SignalRW` backed by 2 EPICS PVs.

    The write PV gets an extra 'O' and the read PV gets an extra 'I'
    added to the prefix.

    Parameters
    ----------
    datatype:
        Check that the PV is of this type
    prefix:
        The PV to read and monitor

    """
    return epics_signal_rw(
        datatype,
        read_pv=f"{prefix}I",
        write_pv=f"{prefix}O",
        name=name,
        timeout=timeout,
    )


class DG645Channel(StandardReadable):
    class Reference(StrictEnum):
        T0 = "T0"
        A = "A"
        B = "B"
        C = "C"
        D = "D"
        E = "E"
        F = "F"
        G = "G"
        H = "H"

    def __init__(self, prefix: str, name: str = ""):
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            self.reference = epics_signal_io(self.Reference, f"{prefix}ReferenceM")
            self.delay = epics_signal_io(float, f"{prefix}DelayA")
        super().__init__(name=name)


class DG645Output(StandardReadable):
    class Polarity(StrictEnum):
        NEG = "NEG"
        POS = "POS"

    def __init__(self, prefix: str, name: str = ""):
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            self.polarity = epics_signal_io(self.Polarity, f"{prefix}OutputPolarityB")
            self.amplitude = epics_signal_io(float, f"{prefix}OutputAmpA")
            self.offset = epics_signal_io(float, f"{prefix}OutputOffsetA")
        self.output_mode_ttl = epics_signal_x(f"{prefix}OutputModeTtlSS.PROC")
        self.output_mode_nim = epics_signal_x(f"{prefix}OutputModeNimSS.PROC")
        super().__init__(name=name)


class DG645DelayOutput(DG645Output):
    def __init__(
        self, prefix: str, name: str = "", channels: Sequence[DG645Channel] = ()
    ):
        """*channels* are the two channels that should be controlled by this output."""
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            self.trigger_prescale = epics_signal_io(int, f"{prefix}TriggerPrescaleL")
            self.trigger_phase = epics_signal_io(int, f"{prefix}TriggerPhaseL")
        self.channels = channels
        super().__init__(prefix=prefix, name=name)

    @AsyncStatus.wrap
    async def prepare(self, value: TriggerInfo):
        """Prepare this output to trigger another device.

        *value* in this case is the trigger info for the other device,
        and this output will be set up to trigger it appropriately.

        """
        aws = [
            self.channels[0].reference.set(self.channels[0].Reference.T0),
            self.channels[0].delay.set(0),
            self.channels[1].reference.set(self.channels[0].Reference.T0),
        ]
        if value.trigger == DetectorTrigger.EDGE_TRIGGER:
            aws.append(self.channels[1].delay.set(1e-5))
        elif value.trigger in [
            DetectorTrigger.CONSTANT_GATE,
            DetectorTrigger.VARIABLE_GATE,
        ]:
            aws.append(self.channels[1].delay.set(value.livetime - value.deadtime))
        await asyncio.gather(*aws)


class DG645Delay(StandardReadable):

    class BaudRate(SubsetEnum):
        B4800 = "4800"
        B9600 = "9600"
        B19200 = "19200"
        B38400 = "38400"
        B57600 = "57600"
        B115200 = "115200"

    class TriggerSource(SubsetEnum):
        INTERNAL = "Internal"
        EXTERNAL_RISING_EDGE = "Ext rising edge"
        EXTERNAL_FALLING_EDGE = "Ext falling edge"
        SINGLE_SHOT_EXTERNAL_RISING_EDGE = "SS ext rise edge"
        SINGLE_SHOT_EXTERNAL_FALLING_EDGE = "SS ext fall edge"
        SINGLE_SHOT = "Single shot"
        LINE = "Line"

    class TriggerInhibit(SubsetEnum):
        OFF = "Off"
        TRIGGERS = "Triggers"
        AB = "AB"
        AB_CD = "AB,CD"
        AB_CD_EF = "AB,CD,EF"
        AB_CD_EF_GH = "AB,CD,EF,GH"

    class BurstConfig(SubsetEnum):
        ALL_CYCLES = "All Cycles"
        FIRST_CYCLE = "1st Cycle"

    def __init__(self, prefix: str, name: str = ""):
        # Conventional signals
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            self.label = epics_signal_rw(str, f"{prefix}Label")
            self.device_id = epics_signal_r(str, f"{prefix}IdentSI")
        self.status = epics_signal_r(str, f"{prefix}StatusSI")
        self.clear_error = epics_signal_x(f"{prefix}StatusClearBO")
        self.goto_remote = epics_signal_x(f"{prefix}GotoRemoteBO")
        self.goto_local = epics_signal_x(f"{prefix}GotoLocalBO")
        self.reset = epics_signal_x(f"{prefix}ResetBO")
        self.status_checking = epics_signal_rw(bool, f"{prefix}StatusCheckingBO")
        self.reset_serial = epics_signal_x(f"{prefix}IfaceSerialResetBO")
        self.serial_state = epics_signal_io(bool, f"{prefix}IfaceSerialStateB")
        self.serial_baud = epics_signal_io(self.BaudRate, f"{prefix}IfaceSerialBaudM")
        self.reset_gpib = epics_signal_x(f"{prefix}IfaceGpibResetBO")
        self.gpib_state = epics_signal_io(bool, f"{prefix}IfaceGpibStateB")
        self.gpib_address = epics_signal_io(int, f"{prefix}IfaceGpibAddrL")
        self.reset_lan = epics_signal_x(f"{prefix}IfaceLanResetBO")
        self.mac_address = epics_signal_r(str, f"{prefix}IfaceMacAddrSI")
        self.lan_state = epics_signal_io(bool, f"{prefix}IfaceLanStateB")
        self.dhcp_state = epics_signal_io(bool, f"{prefix}IfaceDhcpStateB")
        self.autoip_state = epics_signal_io(bool, f"{prefix}IfaceAutoIpStateB")
        self.static_ip_state = epics_signal_io(bool, f"{prefix}IfaceStaticIpStateB")
        self.bare_socket_state = epics_signal_io(bool, f"{prefix}IfaceBareSocketStateB")
        self.telnet_state = epics_signal_io(bool, f"{prefix}IfaceTelnetStateB")
        self.vxi11_state = epics_signal_io(bool, f"{prefix}IfaceVxiStateB")
        self.ip_address = epics_signal_io(str, f"{prefix}IfaceIpAddrS")
        self.network_mask = epics_signal_io(str, f"{prefix}IfaceNetMaskS")
        self.gateway = epics_signal_io(str, f"{prefix}IfaceGatewayS")
        # Individual delay channels
        with self.add_children_as_readables():
            self.channel_A = DG645Channel(f"{prefix}A")
            self.channel_B = DG645Channel(f"{prefix}B")
            self.channel_C = DG645Channel(f"{prefix}C")
            self.channel_D = DG645Channel(f"{prefix}D")
            self.channel_E = DG645Channel(f"{prefix}E")
            self.channel_F = DG645Channel(f"{prefix}F")
            self.channel_G = DG645Channel(f"{prefix}G")
            self.channel_H = DG645Channel(f"{prefix}H")
        # 2-channel delay outputs
        with self.add_children_as_readables():
            self.output_T0 = DG645Output(f"{prefix}T0")
            self.output_AB = DG645DelayOutput(
                f"{prefix}AB", channels=(self.channel_A, self.channel_B)
            )
            self.output_CD = DG645DelayOutput(
                f"{prefix}CD", channels=(self.channel_C, self.channel_D)
            )
            self.output_EF = DG645DelayOutput(
                f"{prefix}EF", channels=(self.channel_E, self.channel_F)
            )
            self.output_GH = DG645DelayOutput(
                f"{prefix}GH", channels=(self.channel_G, self.channel_H)
            )
        # Trigger control
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            self.trigger_source = epics_signal_io(
                self.TriggerSource,
                f"{prefix}TriggerSourceM",
            )
            self.trigger_inhibit = epics_signal_io(
                self.TriggerInhibit, f"{prefix}TriggerInhibitM"
            )
            self.trigger_level = epics_signal_io(float, f"{prefix}TriggerLevelA")
            self.trigger_rate = epics_signal_io(float, f"{prefix}TriggerRateA")
            self.trigger_advanced_mode = epics_signal_io(
                bool, f"{prefix}TriggerAdvancedModeB"
            )
            self.trigger_holdoff = epics_signal_io(float, f"{prefix}TriggerHoldoffA")
            self.trigger_prescale = epics_signal_io(int, f"{prefix}TriggerPrescaleL")
        # Burst settings
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            self.burst_mode = epics_signal_io(bool, f"{prefix}BurstModeB")
            self.burst_count = epics_signal_io(int, f"{prefix}BurstCountL")
            self.burst_config = epics_signal_io(
                self.BurstConfig, f"{prefix}BurstConfigB"
            )
            self.burst_delay = epics_signal_io(float, f"{prefix}BurstDelayA")
            self.burst_period = epics_signal_io(float, f"{prefix}BurstPeriodA")
        super().__init__(name=name)

    @AsyncStatus.wrap
    async def prepare(self, value: TriggerInfo):
        if value.trigger == DetectorTrigger.INTERNAL:
            trigger_source = self.TriggerSource.INTERNAL
        elif value.trigger == DetectorTrigger.EDGE_TRIGGER:
            trigger_source = self.TriggerSource.EXTERNAL_RISING_EDGE
        await self.trigger_source.set(trigger_source)


UNSET = ""
HIGH = "1"
HIGH_NOW = "1!"
INPUT = SGSig("pulseIn")
RESET = SGSig("reset")
GATE_LATCH = SGSig("gateLatch")
TRIGGER_LIMIT_REACHED = SGSig("stopTrig")
BLOCK_TRIGGERS = SGSig("blockTrigs")
OUTPUT_PERMIT = SGSig("outPermit")
CLOCK = SGSig("internClk")
GATE_OUTPUT = SGSig("gateOut")
TRIGGER_OUTPUT = SGSig("trigOut")


class SoftGlueDelayOutput(StandardReadable, Preparable):
    def __init__(self, prefix: str, output_num: int, name: str = ""):
        """*output_num* is the index of the components to use, 0-indexed."""
        self.and_gate = soft_glue.LogicGate(f"{prefix}AND-{output_num+1}")
        self.output = soft_glue.FieldIO(f"{prefix}FO{output_num+1}")
        super().__init__(name=name)

    @AsyncStatus.wrap
    async def prepare(self, trigger_info: TriggerInfo):
        match trigger_info.trigger:
            case DetectorTrigger.EDGE_TRIGGER:
                # External input provides the input uplses
                aws = (
                    self.and_gate.inputB_signal.set(INPUT),
                    self.and_gate.output_signal.set(TRIGGER_OUTPUT),
                    self.output.signal.set(TRIGGER_OUTPUT),
                )
            case DetectorTrigger.CONSTANT_GATE | DetectorTrigger.VARIABLE_GATE:
                aws = (
                    self.and_gate.inputB_signal.set(GATE_LATCH),
                    self.and_gate.output_signal.set(GATE_OUTPUT),
                    self.output.signal.set(GATE_OUTPUT),
                )
            case _:
                raise ValueError(f"Soft glue output cannot provide triggers for {trigger_info.trigger}")
        # Set all the signals concurrently
        await asyncio.gather(
            self.and_gate.inputA_signal.set(OUTPUT_PERMIT),
            *aws,
        )

    @AsyncStatus.wrap
    async def kickoff(self):
        pass

        
    @AsyncStatus.wrap
    async def complete(self):
        pass



class SoftGlueDelay(StandardReadable, Preparable):
    def __init__(self, prefix: str, name="", pulse_input: int=0):
        self.output_permitted_gate = soft_glue.LogicGate(f"{prefix}AND-1")
        self.pulse_counter = soft_glue.Counter(f"{prefix}DnCntr-1", direction=soft_glue.Counter.Direction.DOWN)
        self.reset_buffer = soft_glue.Buffer(f"{prefix}BUFFER-1")
        self.pulse_input = soft_glue.FieldIO(f"{prefix}FI{pulse_input+1}")
        self.trigger_output = soft_glue.FieldIO(f"{prefix}FO1")
        self.gate_latch = soft_glue.Latch(f"{prefix}DFF-1")
        self.stop_trigger_latch = soft_glue.Latch(f"{prefix}DFF-2")
        # Internal triggering mechanism
        self.internal_clock = soft_glue.Clock(prefix=f"{prefix}10MHZ_CLOCK", frequency=10e6)
        self.clock_divider = soft_glue.Divider(prefix=f"{prefix}DivByN-1")
        # Specific output signal chains
        self.pulse_output = soft_glue.FieldIO(prefix=f"{prefix}FO1")
        self.trigger_output = SoftGlueDelayOutput(prefix=prefix, output_num=1)
        self.gate_output = SoftGlueDelayOutput(prefix=prefix, output_num=2)
        super().__init__(name=name)

    @AsyncStatus.wrap        
    async def prepare(self, trigger_info: TriggerInfo):
        aws = (
            # Input/output channels
            self.reset_buffer.description.set("Reset"),
            self.reset_buffer.output_signal.set(RESET),
            self.pulse_output.signal.set(INPUT),
            # Latch for opening any gate signals
            self.gate_latch.description.set("Gate latch"),
            self.gate_latch.data_signal.set(HIGH),
            self.gate_latch.clock_signal.set(INPUT),
            self.gate_latch.clear_signal.set(~RESET),
            self.gate_latch.output_signal.set(GATE_LATCH),
            # Latch for stopping triggers once enough have passed
            self.pulse_counter.description.set("Pulse counter"),
            self.pulse_counter.clock_signal.set(INPUT),
            self.pulse_counter.load_signal.set(RESET),
            self.pulse_counter.output_signal.set(TRIGGER_LIMIT_REACHED),
            self.pulse_counter.preset_counts.set(0),  # Set properly during kickoff()
            self.stop_trigger_latch.description.set("Block extra triggers"),
            self.stop_trigger_latch.data_signal.set(HIGH),
            self.stop_trigger_latch.clock_signal.set(TRIGGER_LIMIT_REACHED),
            self.stop_trigger_latch.clear_signal.set(~RESET),
            self.stop_trigger_latch.output_signal.set(BLOCK_TRIGGERS),
            self.output_permitted_gate.description.set("Output permit"),
            self.output_permitted_gate.inputA_signal.set(~BLOCK_TRIGGERS),
            self.output_permitted_gate.inputB_signal.set(~INPUT),
            self.output_permitted_gate.output_signal.set(OUTPUT_PERMIT),
            # Internal triggering signals that don't interfere with external triggering
            self.internal_clock.signal.set(CLOCK),
            self.clock_divider.clock_signal.set(CLOCK),
            self.clock_divider.enable_signal.set(HIGH),
            self.clock_divider.reset_signal.set(RESET),
        )
        match trigger_info.trigger:
            case DetectorTrigger.INTERNAL:
                # The internal clock provides the input pulses
                aws = (
                    self.pulse_input.signal.set(UNSET),
                    self.clock_divider.output_signal.set(INPUT),
                    *aws,
                )
            case DetectorTrigger.EDGE_TRIGGER:
                # External input provides the input uplses
                aws = (
                    self.pulse_input.signal.set(INPUT),
                    self.clock_divider.output_signal.set(UNSET),
                    *aws,
                )
            case _:
                raise ValueError(f"Soft glue cannot accept trigger type {trigger_info.trigger}")
        await asyncio.gather(*aws)
        # Prepare an iterator for use during kickoff()
        self._number_of_events_iter = iter(
            trigger_info.number_of_events
            if isinstance(trigger_info.number_of_events, list)
            else [trigger_info.number_of_events]
        )
        self._trigger_info = trigger_info

    @AsyncStatus.wrap
    async def kickoff(self):
        if self._trigger_info is None or self._number_of_events_iter is None:
            raise RuntimeError("Prepare must be called before kickoff!")
        try:
            events_to_complete = next(self._number_of_events_iter)
        except StopIteration as err:
            raise RuntimeError(
                f"Kickoff called more than the configured number of "
                f"{self._trigger_info.total_number_of_exposures} iteration(s)!"
            ) from err
        num_pulses = events_to_complete + 1
        await self.pulse_counter.preset_counts.set(num_pulses)
        # Setting the reset buffer triggers the start of pulses
        await self.reset_buffer.input_signal.set(HIGH_NOW)

    @AsyncStatus.wrap
    async def complete(self):
        pass

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
