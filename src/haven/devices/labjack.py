"""LabJack Data Acquisition (DAQ)
+++++++++++++++++++++++++++++++++++++++

Ophyd-async definitions for Labjack T-series data acquisition devices.

Supported devices, all inherit from ``LabJackBase``:

- T4
- T7
- T7Pro
- T8

These devices are **based on EPICS LabJack module R3.0**. The EPICS IOC
database changed significantly from R2 to R3 when the module was
rewritten to use the LJM library.

.. seealso:: https://github.com/epics-modules/LabJack/releases/tag/R3-0

There are definitions for the entire LabJack device, as well as the
various inputs/outputs available on the LabJack T-series.
Individual inputs can be used as part of other devices. Assuming
analog input 5 is connected to a gas flow meter:

.. code:: python

    from ophyd_async.core import StandardReadable
    from haven.instrument import labjack

    class MyBeamline(StandardReadable):
        def __init__(self, prefix: str, name: str = ""):
            self.gas_flow = labjack.AnalogInput("LabJackT7_1:Ai5")
            ...   # Other devices
            super().__init__(name=name)

"""

import asyncio

import numpy as np
from bluesky.protocols import Triggerable
from ophyd_async.core import (
    DEFAULT_TIMEOUT,
    Array1D,
    AsyncStatus,
    DeviceVector,
    StandardReadable,
    StandardReadableFormat,
    StrictEnum,
    SubsetEnum,
    observe_value,
)
from ophyd_async.epics.core import epics_signal_r, epics_signal_rw, epics_signal_x

from .synApps import EpicsRecordInputFields, EpicsRecordOutputFields

__all__ = [
    "AnalogOutput",
    "AnalogInput",
    "DigitalIO",
    "WaveformDigitizer",
    "WaveformGenerator",
    "LabJackBase",
    "LabJackT4",
    "LabJackT7",
    "LabJackT7Pro",
    "LabJackT8",
]

KIND_CONFIG_OR_NORMAL = 3
"""Alternative for ``Kind.config | Kind.normal``."""


class Input(EpicsRecordInputFields):
    """A generic input record.

    Similar to synApps input records but with some changes. The .PROC
    field is used as a trigger. This way, even if the .SCAN field is
    set to passive, the record can still be updated before being read.
    """

    def __init__(self, prefix: str, name: str = ""):
        self.process_record = epics_signal_x(f"{prefix}.PROC")
        super().__init__(prefix=prefix, name=name)


class BinaryInput(Input):

    def __init__(self, prefix: str, name: str = ""):
        with self.add_children_as_readables():
            self.final_value = epics_signal_r(bool, f"{prefix}.VAL")
        self.raw_value = epics_signal_rw(float, f"{prefix}.RVAL")
        super().__init__(prefix=prefix, name=name)


class Output(EpicsRecordOutputFields):
    """A generic output record.

    Intended to be sub-classed into different output types.

    """


class BinaryOutput(Output):
    """A binary input on the labjack."""

    def __init__(self, prefix: str, name: str = ""):
        with self.add_children_as_readables():
            self.desired_value = epics_signal_rw(bool, f"{prefix}.VAL")
        self.raw_value = epics_signal_rw(float, f"{prefix}.RVAL")
        self.readback_value = epics_signal_r(float, f"{prefix}.RBV")
        super().__init__(prefix=prefix, name=name)


class AnalogOutput(Output):
    """An analog output on a labjack device."""

    def __init__(self, prefix: str, name: str = ""):
        with self.add_children_as_readables():
            self.desired_value = epics_signal_rw(float, f"{prefix}.VAL")
        self.raw_value = epics_signal_rw(int, f"{prefix}.RVAL")
        with self.add_children_as_readables(StandardReadableFormat.HINTED_SIGNAL):
            self.readback_value = epics_signal_r(int, f"{prefix}.RBV")
        super().__init__(prefix=prefix, name=name)


