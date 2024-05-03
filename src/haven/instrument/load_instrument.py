import asyncio
from typing import Mapping

from ophyd import sim

from .._iconfig import load_config
from .aerotech import load_aerotech_stages
from .aps import load_aps
from .area_detector import load_area_detectors
from .beamline_manager import load_beamline_manager
from .camera import load_cameras
from .dxp import load_dxp_detectors
from .energy_positioner import load_energy_positioner
from .heater import load_heaters
from .instrument_registry import InstrumentRegistry
from .instrument_registry import registry as default_registry
from .ion_chamber import load_ion_chambers
from .lerix import load_lerix_spectrometers
from .mirrors import load_mirrors
from .monochromator import load_monochromators
from .motor import HavenMotor, load_motors
from .power_supply import load_power_supplies
from .robot import load_robots
from .shutter import load_shutters
from .slits import load_slits
from .stage import load_stages
from .table import load_tables
from .xia_pfcu import load_xia_pfcu4s
from .xray_source import load_xray_source
from .xspress import load_xspress_detectors

__all__ = ["load_instrument"]


def load_instrument(
    registry: InstrumentRegistry = default_registry,
    config: Mapping = None,
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
    return_devices
      If true, return the newly loaded devices when complete.

    """
    # Clear out any existing registry entries
    if registry is not None:
        registry.clear()
    # Make sure we have the most up-to-date configuration
    # load_config.cache_clear()
    # Load the configuration
    if config is None:
        config = load_config()
    # Synchronous loading of devices
    devices = [
        *load_aerotech_stages(config=config),
        load_aps(config=config),
        *load_area_detectors(config=config),
        load_beamline_manager(config=config),
        *load_cameras(config=config),
        *load_dxp_detectors(config=config),
        load_energy_positioner(config=config),
        *load_heaters(config=config),
        # *load_ion_chambers(config=config),
        *load_lerix_spectrometers(config=config),
        *load_mirrors(config=config),
        *load_monochromators(config=config),
        *load_power_supplies(config=config),
        *load_robots(config=config),
        *load_shutters(config=config),
        *load_slits(config=config),
        *load_stages(config=config),
        *load_tables(config=config),
        *load_xia_pfcu4s(config=config),
        load_xray_source(config=config),
        *load_xspress_detectors(config=config),
        # Load the motor devices last so that we can check for
        # existing motors in the registry
        # *load_motors(config=config),
    ]
    # Also import some simulated devices for testing
    devices += load_simulated_devices(config=config)
    # Filter out devices that couldn't be reached
    devices = [d for d in devices if d is not None]
    # Put the devices into the registry
    if registry is not None:
        [registry.register(device) for device in devices]
    if return_devices:
        return devices


# def load_instrument(
#     registry: InstrumentRegistry = default_registry,
#     config: Mapping = None,
#     return_devices: bool = False,
# ):
#     """Load the beamline instrumentation into an instrument registry.

#     This function will reach out and query various IOCs for motor
#     information based on the information in *config* (see
#     ``iconfig_default.toml`` for examples). Based on the
#     configuration, it will create Ophyd devices and register them with
#     *registry*.

#     This function starts the asyncio event loop. If one is already
#     running (e.g. jupyter notebook), then use ``await
#     aload_instrument()`` instead.

#     Parameters
#     ==========
#     registry:
#       The registry into which the ophyd devices will be placed.
#     config:
#       The beamline configuration read in from TOML files. Mostly
#       useful for testing.
#     return_devices
#       If true, return the newly loaded devices when complete.

#     """
#     # Import devices concurrently
#     loop = asyncio.get_event_loop()
#     coro = aload_instrument(registry=registry, config=config)
#     devices = loop.run_until_complete(coro)
#     if return_devices:
#         return devices


def load_simulated_devices(config={}):
    # Motors
    FakeMotor = sim.make_fake_device(HavenMotor)
    motor = FakeMotor(name="sim_motor", labels={"motors"})
    default_registry.register(motor)
    # Detectors
    detector = sim.SynGauss(
        name="sim_detector",
        motor=motor,
        motor_field="sim_motor",
        labels={"detectors"},
        center=0,
        Imax=1,
    )
    default_registry.register(detector)
    return (motor, detector)


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
