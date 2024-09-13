import enum

from ophyd import Component as Cpt
from ophyd import Device, EpicsSignal, EpicsSignalRO, Kind


class EpicsSignalWithIO(EpicsSignal):
    # An EPICS signal that simply uses the DG-645 convention of
    # 'AO' being the setpoint and 'AI' being the read-back

    def __init__(self, prefix, **kwargs):
        super().__init__(f"{prefix}I", write_pv=f"{prefix}O", **kwargs)


class DG645Channel(Device):
    reference = Cpt(EpicsSignalWithIO, "ReferenceM", kind=Kind.config)
    delay = Cpt(EpicsSignalWithIO, "DelayA", kind=Kind.config)


class DG645Output(Device):
    output_mode_ttl = Cpt(EpicsSignal, "OutputModeTtlSS.PROC", kind=Kind.config)
    output_mode_nim = Cpt(EpicsSignal, "OutputModeNimSS.PROC", kind=Kind.config)
    polarity = Cpt(EpicsSignalWithIO, "OutputPolarityB", kind=Kind.config)
    amplitude = Cpt(EpicsSignalWithIO, "OutputAmpA", kind=Kind.config)
    offset = Cpt(EpicsSignalWithIO, "OutputOffsetA", kind=Kind.config)


class DG645DelayOutput(DG645Output):
    trigger_prescale = Cpt(EpicsSignalWithIO, "TriggerPrescaleL", kind=Kind.config)
    trigger_phase = Cpt(EpicsSignalWithIO, "TriggerPhaseL", kind=Kind.config)


class DG645Delay(Device):
    label = Cpt(EpicsSignal, "Label", kind=Kind.config)
    status = Cpt(EpicsSignalRO, "StatusSI", kind=Kind.omitted)
    clear_error = Cpt(EpicsSignal, "StatusClearBO", kind=Kind.omitted)
    device_id = Cpt(EpicsSignalRO, "IdentSI", kind=Kind.omitted)
    goto_remote = Cpt(EpicsSignal, "GotoRemoteBO", kind=Kind.omitted)
    goto_local = Cpt(EpicsSignal, "GotoLocalBO", kind=Kind.omitted)
    reset = Cpt(EpicsSignal, "ResetBO", kind=Kind.omitted)
    status_checking = Cpt(EpicsSignal, "StatusCheckingBO", kind=Kind.omitted)
    reset_serial = Cpt(EpicsSignal, "IfaceSerialResetBO", kind=Kind.omitted)
    serial_state = Cpt(EpicsSignalWithIO, "IfaceSerialStateB", kind=Kind.omitted)
    serial_baud = Cpt(EpicsSignalWithIO, "IfaceSerialBaudM", kind=Kind.omitted)
    reset_gpib = Cpt(EpicsSignal, "IfaceGpibResetBO", kind=Kind.omitted)
    gpib_state = Cpt(EpicsSignalWithIO, "IfaceGpibStateB", kind=Kind.omitted)
    gpib_address = Cpt(EpicsSignalWithIO, "IfaceGpibAddrL", kind=Kind.omitted)
    reset_lan = Cpt(EpicsSignal, "IfaceLanResetBO", kind=Kind.omitted)
    mac_address = Cpt(EpicsSignalRO, "IfaceMacAddrSI", kind=Kind.omitted)
    lan_state = Cpt(EpicsSignalWithIO, "IfaceLanStateB", kind=Kind.omitted)
    dhcp_state = Cpt(EpicsSignalWithIO, "IfaceDhcpStateB", kind=Kind.omitted)
    autoip_state = Cpt(EpicsSignalWithIO, "IfaceAutoIpStateB", kind=Kind.omitted)
    static_ip_state = Cpt(EpicsSignalWithIO, "IfaceStaticIpStateB", kind=Kind.omitted)
    bare_socket_state = Cpt(
        EpicsSignalWithIO, "IfaceBareSocketStateB", kind=Kind.omitted
    )
    telnet_state = Cpt(EpicsSignalWithIO, "IfaceTelnetStateB", kind=Kind.omitted)
    vxi11_state = Cpt(EpicsSignalWithIO, "IfaceVxiStateB", kind=Kind.omitted)
    ip_address = Cpt(EpicsSignalWithIO, "IfaceIpAddrS", kind=Kind.omitted)
    network_mask = Cpt(EpicsSignalWithIO, "IfaceNetMaskS", kind=Kind.omitted)
    gateway = Cpt(EpicsSignalWithIO, "IfaceGatewayS", kind=Kind.omitted)

    # Individual delay channels
    channel_A = Cpt(DG645Channel, "A")
    channel_B = Cpt(DG645Channel, "B")
    channel_C = Cpt(DG645Channel, "C")
    channel_D = Cpt(DG645Channel, "D")
    channel_E = Cpt(DG645Channel, "E")
    channel_F = Cpt(DG645Channel, "F")
    channel_G = Cpt(DG645Channel, "G")
    channel_H = Cpt(DG645Channel, "H")

    # 2-channel delay outputs
    output_T0 = Cpt(DG645Output, "T0")
    output_AB = Cpt(DG645DelayOutput, "AB")
    output_CD = Cpt(DG645DelayOutput, "CD")
    output_EF = Cpt(DG645DelayOutput, "EF")
    output_GH = Cpt(DG645DelayOutput, "GH")

    # Trigger control
    trigger_source = Cpt(EpicsSignalWithIO, "TriggerSourceM", kind=Kind.config)
    trigger_inhibit = Cpt(EpicsSignalWithIO, "TriggerInhibitM", kind=Kind.config)
    trigger_level = Cpt(EpicsSignalWithIO, "TriggerLevelA", kind=Kind.config)
    trigger_rate = Cpt(EpicsSignalWithIO, "TriggerRateA", kind=Kind.config)
    trigger_advanced_mode = Cpt(
        EpicsSignalWithIO, "TriggerAdvancedModeB", kind=Kind.config
    )
    trigger_holdoff = Cpt(EpicsSignalWithIO, "TriggerHoldoffA", kind=Kind.config)
    trigger_prescale = Cpt(EpicsSignalWithIO, "TriggerPrescaleL", kind=Kind.config)

    # Burst settings
    burst_mode = Cpt(EpicsSignalWithIO, "BurstModeB", kind=Kind.config)
    burst_count = Cpt(EpicsSignalWithIO, "BurstCountL", kind=Kind.config)
    burst_mode = Cpt(EpicsSignalWithIO, "BurstConfigB", kind=Kind.config)
    burst_delay = Cpt(EpicsSignalWithIO, "BurstDelayA", kind=Kind.config)
    burst_period = Cpt(EpicsSignalWithIO, "BurstPeriodA", kind=Kind.config)

    class trigger_sources(enum.IntEnum):
        INTERNAL = 0
        EXT_RISING_EDGE = 1
        EXT_FALLING_EDGE = 2
        SS_EXT_RISE_EDGE = 3
        SS_EXT_FALL_EDGE = 4
        SINGLE_SHOT = 5
        LINE = 6

    class polarities(enum.IntEnum):
        NEGATIVE = 0
        POSITIVE = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stage_sigs[self.trigger_source] = self.trigger_sources.EXT_RISING_EDGE


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