class AnalogInput(Input, Triggerable):
    """An analog input on a labjack device.

    It is based on the synApps input record, but with LabJack specific
    signals added.

    """

    class DifferentialMode(StrictEnum):
        SINGLE_ENDED = "Single-Ended"
        DIFFERENTIAL = "Differential"

    class TemperatureUnits(SubsetEnum):
        KELVIN = "K"
        CELSIUS = "C"
        FAHRENHEIT = "F"

    class Mode(SubsetEnum):
        VOLTS = "Volts"
        TYPE_B_TC = "Type B TC"
        TYPE_C_TC = "Type C TC"
        TYPE_E_TC = "Type E TC"
        TYPE_J_TC = "Type J TC"
        TYPE_K_TC = "Type K TC"
        TYPE_N_TC = "Type N TC"
        TYPE_R_TC = "Type R TC"
        TYPE_S_TC = "Type S TC"
        TYPE_T_TC = "Type T TC"

    class Range(SubsetEnum):
        TEN_VOLTS = "+= 10V"
        ONE_VOLT = "+= 1V"
        HUNDRED_MILLIVOLTS = "+= 0.1V"
        TEN_MILLIVOLTS = "+= 0.01V"

    class Resolution(SubsetEnum):
        DEFAULT = "Default"
        ONE = "1"
        TWO = "2"
        THREE = "3"
        FOUR = "4"
        FIVE = "5"
        SIX = "6"
        SEVEN = "7"
        EIGHT = "8"

    def __init__(self, prefix: str, ch_num: int, name: str = ""):
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            self.differential = epics_signal_rw(
                self.DifferentialMode, f"{prefix}AiDiff{ch_num}"
            )
            self.high = epics_signal_rw(float, f"{prefix}AiHOPR{ch_num}")
            self.low = epics_signal_rw(float, f"{prefix}AiLOPR{ch_num}")
            self.temperature_units = epics_signal_rw(
                self.TemperatureUnits, f"{prefix}AiTempUnits{ch_num}"
            )

            self.resolution = epics_signal_rw(
                self.Resolution, f"{prefix}AiResolution{ch_num}"
            )
            self.range = epics_signal_rw(self.Range, f"{prefix}AiRange{ch_num}")
            self.mode = epics_signal_rw(self.Mode, f"{prefix}AiMode{ch_num}")
            self.enable = epics_signal_rw(bool, f"{prefix}AiEnable{ch_num}")
        with self.add_children_as_readables(StandardReadableFormat.HINTED_SIGNAL):
            self.final_value = epics_signal_r(float, f"{prefix}Ai{ch_num}.VAL")
        self.raw_value = epics_signal_rw(int, f"{prefix}Ai{ch_num}.RVAL")
        super().__init__(prefix=f"{prefix}Ai{ch_num}", name=name)

    @AsyncStatus.wrap
    async def trigger(self):
        await self.process_record.trigger()


class DigitalIO(StandardReadable):
    """A digital input/output channel on the labjack.

    Because of the how the records are structured in EPICS, the prefix
    must not include the "Bi{N}" portion of the prefix. Instead, the
    prefix should be prefix for the whole labjack
    (e.g. ``LabJackT7_1:``), and the channel number should be provided
    using the *ch_num* property. So for the digital I/O with its input
    available at PV ``LabJackT7_1:Bi3``, use:

    .. code:: python

        dio3 = DigitalIO("LabJackT7_1:", name="dio3", ch_num=3)

    This will create signals for the input (``Bi3``), output
    (``Bo3``), and direction (``Bd3``) records.

    """

    class Direction(SubsetEnum):
        INPUT = "In"
        OUTPUT = "Out"

    def __init__(self, prefix: str, ch_num: int, name: str = ""):
        with self.add_children_as_readables():
            self.input = BinaryInput(f"{prefix}Bi{ch_num}")
            self.output = BinaryOutput(f"{prefix}Bo{ch_num}")
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            self.direction = epics_signal_rw(self.Direction, f"{prefix}Bd{ch_num}")
        super().__init__(name=name)


