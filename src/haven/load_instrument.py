import asyncio
import logging
import warnings
from typing import Mapping

from ophyd import sim
from ophyd_async.core import NotConnected
from rich import print

from ._iconfig import load_config
from .devices.aerotech import load_aerotech_stages
from .devices.aps import load_aps
from .devices.area_detector import load_area_detectors
from .devices.beamline_manager import load_beamline_manager
from .devices.camera import load_cameras
from .device import connect_devices
from .devices.dxp import load_dxp_detectors
from .devices.energy_positioner import load_energy_positioner
from .devices.heater import load_heaters
from .devices.instrument_registry import InstrumentRegistry
from .devices.instrument_registry import registry as default_registry
from .devices.lerix import load_lerix_spectrometers
from .devices.motor import HavenMotor, load_motors
from .devices.power_supply import load_power_supplies
from .devices.robot import load_robots
from .devices.shutter import load_shutters
from .devices.slits import load_slits
from .devices.xia_pfcu import load_xia_pfcu4s
from .devices.xspress import load_xspress_detectors
from .instrument import Instrument

__all__ = ["load_instrument"]

log = logging.getLogger(__name__)


async def load_instrument(
    registry: InstrumentRegistry = default_registry,
    config: Mapping = None,
    wait_for_connection: bool = True,
    timeout: int = 5,
    return_devices: bool = False,
):
    """Load the beamline instrumentation.

    This function will reach out and query various IOCs for motor
    information based on the information in *config* (see
    ``iconfig_default.toml`` for examples). Based on the
    configuration, it will create Ophyd devices and register them with
    *registry*.

    Parameters
    ==========
    registry:
      The registry into which the ophyd devices will be placed.
    config:
      The beamline configuration read in from TOML files. Mostly
      useful for testing.
    wait_for_connection
      If true, only connected devices will be kept.
    timeout
      How long to wait for if *wait_for_connection* is true.
    return_devices
      If true, return the newly loaded devices when complete.

    """
    instrument = Instrument(
        {
            "ion_chamber": IonChamber,
            "high_heat_load_mirror": HighHeatLoadMirror,
            "kb_mirrors": KBMirrors,
            "xy_stage": XYStage,
            "table": Table,
            "aerotech_stage": AerotechStage,
            "motor": Motor,
            # Motors happen later so duplicate motors can be removed
            "motors": load_motors,
        },
    )
    await instrument.load()
    # Connect the instrument
    print(f"Loaded [repr.number]{len(instrument.devices)}[/] devices.", flush=True)
    # Clear out any existing registry entries
    registry = instrument.registry
    # Load the configuration
    if config is None:
        config = load_config()
    # Load the devices from the configuration files
    # Synchronous (threaded) devices
    devices = []
    devices.extend(
        [
            load_aps(config=config),
            *load_area_detectors(config=config),
            load_beamline_manager(config=config),
            *load_cameras(config=config),
            *load_dxp_detectors(config=config),
            load_energy_positioner(config=config),
            *load_heaters(config=config),
            *load_lerix_spectrometers(config=config),
            *load_power_supplies(config=config),
            *load_robots(config=config),
            *load_shutters(config=config),
            *load_slits(config=config),
            *load_xia_pfcu4s(config=config),
            *load_xspress_detectors(config=config),
        ]
    )
    # Filter out devices that couldn't be reached
    devices = [d for d in devices if d is not None]
    # Put the devices into the registry
    if not getattr(registry, "auto_register", True):
        [registry.register(device) for device in devices]
    # Only keep connected devices
    disconnected = []
    if wait_for_connection and registry is not None:
        disconnected = registry.pop_disconnected(timeout=timeout)
        devices = [dev for dev in devices if dev not in disconnected]
        if len(disconnected) > 0:
            msg = "Removed disconnected devices: "
            msg += ", ".join(dev.name for dev in disconnected)
            warnings.warn(msg)
            log.warning(msg)
    # Return the final list
    if return_devices:
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
