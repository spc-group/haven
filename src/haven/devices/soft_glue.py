"""Components used to build a soft glue Zynq device.

Softglue is very configurable, so a softglue device that meets all use
cases would be unwieldy.

This module provides reusable components that can be built into
application-specific device definitions.

"""

from collections.abc import Sequence
from enum import IntEnum
from typing import Annotated as A

from ophyd_async.core import (
    DeviceVector,
    SignalR,
    SignalRW,
    StandardReadable,
)
from ophyd_async.core import StandardReadableFormat as Format
from ophyd_async.epics.core import (
    EpicsDevice,
    PvSuffix,
    epics_signal_r,
    epics_signal_rw,
)


class SoftGlueSignal:
    def __init__(self, name: str):
        self._name = name

    def __str__(self):
        return self._name

    def __repr__(self):
        return self._name

    def __invert__(self):
        # Add/remove the trailing '*' for inverted signals
        if self._name.endswith("*"):
            return type(self)(self._name.rstrip("*"))
        else:
            return type(self)(f"{self._name}*")


class LogicGate(StandardReadable, EpicsDevice):
    inputA_signal: A[SignalRW[str], PvSuffix("_IN1_Signal"), Format.CONFIG_SIGNAL]
    inputB_signal: A[SignalRW[str], PvSuffix("_IN2_Signal"), Format.CONFIG_SIGNAL]
    output_signal: A[SignalRW[str], PvSuffix("_OUT_Signal"), Format.CONFIG_SIGNAL]
    inputA_value: A[SignalR[bool], PvSuffix("_IN1_BI")]
    inputB_value: A[SignalR[bool], PvSuffix("_IN2_BI")]
    output_value: A[SignalR[bool], PvSuffix("_OUT_BI")]
    description: A[SignalRW[str], PvSuffix("_desc"), Format.CONFIG_SIGNAL]


class Buffer(StandardReadable, EpicsDevice):
    input_signal: A[SignalRW[str], PvSuffix("_IN_Signal"), Format.CONFIG_SIGNAL]
    output_signal: A[SignalRW[str], PvSuffix("_OUT_Signal"), Format.CONFIG_SIGNAL]
    input_value: A[SignalR[bool], PvSuffix("_IN_BI")]
    output_value: A[SignalR[bool], PvSuffix("_OUT_BI")]
    description: A[SignalRW[str], PvSuffix("_desc"), Format.CONFIG_SIGNAL]


class Latch(StandardReadable, EpicsDevice):
    clock_signal: A[SignalRW[str], PvSuffix("_CLOCK_Signal"), Format.CONFIG_SIGNAL]
    clock_value: A[SignalRW[str], PvSuffix("_CLOCK_BI")]
    set_signal: A[SignalRW[str], PvSuffix("_SET_Signal"), Format.CONFIG_SIGNAL]
    set_value: A[SignalRW[str], PvSuffix("_SET_BI")]
    clear_signal: A[SignalRW[str], PvSuffix("_CLEAR_Signal"), Format.CONFIG_SIGNAL]
    clear_value: A[SignalRW[str], PvSuffix("_CLEAR_BI")]
    data_signal: A[SignalRW[str], PvSuffix("_D_Signal"), Format.CONFIG_SIGNAL]
    data_value: A[SignalRW[str], PvSuffix("_D_BI")]
    output_signal: A[SignalRW[str], PvSuffix("_OUT_Signal"), Format.CONFIG_SIGNAL]
    output_value: A[SignalRW[str], PvSuffix("_OUT_BI")]
    description: A[SignalRW[str], PvSuffix("_desc"), Format.CONFIG_SIGNAL]


class Multiplexer(StandardReadable, EpicsDevice):
    inputA_signal: A[SignalRW[str], PvSuffix("_IN0_Signal"), Format.CONFIG_SIGNAL]
    inputA_value: A[SignalR[bool], PvSuffix("_IN0_BI")]
    inputB_signal: A[SignalRW[str], PvSuffix("_IN1_Signal"), Format.CONFIG_SIGNAL]
    inputB_value: A[SignalR[bool], PvSuffix("_IN1_BI")]
    select_signal: A[SignalRW[str], PvSuffix("_SEL_Signal"), Format.CONFIG_SIGNAL]
    select_value: A[SignalR[bool], PvSuffix("_SEL_BI")]
    output_signal: A[SignalRW[str], PvSuffix("_OUT_Signal"), Format.CONFIG_SIGNAL]
    output_value: A[SignalR[bool], PvSuffix("_OUT_BI")]
    description: A[SignalRW[str], PvSuffix("_desc"), Format.CONFIG_SIGNAL]


