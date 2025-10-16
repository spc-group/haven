"""Tools for changing the shape of a trigger pulse, mostly meant for fly scanning.

These devices will be prepared from a bluesky fly scan plan.

"""

import asyncio

from bluesky.protocols import Preparable
from ophyd_async.core import (
    AsyncStatus,
    DetectorTrigger,
    StandardReadable,
    TriggerInfo,
)

from haven.devices import soft_glue
from haven.devices.soft_glue import SoftGlueSignal as SGSig

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


class SoftGlueTriggerOutput(StandardReadable, Preparable):
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
                raise ValueError(
                    f"Soft glue output cannot provide triggers for {trigger_info.trigger}"
                )
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


class SoftGlueFlyerController(StandardReadable, Preparable):
    def __init__(self, prefix: str, name="", pulse_input: int = 0):
        self.output_permitted_gate = soft_glue.LogicGate(f"{prefix}AND-1")
        self.pulse_counter = soft_glue.Counter(
            f"{prefix}DnCntr-1", direction=soft_glue.Counter.Direction.DOWN
        )
        self.reset_buffer = soft_glue.Buffer(f"{prefix}BUFFER-1")
        self.pulse_input = soft_glue.FieldIO(f"{prefix}FI{pulse_input+1}")
        self.trigger_output = soft_glue.FieldIO(f"{prefix}FO1")
        self.gate_latch = soft_glue.Latch(f"{prefix}DFF-1")
        self.stop_trigger_latch = soft_glue.Latch(f"{prefix}DFF-2")
        # Internal triggering mechanism
        self.internal_clock = soft_glue.Clock(
            prefix=f"{prefix}10MHZ_CLOCK", frequency=10e6
        )
        self.clock_divider = soft_glue.Divider(prefix=f"{prefix}DivByN-1")
        # Specific output signal chains
        self.pulse_output = soft_glue.FieldIO(prefix=f"{prefix}FO1")
        self.trigger_output = SoftGlueTriggerOutput(prefix=prefix, output_num=1)
        self.gate_output = SoftGlueTriggerOutput(prefix=prefix, output_num=2)
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
                raise ValueError(
                    f"Soft glue cannot accept trigger type {trigger_info.trigger}"
                )
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
