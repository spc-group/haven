from typing import Type

from ophyd_async.core import (
    Device,
    T,
    SignalRW,
    StandardReadable,
    ConfigSignal,
    DeviceVector,
)
from ophyd_async.epics.signal import epics_signal_rw, epics_signal_r, epics_signal_x


def epics_signal_io(datatype: Type[T], prefix: str, name: str = "") -> SignalRW[T]:
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
        datatype, read_pv=f"{prefix}I", write_pv=f"{prefix}O", name=name
    )


class DG645Channel(StandardReadable):
    def __init__(self, prefix: str, name: str = ""):
        with self.add_children_as_readables(ConfigSignal):
            self.reference = epics_signal_io(int, f"{prefix}ReferenceM")
            self.delay = epics_signal_io(int, f"{prefix}DelayA")
        super().__init__(name=name)


class DG645Output(StandardReadable):
    def __init__(self, prefix: str, name: str = ""):
        with self.add_children_as_readables(ConfigSignal):
            self.polarity = epics_signal_io(int, f"{prefix}OutputPolarityB")
            self.amplitude = epics_signal_io(int, f"{prefix}OutputAmpA")
            self.offset = epics_signal_io(int, f"{prefix}OutputOffsetA")
        self.output_mode_ttl = epics_signal_x(f"{prefix}OutputModeTtlSS.PROC")
        self.output_mode_nim = epics_signal_x(f"{prefix}OutputModeNimSS.PROC")
        super().__init__(name=name)


class DG645DelayOutput(DG645Output):
    def __init__(self, prefix: str, name: str = ""):
        with self.add_children_as_readables(ConfigSignal):
            self.trigger_prescale = epics_signal_io(int, f"{prefix}TriggerPrescaleL")
            self.trigger_phase = epics_signal_io(int, f"{prefix}TriggerPhaseL")
        super().__init__(prefix=prefix, name=name)


class DG645Delay(StandardReadable):
    def __init__(self, prefix: str, name: str = ""):
        # Conventional signals
        with self.add_children_as_readables(ConfigSignal):
            self.label = epics_signal_rw(str, f"{prefix}Label")
            self.device_id = epics_signal_r(int, f"{prefix}IdentSI")
        self.status = epics_signal_r(int, f"{prefix}StatusSI")
        self.clear_error = epics_signal_rw(int, f"{prefix}StatusClearBO")
        self.goto_remote = epics_signal_rw(int, f"{prefix}GotoRemoteBO")
        self.goto_local = epics_signal_rw(int, f"{prefix}GotoLocalBO")
        self.reset = epics_signal_rw(int, f"{prefix}ResetBO")
        self.status_checking = epics_signal_rw(int, f"{prefix}StatusCheckingBO")
        self.reset_serial = epics_signal_rw(int, f"{prefix}IfaceSerialResetBO")
        self.serial_state = epics_signal_io(int, f"{prefix}IfaceSerialStateB")
        self.serial_baud = epics_signal_io(int, f"{prefix}IfaceSerialBaudM")
        self.reset_gpib = epics_signal_rw(int, f"{prefix}IfaceGpibResetBO")
        self.gpib_state = epics_signal_io(int, f"{prefix}IfaceGpibStateB")
        self.gpib_address = epics_signal_io(int, f"{prefix}IfaceGpibAddrL")
        self.reset_lan = epics_signal_rw(int, f"{prefix}IfaceLanResetBO")
        self.mac_address = epics_signal_r(int, f"{prefix}IfaceMacAddrSI")
        self.lan_state = epics_signal_io(int, f"{prefix}IfaceLanStateB")
        self.dhcp_state = epics_signal_io(int, f"{prefix}IfaceDhcpStateB")
        self.autoip_state = epics_signal_io(int, f"{prefix}IfaceAutoIpStateB")
        self.static_ip_state = epics_signal_io(int, f"{prefix}IfaceStaticIpStateB")
        self.bare_socket_state = epics_signal_io(int, f"{prefix}IfaceBareSocketStateB")
        self.telnet_state = epics_signal_io(int, f"{prefix}IfaceTelnetStateB")
        self.vxi11_state = epics_signal_io(int, f"{prefix}IfaceVxiStateB")
        self.ip_address = epics_signal_io(int, f"{prefix}IfaceIpAddrS")
        self.network_mask = epics_signal_io(int, f"{prefix}IfaceNetMaskS")
        self.gateway = epics_signal_io(int, f"{prefix}IfaceGatewayS")
        # Individual delay channels
        with self.add_children_as_readables():
            self.channels = DeviceVector(
                {
                    "A": DG645Channel(f"{prefix}A"),
                    "B": DG645Channel(f"{prefix}B"),
                    "C": DG645Channel(f"{prefix}C"),
                    "D": DG645Channel(f"{prefix}D"),
                    "E": DG645Channel(f"{prefix}E"),
                    "F": DG645Channel(f"{prefix}F"),
                    "G": DG645Channel(f"{prefix}G"),
                    "H": DG645Channel(f"{prefix}H"),
                }
            )
        # 2-channel delay outputs
        with self.add_children_as_readables():
            self.outputs = DeviceVector(
                {
                    "T0": DG645Output(f"{prefix}T0"),
                    "AB": DG645DelayOutput(f"{prefix}AB"),
                    "CD": DG645DelayOutput(f"{prefix}CD"),
                    "EF": DG645DelayOutput(f"{prefix}EF"),
                    "GH": DG645DelayOutput(f"{prefix}GH"),
                }
            )
        # Trigger control
        with self.add_children_as_readables(ConfigSignal):
            self.trigger_source = epics_signal_io(int, f"{prefix}TriggerSourceM")
            self.trigger_inhibit = epics_signal_io(int, f"{prefix}TriggerInhibitM")
            self.trigger_level = epics_signal_io(int, f"{prefix}TriggerLevelA")
            self.trigger_rate = epics_signal_io(int, f"{prefix}TriggerRateA")
            self.trigger_advanced_mode = epics_signal_io(
                int, f"{prefix}TriggerAdvancedModeB"
            )
            self.trigger_holdoff = epics_signal_io(int, f"{prefix}TriggerHoldoffA")
            self.trigger_prescale = epics_signal_io(int, f"{prefix}TriggerPrescaleL")
        # Burst settings
        with self.add_children_as_readables(ConfigSignal):
            self.burst_mode = epics_signal_io(int, f"{prefix}BurstModeB")
            self.burst_count = epics_signal_io(int, f"{prefix}BurstCountL")
            self.burst_mode = epics_signal_io(int, f"{prefix}BurstConfigB")
            self.burst_delay = epics_signal_io(int, f"{prefix}BurstDelayA")
            self.burst_period = epics_signal_io(int, f"{prefix}BurstPeriodA")
        super().__init__(name=name)


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