class WaveformDigitizer(StandardReadable, Triggerable):
    """A feature of the Labjack devices that allows waveform capture."""

    class TriggerSource(StrictEnum):
        INTERNAL = "Internal"
        EXTERNAL = "External"

    class ReadWaveform(StrictEnum):
        DONE = "Done"
        READ = "Read"

    class FirstChannel(SubsetEnum):
        ONE = "1"
        TWO = "2"
        THREE = "3"
        FOUR = "4"
        FIVE = "5"
        SIX = "6"
        SEVEN = "7"
        EIGHT = "8"
        NINE = "9"
        TEN = "10"
        ELEVEN = "11"
        TWELVE = "12"
        THIRTEEN = "13"

    class NumberOfChannels(SubsetEnum):
        ONE = "1"
        TWO = "2"
        THREE = "3"
        FOUR = "4"
        FIVE = "5"
        SIX = "6"
        SEVEN = "7"
        EIGHT = "8"
        NINE = "9"
        TEN = "10"
        ELEVEN = "11"
        TWELVE = "12"
        THIRTEEN = "13"
        FOURTEEN = "14"

    class Resolution(SubsetEnum):
        DEFAULT = "Default"
        ONE = "1"
        TWO = "2"
        THREE = "3"
        FOUR = "4"
        FIVE = "5"
        SIX = "6"
        SEVEN = "7"
        EIGHT = "8"

    def __init__(self, prefix: str, name: str = "", waveforms=[]):
        with self.add_children_as_readables():
            self.timebase_waveform = epics_signal_rw(
                Array1D[np.float64], f"{prefix}WaveDigTimeWF"
            )
            self.dwell_actual = epics_signal_rw(float, f"{prefix}WaveDigDwellActual")
            self.total_time = epics_signal_rw(float, f"{prefix}WaveDigTotalTime")
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            self.num_points = epics_signal_rw(int, f"{prefix}WaveDigNumPoints")
            self.dwell_time = epics_signal_rw(float, f"{prefix}WaveDigDwell")
            self.first_chan = epics_signal_rw(
                self.FirstChannel, f"{prefix}WaveDigFirstChan"
            )
            self.num_chans = epics_signal_rw(
                self.NumberOfChannels, f"{prefix}WaveDigNumChans"
            )
            self.resolution = epics_signal_rw(
                self.Resolution, f"{prefix}WaveDigResolution"
            )
            self.settling_time = epics_signal_rw(float, f"{prefix}WaveDigSettlingTime")
        self.current_point = epics_signal_rw(int, f"{prefix}WaveDigCurrentPoint")
        self.ext_trigger = epics_signal_rw(
            self.TriggerSource, f"{prefix}WaveDigExtTrigger"
        )
        self.ext_clock = epics_signal_rw(self.TriggerSource, f"{prefix}WaveDigExtClock")
        self.auto_restart = epics_signal_x(f"{prefix}WaveDigAutoRestart")
        self.run = epics_signal_rw(bool, f"{prefix}WaveDigRun")
        self.read_waveform = epics_signal_rw(
            self.ReadWaveform, f"{prefix}WaveDigReadWF"
        )
        # Add waveforms
        with self.add_children_as_readables():
            self.waveforms = DeviceVector(
                {
                    idx: epics_signal_r(
                        Array1D[np.float64], f"{prefix}WaveDigVoltWF{idx}"
                    )
                    for idx in waveforms
                }
            )
        super().__init__(name=name)

    @AsyncStatus.wrap
    async def trigger(self):
        # Determine how long the trigger will take
        dwell_time, num_points = await asyncio.gather(
            self.dwell_time.get_value(),
            self.num_points.get_value(),
        )
        timeout = dwell_time * num_points + DEFAULT_TIMEOUT
        # Start the triggering
        await self.run.set(True, wait=False)
        # Wait for the read to complete
        async for value in observe_value(self.run, timeout=timeout):
            if not value:
                break


