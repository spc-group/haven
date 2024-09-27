"""Loader for creating instances of the devices from a config file."""

import asyncio
import inspect
import logging
import os
from pathlib import Path
from typing import Mapping

import tomlkit
from ophyd_async.core import DEFAULT_TIMEOUT, NotConnected
from ophydregistry import Registry

from .devices.ion_chamber import IonChamber
from .exceptions import InvalidConfiguration

log = logging.getLogger(__name__)


class Instrument:
    """A beamline instrument built from config files of Ophyd devices.

    Parameters
    ==========
    device_classes
      Maps config section names to device classes.

    """

    devices: list
    registry: Registry
    beamline_name: str = ""
    hardware_is_present: bool | None = None

    def __init__(self, device_classes: Mapping):
        self.devices = []
        self.registry = Registry(auto_register=False, use_typhos=False)
        self.device_classes = device_classes

    def parse_toml_file(self, fd):
        """Parse TOML instrument configuration and create devices.

        An open file descriptor
        """
        config = tomlkit.load(fd)
        # Set global parameters
        beamline = config.get("beamline", {})
        self.beamline_name = beamline.get("name", self.beamline_name)
        self.hardware_is_present = beamline.get(
            "hardware_is_present", self.hardware_is_present
        )
        # Make devices from config file
        return self.parse_config(config)

    def parse_config(self, cfg):
        devices = []
        for key, Klass in self.device_classes.items():
            # Create the devices
            for params in cfg[key]:
                self.validate_params(params, Klass)
                device = self.make_device(params, Klass)
                devices.append(device)
        # Save devices for connecting to later
        self.devices.extend(devices)
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
                has_type = not issubclass(sig_param.annotation, inspect._empty)
                if has_type and not correct_type:
                    raise InvalidConfiguration(
                        f"Incorrect type for {Klass} key '{key}': "
                        f"expected `{sig_param.annotation}` but got "
                        f"`{type(params[key])}`."
                    )

    def make_device(self, params, Klass):
        """Create the device from its parameters."""
        return Klass(**params)

    async def connect(
        self,
        mock: bool = False,
        timeout: float = DEFAULT_TIMEOUT,
        force_reconnect: bool = False,
    ):
        """Connect all Devices.

        Contains a timeout that gets propagated to device.connect methods.

        Parameters
        ----------
        mock:
          If True then use ``MockSignalBackend`` for all Signals
        timeout:
          Time to wait before failing with a TimeoutError.
        force_reconnect
          Force the signals to establish a new connection.
        """
        aws = (
            dev.connect(mock=mock, timeout=timeout, force_reconnect=force_reconnect)
            for dev in self.devices
        )
        results = await asyncio.gather(*aws, return_exceptions=True)
        # Filter out the disconnected devices
        new_devices = []
        exceptions = {}
        for device, result in zip(self.devices, results):
            if result is None:
                log.debug(f"Successfully connected device {device.name}")
                new_devices.append(device)
            else:
                # Unexpected exception, raise it so it can be handled
                exceptions[device.name] = result
        # Register connected devices with the registry
        if self.registry is not None:
            for device in new_devices:
                self.registry.register(device)
        # Raise exceptions if any were present
        if len(exceptions) > 0:
            raise NotConnected(exceptions)
        return new_devices

    async def load(self):
        """Load instrument specified in config files.

        Config files are read from the environmental variable
        HAVEN_CONFIG_FILES.

        """
        file_paths = os.environ.get("HAVEN_CONFIG_FILES", "").split(":")
        file_paths = [Path(fp) for fp in file_paths]
        for fp in file_paths:
            with open(fp, mode="tr", encoding="utf-8") as fd:
                self.parse_toml_file(fd)
        # Connect the devices
        await self.connect(mock=not self.hardware_is_present)


instrument = Instrument({
    "ion_chamber": IonChamber
})
