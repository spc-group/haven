import logging
import time
import warnings
from typing import Mapping

from rich import print

from ._iconfig import load_config
from .devices.aerotech import AerotechStage
from .devices.aps import ApsMachine
from .devices.area_detector import make_area_detector
from .devices.beamline_manager import BeamlineManager
from .devices.dxp import make_dxp_device
from .devices.energy_positioner import EnergyPositioner
from .devices.heater import CapillaryHeater
from .devices.instrument_registry import InstrumentRegistry
from .devices.instrument_registry import registry as default_registry
from .devices.ion_chamber import IonChamber
from .devices.mirrors import HighHeatLoadMirror, KBMirrors
from .devices.motor import Motor, load_motors
from .devices.power_supply import NHQ203MChannel
from .devices.robot import Robot
from .devices.scaler import Scaler
from .devices.shutter import PssShutter
from .devices.slits import BladeSlits, ApertureSlits
from .devices.stage import XYStage
from .devices.table import Table
from .devices.xia_pfcu import PFCUFilterBank
from .devices.xspress import make_xspress_device
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
            "blade_slits": BladeSlits,
            "aperture_slits": ApertureSlits,
            "capillary_heater": CapillaryHeater,
            "power_supply": NHQ203MChannel,
            "synchrotron": ApsMachine,
            "robot": Robot,
            "pfcu4": PFCUFilterBank,
            "pss_shutter": PssShutter,
            "energy": EnergyPositioner,
            "xspress": make_xspress_device,
            "dxp": make_dxp_device,
            "beamline_manager": BeamlineManager,
            "area_detector": make_area_detector,
            "scaler": Scaler,
        },
    )
    t0 = time.monotonic()
    await instrument.load()
    # VME-style Motors happen later so duplicate motors can be
    # removed
    await instrument.load(device_classes={"motors": load_motors})
    # Notify with the new device count
    load_time = time.monotonic() - t0
    print(
        f"Loaded [repr.number]{len(instrument.devices)}[/] devices in {load_time:.1f} sec.",
        flush=True,
    )
    # Return the final list
    if return_devices:
        return devices
    else:
        return instrument


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