class Demultiplexer(StandardReadable, EpicsDevice):
    input_signal: A[SignalRW[str], PvSuffix("_IN_Signal"), Format.CONFIG_SIGNAL]
    input_value: A[SignalR[bool], PvSuffix("_IN_BI")]
    select_signal: A[SignalRW[str], PvSuffix("_SEL_Signal"), Format.CONFIG_SIGNAL]
    select_value: A[SignalR[bool], PvSuffix("_SEL_BI")]
    outputA_signal: A[SignalRW[str], PvSuffix("_OUT0_Signal"), Format.CONFIG_SIGNAL]
    outputA_value: A[SignalR[bool], PvSuffix("_OUT0_BI")]
    outputB_signal: A[SignalRW[str], PvSuffix("_OUT1_Signal"), Format.CONFIG_SIGNAL]
    outputB_value: A[SignalR[bool], PvSuffix("_OUT1_BI")]
    description: A[SignalRW[str], PvSuffix("_desc"), Format.CONFIG_SIGNAL]


class Counter(StandardReadable, EpicsDevice):
    enable_signal: A[SignalRW[str], PvSuffix("_ENABLE_Signal"), Format.CONFIG_SIGNAL]
    enable_value: A[SignalR[bool], PvSuffix("_ENABLE_BI")]
    clock_signal: A[SignalRW[str], PvSuffix("_CLOCK_Signal"), Format.CONFIG_SIGNAL]
    clock_value: A[SignalR[bool], PvSuffix("_CLOCK_BI")]
    description: A[SignalRW[str], PvSuffix("_desc"), Format.CONFIG_SIGNAL]

    class Direction(IntEnum):
        UP = 1
        DOWN = 0
        UP_DOWN = 2

    def __init__(
        self,
        prefix: str,
        direction: Direction,
        name: str = "",
    ):
        if direction in [self.Direction.UP, self.Direction.UP_DOWN]:
            with self.add_children_as_readables(Format.CONFIG_SIGNAL):
                self.clear_signal = epics_signal_rw(str, f"{prefix}_CLEAR_Signal")
            self.clear_value = epics_signal_r(bool, f"{prefix}_CLEAR_BI")
            self.counts = epics_signal_r(int, f"{prefix}_COUNTS")
        if direction in [self.Direction.DOWN, self.Direction.UP_DOWN]:
            with self.add_children_as_readables(Format.CONFIG_SIGNAL):
                self.preset_counts = epics_signal_rw(int, f"{prefix}_PRESET")
                self.output_signal = epics_signal_rw(str, f"{prefix}_OUT_Signal")
                self.load_signal = epics_signal_rw(str, f"{prefix}_LOAD_Signal")
            self.output_value = epics_signal_r(bool, f"{prefix}_OUT_BI")
            self.load_value = epics_signal_r(bool, f"{prefix}_LOAD_BI")
        if direction == self.Direction.UP_DOWN:
            with self.add_children_as_readables(Format.CONFIG_SIGNAL):
                self.direction_signal = epics_signal_rw(str, f"{prefix}_UPDOWN_Signal")
            self.direction_value = epics_signal_r(int, f"{prefix}_UPDOWN_BI")
        super().__init__(prefix=prefix, name=name)


class Divider(StandardReadable, EpicsDevice):
    enable_signal: A[SignalRW[str], PvSuffix("_ENABLE_Signal"), Format.CONFIG_SIGNAL]
    enable_value: A[SignalR[bool], PvSuffix("_ENABLE_BI")]
    clock_signal: A[SignalRW[str], PvSuffix("_CLOCK_Signal"), Format.CONFIG_SIGNAL]
    clock_value: A[SignalR[bool], PvSuffix("_CLOCK_BI")]
    output_signal: A[SignalRW[str], PvSuffix("_OUT_Signal"), Format.CONFIG_SIGNAL]
    output_value: A[SignalR[bool], PvSuffix("_OUT_BI")]
    reset_signal: A[SignalRW[str], PvSuffix("_RESET_Signal"), Format.CONFIG_SIGNAL]
    reset_value: A[SignalR[bool], PvSuffix("_RESET_BI")]
    divisor: A[SignalRW[int], PvSuffix("_N"), Format.CONFIG_SIGNAL]
    description: A[SignalRW[str], PvSuffix("_desc"), Format.CONFIG_SIGNAL]


