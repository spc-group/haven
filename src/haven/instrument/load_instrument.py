import asyncio
from typing import Mapping

from ophyd import sim

from .._iconfig import load_config
from .aerotech import load_aerotech_stage_coros
from .aps import load_aps_coros
from .area_detector import load_area_detector_coros
from .beamline_manager import load_beamline_manager_coros
from .camera import load_camera_coros
from .dxp import load_dxp_coros
from .energy_positioner import load_energy_positioner_coros
from .heater import load_heater_coros
from .instrument_registry import InstrumentRegistry
from .instrument_registry import registry as default_registry
from .ion_chamber import load_ion_chamber_coros
from .lerix import load_lerix_spectrometer_coros
from .mirrors import load_mirror_coros
from .monochromator import load_monochromator_coros
from .motor import HavenMotor, load_all_motor_coros
from .power_supply import load_power_supply_coros
from .robot import load_robot_coros
from .shutter import load_shutter_coros
from .slits import load_slit_coros
from .stage import load_stage_coros
from .table import load_table_coros
from .xia_pfcu import load_xia_pfcu4_coros
from .xray_source import load_xray_source_coros
from .xspress import load_xspress_coros

__all__ = ["load_instrument"]


async def aload_instrument(
    registry: InstrumentRegistry = default_registry,
    config: Mapping = None,
    return_devices: bool = False,
):
    """Asynchronously load the beamline instrumentation into an instrument
    registry.

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
    registry.clear()
    # Make sure we have the most up-to-date configuration
    # load_config.cache_clear()
    # Load the configuration
    if config is None:
        config = load_config()
    # Load devices concurrently
    coros = (
        *load_camera_coros(config=config),
        *load_beamline_manager_coros(config=config),
        *load_shutter_coros(config=config),
        *load_aerotech_stage_coros(config=config),
        *load_aps_coros(config=config),
        *load_monochromator_coros(config=config),
        *load_xray_source_coros(config=config),
        *load_energy_positioner_coros(config=config),
        *load_dxp_coros(config=config),
        *load_xspress_coros(config=config),
        *load_stage_coros(config=config),
        *load_heater_coros(config=config),
        *load_power_supply_coros(config=config),
        *load_slit_coros(config=config),
        *load_mirror_coros(config=config),
        *load_table_coros(config=config),
        *load_ion_chamber_coros(config=config),
        *load_area_detector_coros(config=config),
        *load_lerix_spectrometer_coros(config=config),
        *load_robot_coros(config=config),
        *load_xia_pfcu4_coros(config=config),
    )
    devices = await asyncio.gather(*coros)
    # Load the motor devices last so that we can check for existing
    # motors in the registry
    extra_motors = await asyncio.gather(*load_all_motor_coros(config=config))
    devices.extend(extra_motors)
    # Also import some simulated devices for testing
    devices += load_simulated_devices(config=config)
    # Filter out devices that couldn't be reached
    devices = [d for d in devices if d is not None]
    if return_devices:
        return devices


def load_instrument(
    registry: InstrumentRegistry = default_registry,
    config: Mapping = None,
    return_devices: bool = False,
):
    """Load the beamline instrumentation into an instrument registry.

    This function will reach out and query various IOCs for motor
    information based on the information in *config* (see
    ``iconfig_default.toml`` for examples). Based on the
    configuration, it will create Ophyd devices and register them with
    *registry*.

    This function starts the asyncio event loop. If one is already
    running (e.g. jupyter notebook), then use ``await
    aload_instrument()`` instead.

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
    # Import devices concurrently
    loop = asyncio.get_event_loop()
    coro = aload_instrument(registry=registry, config=config)
    devices = loop.run_until_complete(coro)
    if return_devices:
        return devices


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
