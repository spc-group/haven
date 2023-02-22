from typing import Mapping

from ophyd import sim

from .instrument_registry import registry as default_registry, InstrumentRegistry
from .energy_positioner import load_energy_positioner
from .motor import load_all_motors
from .ion_chamber import load_ion_chambers
from .fluorescence_detector import load_fluorescence_detectors
from .monochromator import load_monochromator
from .camera import load_cameras
from .shutter import load_shutters
from .stage import load_stages
from .aps import load_aps
from .power_supply import load_power_supplies
from .xray_source import load_xray_sources
from .slits import load_slits
from .._iconfig import load_config


__all__ = ["load_instrument"]


def load_instrument(registry: InstrumentRegistry = default_registry,
                    config: Mapping = None):
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

    """
    # Clear out any existing registry entries
    registry.clear()
    # Load the configuration
    if config is None:
        config = load_config()
    # Import each device type for the instrument
    load_simulated_devices(config=config)
    load_energy_positioner(config=config)
    load_all_motors(config=config)
    load_monochromator(config=config)
    load_cameras(config=config)
    load_shutters(config=config)
    load_stages(config=config)
    load_power_supplies(config=config)
    load_slits(config=config)
    # Detectors
    load_ion_chambers(config=config)
    load_fluorescence_detectors(config=config)
    # Facility-related devices
    load_aps(config=config)
    load_xray_sources(config=config)


def load_simulated_devices(config={}):
    # Motors
    motor = sim.SynAxis(name="sim_motor", labels={"motors"})
    default_registry.register(motor)
    # Detectors
    detector = sim.SynGauss(
        name="sim_detector",
        motor=motor,
        motor_field="sim_motor",
        center=0,
        Imax=1,
    )
    default_registry.register(detector)
