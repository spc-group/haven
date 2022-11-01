from .instrument_registry import registry as default_registry
from .energy_positioner import load_energy_positioner
from .motor import load_vme_motors
from .ion_chamber import load_ion_chambers
from .monochromator import load_monochromator
from .._iconfig import load_config


def load_instrument(registry=default_registry, config=None):
    # Clear out any existing registry entries
    registry.clear()
    # Load the configuration
    if config is None:
        config = load_config()
    # Import each device type for the instrument
    load_energy_positioner(config=config)
    load_ion_chambers(config=config)
    load_vme_motors(config=config)
    load_monochromator(config=config)