class QuadratureDecoder(StandardReadable, EpicsDevice):
    inputA_signal: A[SignalRW[str], PvSuffix("_A_Signal"), Format.CONFIG_SIGNAL]
    inputA_value: A[SignalR[bool], PvSuffix("_A_BI")]
    inputB_signal: A[SignalRW[str], PvSuffix("_B_Signal"), Format.CONFIG_SIGNAL]
    inputB_value: A[SignalR[bool], PvSuffix("_B_BI")]
    clock_signal: A[SignalRW[str], PvSuffix("_CLOCK_Signal"), Format.CONFIG_SIGNAL]
    clock_value: A[SignalR[bool], PvSuffix("_CLOCK_BI")]
    miss_clear_signal: A[
        SignalRW[str], PvSuffix("_MISSCLR_Signal"), Format.CONFIG_SIGNAL
    ]
    miss_clear_value: A[SignalR[bool], PvSuffix("_MISSCLR_BI")]
    miss_signal: A[SignalRW[str], PvSuffix("_MISS_Signal"), Format.CONFIG_SIGNAL]
    miss_value: A[SignalR[bool], PvSuffix("_MISS_BI")]
    step_signal: A[SignalRW[str], PvSuffix("_STEP_Signal"), Format.CONFIG_SIGNAL]
    step_value: A[SignalR[bool], PvSuffix("_STEP_BI")]
    direction_signal: A[SignalRW[str], PvSuffix("_DIR_Signal"), Format.CONFIG_SIGNAL]
    direction_value: A[SignalR[bool], PvSuffix("_DIR_BI")]
    description: A[SignalRW[str], PvSuffix("_desc"), Format.CONFIG_SIGNAL]


class GateAndDelayGenerator(StandardReadable, EpicsDevice):
    input_signal: A[SignalRW[str], PvSuffix("_IN_Signal"), Format.CONFIG_SIGNAL]
    input_value: A[SignalR[bool], PvSuffix("_IN_BI")]
    clock_signal: A[SignalRW[str], PvSuffix("_CLK_Signal"), Format.CONFIG_SIGNAL]
    clock_value: A[SignalR[bool], PvSuffix("_CLK_BI")]
    delay: A[SignalRW[int], PvSuffix("_DLY"), Format.CONFIG_SIGNAL]
    width: A[SignalRW[int], PvSuffix("_WIDTH"), Format.CONFIG_SIGNAL]
    output_signal: A[SignalRW[str], PvSuffix("_OUT_Signal"), Format.CONFIG_SIGNAL]
    output_value: A[SignalR[bool], PvSuffix("_OUT_BI")]
    description: A[SignalRW[str], PvSuffix("_desc"), Format.CONFIG_SIGNAL]


class FrequencyCounter(StandardReadable, EpicsDevice):
    input_signal: A[SignalRW[str], PvSuffix("_CLK_Signal"), Format.CONFIG_SIGNAL]
    input_value: A[SignalR[bool], PvSuffix("_CLK_BI")]
    frequency: A[SignalR[int], PvSuffix("_COUNTS")]
    description: A[SignalRW[str], PvSuffix("_desc"), Format.CONFIG_SIGNAL]


class Clock(StandardReadable, EpicsDevice):
    signal: A[SignalRW[str], PvSuffix("_Signal"), Format.CONFIG_SIGNAL]

    def __init__(self, prefix: str, name: str = "", frequency: int | None = None):
        self.frequency = frequency
        super().__init__(prefix=prefix, name=name)


class FieldIO(StandardReadable, EpicsDevice):
    description: A[SignalRW[str], PvSuffix("_Signal.DESC"), Format.CONFIG_SIGNAL]
    signal: A[SignalRW[str], PvSuffix("_Signal"), Format.CONFIG_SIGNAL]
    value: A[SignalR[bool], PvSuffix("_BI")]