class WaveformGenerator(StandardReadable):
    """A feature of the Labjack devices that generates output waveforms."""

    class WaveType(StrictEnum):
        USER_DEFINED = "User-defined"
        SINE_WAVE = "Sin wave"
        SQUARE_WAVE = "Square wave"
        SAWTOOTH = "Sawtooth"
        PULSE = "Pulse"
        RANDOM = "Random"

    TriggerSource = WaveformDigitizer.TriggerSource

    class TriggerMode(StrictEnum):
        ONE_SHOT = "One-shot"
        CONTINUOS = "Continuous"

    def __init__(self, prefix: str, name: str = ""):
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            self.external_trigger = epics_signal_rw(
                self.TriggerSource, f"{prefix}WaveGenExtTrigger"
            )
            self.external_clock = epics_signal_rw(
                self.TriggerSource, f"{prefix}WaveGenExtClock"
            )
            self.continuous = epics_signal_rw(
                self.TriggerMode, f"{prefix}WaveGenContinuous"
            )
        self.run = epics_signal_x(f"{prefix}WaveGenRun")

        # These signals give a readback based on whether user-defined or
        # internal waves are used
        with self.add_children_as_readables():
            self.frequency = epics_signal_r(float, f"{prefix}WaveGenFrequency")
            self.dwell = epics_signal_r(float, f"{prefix}WaveGenDwell")
            self.dwell_actual = epics_signal_r(float, f"{prefix}WaveGenDwellActual")
            self.total_time = epics_signal_r(float, f"{prefix}WaveGenTotalTime")
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            self.num_points = epics_signal_r(int, f"{prefix}WaveGenNumPoints")
        self.current_point = epics_signal_r(int, f"{prefix}WaveGenCurrentPoint")

        # Settings for user-defined waveforms
        with self.add_children_as_readables():
            self.user_time_waveform = epics_signal_rw(
                Array1D[np.float64], f"{prefix}WaveGenUserTimeWF"
            )
        self.user_num_points = epics_signal_rw(int, f"{prefix}WaveGenUserNumPoints")
        self.user_dwell = epics_signal_rw(float, f"{prefix}WaveGenUserDwell")
        self.user_frequency = epics_signal_rw(float, f"{prefix}WaveGenUserFrequency")

        # Settings for internal waveforms
        with self.add_children_as_readables():
            self.internal_time_waveform = epics_signal_rw(
                Array1D[np.float64], f"{prefix}WaveGenIntTimeWF"
            )
        self.internal_num_points = epics_signal_rw(int, f"{prefix}WaveGenIntNumPoints")
        self.internal_dwell = epics_signal_rw(float, f"{prefix}WaveGenIntDwell")
        self.internal_frequency = epics_signal_rw(float, f"{prefix}WaveGenIntFrequency")

        # Waveform specific settings
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            self.user_waveform_0 = epics_signal_rw(
                Array1D[np.float64], f"{prefix}WaveGenUserWF0"
            )
            self.enable_0 = epics_signal_rw(bool, f"{prefix}WaveGenEnable0")
            self.type_0 = epics_signal_rw(self.WaveType, f"{prefix}WaveGenType0")
            self.pulse_width_0 = epics_signal_rw(float, f"{prefix}WaveGenPulseWidth0")
            self.amplitude_0 = epics_signal_rw(float, f"{prefix}WaveGenAmplitude0")
            self.offset_0 = epics_signal_rw(float, f"{prefix}WaveGenOffset0")
            self.user_waveform_1 = epics_signal_rw(
                Array1D[np.float64], f"{prefix}WaveGenUserWF1"
            )
            self.enable_1 = epics_signal_rw(bool, f"{prefix}WaveGenEnable1")
            self.type_1 = epics_signal_rw(self.WaveType, f"{prefix}WaveGenType1")
            self.pulse_width_1 = epics_signal_rw(float, f"{prefix}WaveGenPulseWidth1")
            self.amplitude_1 = epics_signal_rw(float, f"{prefix}WaveGenAmplitude1")
            self.offset_1 = epics_signal_rw(float, f"{prefix}WaveGenOffset1")
        self.internal_waveform_0 = epics_signal_rw(
            Array1D[np.float64], f"{prefix}WaveGenInternalWF0"
        )
        self.internal_waveform_1 = epics_signal_r(
            Array1D[np.float64], f"{prefix}WaveGenInternalWF1"
        )

        super().__init__(name=name)


