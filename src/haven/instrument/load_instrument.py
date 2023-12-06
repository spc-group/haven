import asyncio
from typing import Mapping

from ophyd import sim

from .._iconfig import load_config
from .aps import load_aps_coros
from .area_detector import load_area_detector_coros
from .camera import load_camera_coros
from .dxp import load_dxp_coros
from .energy_positioner import load_energy_positioner_coros
from .heater import load_heater_coros
from .instrument_registry import InstrumentRegistry
from .instrument_registry import registry as default_registry
from .ion_chamber import load_ion_chamber_coros
from .lerix import load_lerix_spectrometer_coros
from .monochromator import load_monochromator_coros
from .motor import HavenMotor, load_all_motor_coros
from .mirrors import load_mirror_coros
from .power_supply import load_power_supply_coros
from .shutter import load_shutter_coros
from .slits import load_slit_coros
from .stage import load_stage_coros
from .xray_source import load_xray_source_coros
from .xspress import load_xspress_coros

__all__ = ["load_instrument"]


async def aload_instrument(
    registry: InstrumentRegistry = default_registry, config: Mapping = None
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

    """
    coros = (
        *load_all_motor_coros(config=config),
        *load_camera_coros(config=config),
        *load_shutter_coros(config=config),
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
        *load_ion_chamber_coros(config=config),
        *load_area_detector_coros(config=config),
        *load_lerix_spectrometer_coros(config=config),
    )
    devices = await asyncio.gather(*coros)
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
    # Import devices concurrently
    loop = asyncio.get_event_loop()
    devices = loop.run_until_complete(
        aload_instrument(registry=registry, config=config)
    )
    # Also import some simulated devices for testing
    devices += load_simulated_devices(config=config)
    # Filter out devices that couldn't be reached
    if return_devices:
        devices = [d for d in devices if d is not None]
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