class SoftGlueZynq(StandardReadable):
    def __init__(
        self,
        prefix: str,
        *,
        and_gates: Sequence[int] = range(4),
        or_gates: Sequence[int] = range(4),
        xor_gates: Sequence[int] = range(2),
        buffers: Sequence[int] = range(4),
        latches: Sequence[int] = range(4),
        multiplexers: Sequence[int] = range(2),
        demultiplexers: Sequence[int] = range(2),
        up_counters: Sequence[int] = range(4),
        down_counters: Sequence[int] = range(4),
        up_down_counters: Sequence[int] = range(4),
        dividers: Sequence[int] = range(4),
        quadrature_decoders: Sequence[int] = range(2),
        gate_and_delay_generators: Sequence[int] = range(4),
        inputs: Sequence[int] = range(12),
        outputs: Sequence[int] = range(12),
        name="",
    ):
        with self.add_children_as_readables():
            self.and_gates = DeviceVector(
                {i: LogicGate(prefix=f"{prefix}AND-{i+1}") for i in and_gates}
            )
            self.or_gates = DeviceVector(
                {i: LogicGate(prefix=f"{prefix}OR-{i+1}") for i in or_gates}
            )
            self.xor_gates = DeviceVector(
                {i: LogicGate(prefix=f"{prefix}XOR-{i+1}") for i in xor_gates}
            )
            self.buffers = DeviceVector(
                {i: Buffer(prefix=f"{prefix}BUFFER-{i+1}") for i in buffers}
            )
            self.latches = DeviceVector(
                {i: Latch(prefix=f"{prefix}DFF-{i+1}") for i in latches}
            )
            self.multiplexers = DeviceVector(
                {i: Multiplexer(prefix=f"{prefix}MUX2-{i+1}") for i in multiplexers}
            )
            self.demultiplexers = DeviceVector(
                {
                    i: Demultiplexer(prefix=f"{prefix}DEMUX2-{i+1}")
                    for i in demultiplexers
                }
            )
            self.up_counters = DeviceVector(
                {
                    i: Counter(
                        prefix=f"{prefix}UpCntr-{i+1}", direction=Counter.Direction.UP
                    )
                    for i in up_counters
                }
            )
            self.down_counters = DeviceVector(
                {
                    i: Counter(
                        prefix=f"{prefix}DnCntr-{i+1}", direction=Counter.Direction.DOWN
                    )
                    for i in down_counters
                }
            )
            self.dividers = DeviceVector(
                {i: Divider(prefix=f"{prefix}DivByN-{i+1}") for i in dividers}
            )
            self.up_down_counters = DeviceVector(
                {
                    i: Counter(
                        prefix=f"{prefix}UpDnCntr-{i+1}",
                        direction=Counter.Direction.UP_DOWN,
                    )
                    for i in up_down_counters
                }
            )
            self.quadrature_decoders = DeviceVector(
                {
                    i: QuadratureDecoder(prefix=f"{prefix}QuadDec-{i+1}")
                    for i in quadrature_decoders
                }
            )
            self.gate_and_delay_generators = DeviceVector(
                {
                    i: GateAndDelayGenerator(prefix=f"{prefix}GateDly-{i+1}")
                    for i in gate_and_delay_generators
                }
            )
            self.frequency_counter = FrequencyCounter(prefix=f"{prefix}FreqCntr-1")
            self.clock_10MHz = Clock(prefix=f"{prefix}10MHZ_CLOCK", frequency=10e6)
            self.clock_20MHz = Clock(prefix=f"{prefix}20MHZ_CLOCK", frequency=20e6)
            self.clock_50MHz = Clock(prefix=f"{prefix}50MHZ_CLOCK", frequency=50e6)
            self.clock_variable = Clock(prefix=f"{prefix}VAR_CLOCK", frequency=None)
            self.inputs = DeviceVector(
                {i: FieldIO(prefix=f"{prefix}FI{i+1}") for i in inputs}
            )
            self.outputs = DeviceVector(
                {i: FieldIO(prefix=f"{prefix}FO{i+1}") for i in outputs}
            )
        super().__init__(name=name)
