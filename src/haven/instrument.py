"""Loader for creating instances of the devices from a config file."""

import inspect
from typing import Mapping

import tomlkit

from .exceptions import InvalidConfiguration


class Instrument:
    """A beamline instrument built from config files of Ophyd devices.

    Parameters
    ==========
    device_classes
      Maps config section names to device classes.

    """

    def __init__(self, device_classes: Mapping):
        self.device_classes = device_classes

    def parse_toml_file(self, fd):
        """Parse TOML instrument configuration and create devices.

        An open file descriptor
        """
        config = tomlkit.load(fd)
        return self.parse_config(config)

    def parse_config(self, cfg):
        devices = []
        for key, Klass in self.device_classes.items():
            # Create the devices
            for params in cfg[key]:
                self.validate_params(params, Klass)
                device = self.make_device(params, Klass)
                devices.append(device)
        return devices

    def validate_params(self, params, Klass):
        """Check that parameters match a Device class's initializer."""
        sig = inspect.signature(Klass)
        # Make sure we're not missing any required parameters
        for key, sig_param in sig.parameters.items():
            # Check for missing parameters
            param_missing = key not in params
            param_required = sig_param.default is sig_param.empty
            if param_missing and param_required:
                raise InvalidConfiguration(
                    f"Missing required key '{key}' for {Klass}: {params}"
                )
            # Check types
            if not param_missing:
                correct_type = isinstance(params[key], sig_param.annotation)
                if not correct_type:
                    raise InvalidConfiguration(
                        f"Incorrect type for {Klass} key '{key}': "
                        f"expected `{sig_param.annotation}` but got "
                        f"`{type(params[key])}`."
                    )

    def make_device(self, params, Klass):
        """Create the device from its parameters."""
        return Klass(**params)
