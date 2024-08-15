import logging
import warnings
from typing import Mapping, Sequence

from apstools.utils.misc import safe_ophyd_name
from ophyd import Component as Cpt
from ophyd import EpicsMotor, EpicsSignal, EpicsSignalRO, Kind
from ophyd_async.core import ConfigSignal
from ophyd_async.core._utils import DEFAULT_TIMEOUT
from ophyd_async.epics.motor import Motor as MotorBase
from ophyd_async.epics.signal import epics_signal_r, epics_signal_rw
from ophyd_async.epics.signal._signal import _epics_signal_backend
from ophyd_async.core import SignalX, SignalBackend, DEFAULT_TIMEOUT, CalculatableTimeout, CalculateTimeout, AsyncStatus

from .._iconfig import load_config
from .device import connect_devices, make_device, resolve_device_names
from .instrument_registry import InstrumentRegistry
from .instrument_registry import registry as default_registry
from .motor_flyer import MotorFlyer

log = logging.getLogger(__name__)


class SignalX(SignalX):
    trigger_value = 1

    def __init__(self, *args, trigger_value=1, **kwargs):
        self.trigger_value = trigger_value
        super().__init__(*args, **kwargs)
    
    def trigger(
        self, wait=False, timeout: CalculatableTimeout = CalculateTimeout
    ) -> AsyncStatus:
        """Trigger the action and return a status saying when it's done"""
        if timeout is CalculateTimeout:
            timeout = self._timeout
        coro = self._backend.put(self.trigger_value, wait=wait, timeout=timeout)
        return AsyncStatus(coro)


def epics_signal_x(write_pv: str, name: str = "", trigger_value=1) -> SignalX:
    """Create a `SignalX` backed by 1 EPICS PVs

    Parameters
    ----------
    write_pv:
      The PV to write its initial value to on trigger
    trigger_value:
      The value to send to the write PV.
    """
    backend: SignalBackend = _epics_signal_backend(None, write_pv, write_pv)
    return SignalX(backend, name=name, trigger_value=trigger_value)


class Motor(MotorBase):
    """The default motor for asynchrnous movement."""

    def __init__(
        self, prefix: str, name="", labels={"motors"}, auto_name: bool = None
    ) -> None:
        """Parameters
        ==========
        auto_name
          If true, or None when no name was provided, the name for
          this motor will be set based on the motor's *description*
          field.

        """
        self._ophyd_labels_ = labels
        self.auto_name = bool(auto_name) or (auto_name is None and name == "")
        # Configuration signals
        with self.add_children_as_readables(ConfigSignal):
            self.description = epics_signal_rw(str, f"{prefix}.DESC")
        # Motor status signals
        self.motor_is_moving = epics_signal_r(int, f"{prefix}.MOVN")
        self.motor_done_move = epics_signal_r(int, f"{prefix}.DMOV")
        self.high_limit_switch = epics_signal_r(int, f"{prefix}.HLS")
        self.low_limit_switch = epics_signal_r(int, f"{prefix}.LLS")
        self.high_limit_travel = epics_signal_rw(float, f"{prefix}.HLM")
        self.low_limit_travel = epics_signal_rw(float, f"{prefix}.LLM")
        self.direction_of_travel = epics_signal_r(int, f"{prefix}.TDIR")
        self.soft_limit_violation = epics_signal_r(int, f"{prefix}.LVIO")
        # Load all the parent signals
        super().__init__(prefix=prefix, name=name)
        self.motor_stop = epics_signal_x(f"{prefix}.STOP", name=self.motor_stop.name)

    async def connect(
        self,
        mock: bool = False,
        timeout: float = DEFAULT_TIMEOUT,
        force_reconnect: bool = False,
    ):
        """Connect self and all child Devices.

        Contains a timeout that gets propagated to child.connect methods.

        Parameters
        ----------
        mock:
            If True then use ``MockSignalBackend`` for all Signals
        timeout:
            Time to wait before failing with a TimeoutError.

        """
        await super().connect(
            mock=mock, timeout=timeout, force_reconnect=force_reconnect
        )
        # Update the device's name
        if bool(self.auto_name):
            try:
                desc = await self.description.get_value()
            except Exception as exc:
                warnings.warn(
                    f"Could not read description for {self}. " "Name not updated. {exc}"
                )
                return
            # Only update the name if the description has been set
            if desc != "":
                self.set_name(safe_ophyd_name(desc))


class HavenMotor(MotorFlyer, EpicsMotor):
    """The default motor for haven movement.

    This motor also implements the flyer interface and so can be used
    in a fly scan, though no hardware triggering is supported.

    Returns to the previous value when being unstaged.

    """

    # Extra motor record components
    encoder_resolution = Cpt(EpicsSignal, ".ERES", kind=Kind.config)
    description = Cpt(EpicsSignal, ".DESC", kind="omitted")
    tweak_value = Cpt(EpicsSignal, ".TWV", kind="omitted")
    tweak_forward = Cpt(EpicsSignal, ".TWF", kind="omitted", tolerance=2)
    tweak_reverse = Cpt(EpicsSignal, ".TWR", kind="omitted", tolerance=2)
    motor_stop = Cpt(EpicsSignal, ".STOP", kind="omitted", tolerance=2)
    soft_limit_violation = Cpt(EpicsSignalRO, ".LVIO", kind="omitted")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def stage(self):
        super().stage()
        # Override some additional staged signals
        self._original_vals.setdefault(self.user_setpoint, self.user_readback.get())
        self._original_vals.setdefault(self.velocity, self.velocity.get())


async def load_motors(
    config: Mapping = None,
    registry: InstrumentRegistry = default_registry,
    auto_name=True,
) -> Sequence:
    """Load generic hardware motors from IOCs.

    This loader will skip motor prefixes that already exist in the
    registry *registry*, so it is a good idea to run this loader after
    other devices have been created that might potentially use some of
    these motors (e.g. mirrors, tables, etc.).

    Parameters
    ==========
    config
      The beamline configuration. If omitted, will use the config
      provided by :py:func:`haven._iconfig.load_config()`.
    registry
      The instrument registry to check for existing motors. Existing
      motors will not be duplicated.
    auto_name
      If true, motors will be named based on its description signal
      when connecting.

    Returns
    =======
    devices
      The newly created motor devices.

    """
    if config is None:
        config = load_config()
    # Create the motor devices
    devices = []
    for section_name, cfg in config.get("motor", {}).items():
        prefix = cfg["prefix"]
        num_motors = cfg["num_motors"]
        log.info(
            f"Preparing {num_motors} motors from IOC: " f"{section_name} ({prefix})"
        )
        for idx in range(num_motors):
            labels = {"motors", "extra_motors", "baseline", section_name}
            default_name = f"{prefix.strip(':')}_m{idx+1}"
            new_motor = Motor(
                prefix=f"{prefix}m{idx+1}",
                name=default_name,
                labels=labels,
                auto_name=auto_name,
            )
            devices.append(new_motor)
    # Removed motors that are already available somewhere else (e.g. KB Mirrors)
    existing_motors = registry.findall(label="motors", allow_none=True)
    existing_sources = [getattr(m.user_readback, "source", "") for m in existing_motors]
    existing_sources = [s for s in existing_sources if s != ""]
    devices = [
        m
        for m in devices
        if getattr(m.user_readback, "source", "") not in existing_sources
    ]
    # Connect to devices
    devices = await connect_devices(
        devices, mock=not config["beamline"]["is_connected"], registry=registry
    )
    return devices


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