class LabJackBase(StandardReadable):
    """A labjack T-series data acquisition unit (DAQ).

    To use the individual components separately, consider using the
    corresponding devices in the list below.

    This device contains signals for the following:

    - device information (e.g. firmware version ,etc)
    - analog outputs (:py:class:`~haven.instrument.labjack.AnalogInput`)
    - analog inputs* (:py:class:`~haven.instrument.labjack.AnalogOutput`)
    - digital input/output* (:py:class:`~haven.instrument.labjack.DigitalIO`)
    - waveform digitizer* (:py:class:`~haven.instrument.labjack.WaveformDigitizer`)
    - waveform generator (:py:class:`~haven.instrument.labjack.WaveformGenerator`)

    The number of inputs and digital outputs depends on the specific
    LabJack T-series device being used. Therefore, the base device
    ``LabJackBase`` can create arbitrary configurations of these I/O
    signals. For a specific model, consider using one of the
    subclasses, like ``LabJackT4``.

    The waveform generator and waveform digitizer are included for
    convenience. Reading all the analog/digital inputs and outputs can
    be done by calling the ``.read()`` method. However, it is unlikely
    that the goal is also to trigger the digitizer and generator
    during this read. For this reason, **the digitizer and generator
    are not included as readables**. To read or trigger the digitizer or
    generator, they must be used as separate devices:

    .. code:: python

        lj = LabJackT4(...)

        # Read a waveform from the digitizer
        await lj.waveform_digitizer.trigger()
        await lj.waveform_digitizer.read()

        # Same thing for the waveform generator
        await lj.waveform_generator.trigger()

    """

    Resolution = AnalogInput.Resolution

    class Model(StrictEnum):
        T4 = "T4"
        T7 = "T7"
        T7_PRO = "T7-Pro"
        T8 = "T8"

    def __init__(
        self,
        prefix: str,
        name: str = "",
        analog_inputs=[],
        digital_ios=[],
        analog_outputs=range(2),
        digital_words=["dio", "eio", "fio", "mio", "cio"],
    ):
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            self.model_name = epics_signal_r(self.Model, f"{prefix}ModelName")
            self.firmware_version = epics_signal_r(str, f"{prefix}FirmwareVersion")
            self.serial_number = epics_signal_r(str, f"{prefix}SerialNumber")
            self.device_temperature = epics_signal_r(
                float, f"{prefix}DeviceTemperature"
            )
            self.ljm_version = epics_signal_r(str, f"{prefix}LJMVersion")
            self.driver_version = epics_signal_r(str, f"{prefix}DriverVersion")
            self.last_error_message = epics_signal_r(str, f"{prefix}LastErrorMessage")
            self.poll_sleep_ms = epics_signal_rw(float, f"{prefix}PollSleepMS")
            self.analog_in_settling_time_all = epics_signal_rw(
                float, f"{prefix}AiAllSettlingUS"
            )
            self.analog_in_resolution_all = epics_signal_rw(
                self.Resolution, f"{prefix}AiAllResolution"
            )
            self.analog_in_sampling_rate = epics_signal_rw(
                float,
                write_pv=f"{prefix}AiSamplingRate",
                read_pv=f"{prefix}AiSamplingRate_RBV",
            )
        self.poll_time_ms = epics_signal_r(float, f"{prefix}PollTimeMS")
        self.device_reset = epics_signal_x(f"{prefix}DeviceReset")

        # Common sub-devices (all labjacks have 2 analog outputs)
        # NB: Analog inputs/digital I/Os are on a per-model basis
        with self.add_children_as_readables():
            self.analog_outputs = DeviceVector(
                {idx: AnalogOutput(f"{prefix}Ao{idx}") for idx in analog_outputs}
            )
            self.analog_inputs = DeviceVector(
                {idx: AnalogInput(prefix, ch_num=idx) for idx in analog_inputs}
            )
            # Digital I/O channels
            self.digital_ios = DeviceVector(
                {idx: DigitalIO(prefix, ch_num=idx) for idx in digital_ios}
            )
            for word in digital_words:
                setattr(self, word, epics_signal_r(int, f"{prefix}{word.upper()}In"))
        # Waveform devices (not read by default, should be made readable as needed)
        self.waveform_digitizer = WaveformDigitizer(
            f"{prefix}", waveforms=analog_inputs
        )
        self.waveform_generator = WaveformGenerator(f"{prefix}")

        super().__init__(name=name)


class LabJackT4(LabJackBase):
    # Inherit the docstring from the base class
    # (needed for sphinx auto API)
    __doc__ = LabJackBase.__doc__

    def __init__(
        self,
        prefix: str,
        name: str = "",
        analog_inputs=range(12),
        digital_ios=range(16),
        analog_outputs=range(2),
        **kwargs,
    ):
        super().__init__(
            prefix=prefix,
            name=name,
            analog_inputs=analog_inputs,
            digital_ios=digital_ios,
            analog_outputs=analog_outputs,
            **kwargs,
        )


class LabJackT7(LabJackBase):
    # Inherit the docstring from the base class
    # (needed for sphinx auto API)
    __doc__ = LabJackBase.__doc__

    def __init__(
        self,
        prefix: str,
        name: str = "",
        analog_inputs=range(14),
        digital_ios=range(23),
        analog_outputs=range(2),
        **kwargs,
    ):
        super().__init__(
            prefix=prefix,
            name=name,
            analog_inputs=analog_inputs,
            digital_ios=digital_ios,
            analog_outputs=analog_outputs,
            **kwargs,
        )


class LabJackT7Pro(LabJackBase):
    # Inherit the docstring from the base class
    # (needed for sphinx auto API)
    __doc__ = LabJackBase.__doc__

    def __init__(
        self,
        prefix: str,
        name: str = "",
        analog_inputs=range(14),
        digital_ios=range(23),
        analog_outputs=range(2),
        **kwargs,
    ):
        super().__init__(
            prefix=prefix,
            name=name,
            analog_inputs=analog_inputs,
            digital_ios=digital_ios,
            analog_outputs=analog_outputs,
            **kwargs,
        )


class LabJackT8(LabJackBase):
    # Inherit the docstring from the base class
    # (needed for sphinx auto API)
    __doc__ = LabJackBase.__doc__

    def __init__(
        self,
        prefix: str,
        name: str = "",
        analog_inputs=range(8),
        digital_ios=range(20),
        analog_outputs=range(2),
        **kwargs,
    ):
        super().__init__(
            prefix=prefix,
            name=name,
            analog_inputs=analog_inputs,
            digital_ios=digital_ios,
            analog_outputs=analog_outputs,
            **kwargs,
        )


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
