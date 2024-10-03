"""Loader for creating instances of the devices from a config file."""

import time
import asyncio
import inspect
import logging
import os
from pathlib import Path
from typing import Mapping

import tomlkit
from ophyd_async.core import DEFAULT_TIMEOUT, NotConnected
from ophyd import Device as ThreadedDevice
from ophyd.sim import make_fake_device
from ophydregistry import Registry

from .exceptions import InvalidConfiguration

log = logging.getLogger(__name__)


class Instrument:
    """A beamline instrument built from config files of Ophyd devices.

    *device_classes* should be dictionary that maps configuration
     section names to device classes (or similar items).

    Example:

    ```python
    instrument = Instrument({
      "ion_chamber": IonChamber
      "motors": load_motors,
    })
    ```

    The values in *device_classes* should be one of the following:

    1. A device class
    2. A callable that returns an instantiated device object
    3. A callable that returns a sequence of device objects

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
            for params in cfg.get(key, []):
                self.validate_params(params, Klass)
                device = self.make_device(params, Klass)
                try:
                    # Maybe its a list of devices?
                    devices.extend(device)
                except TypeError:
                    # No, assume it's just a single device then
                    devices.append(device)
        # Save devices for connecting to later
        self.devices.extend(devices)
        return devices

    def validate_params(self, params, Klass):
        """Check that parameters match a Device class's initializer."""
        sig = inspect.signature(Klass)
        has_kwargs = any([param.kind == param.VAR_KEYWORD for param in sig.parameters.values()])
        # Make sure we're not missing any required parameters
        for key, sig_param in sig.parameters.items():
            # Check for missing parameters
            param_missing = key not in params
            param_required = (sig_param.default is sig_param.empty and sig_param.kind != sig_param.VAR_KEYWORD)
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
        """Create the devices from their parameters."""
        # Mock threaded ophyd devices if necessary
        try:
            if issubclass(Klass, ThreadedDevice):
                Klass = make_fake_device(Klass)
        except TypeError:
            pass
        # Check if we need to inject the registry
        extra_params = {}
        sig = inspect.signature(Klass)
        if "registry" in sig.parameters.keys():
            extra_params = {"registry": self.registry}
        # Create the device
        result = Klass(**params, **extra_params)
        return result

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
        t0 = time.monotonic()
        # Sort out which devices are which
        threaded_devices = []
        async_devices = []
        for device in self.devices:
            if hasattr(device, "connect"):
                async_devices.append(device)
            else:
                threaded_devices.append(device)
        # Connect to async devices
        aws = (
            dev.connect(mock=mock, timeout=timeout, force_reconnect=force_reconnect)
            for dev in async_devices
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
                log.debug(f"Failed connection for device {device.name}")
                exceptions[device.name] = result
        # Connect to threaded devices
        timeout_reached = False
        while not timeout_reached and len(threaded_devices) > 0:
            # Remove any connected devices for the running list
            connected_devices = [dev for dev in threaded_devices if dev.connected]
            new_devices.extend(connected_devices)
            threaded_devices = [dev for dev in threaded_devices if dev not in connected_devices]
            # Tick the clock for the next round through the while loop
            await asyncio.sleep(min((0.05, timeout / 10.0)))
            timeout_reached = (time.monotonic() - t0) > timeout
        # Add disconnected devices to the exception list
        for device in threaded_devices:
            try:
                device.wait_for_connection(timeout=0)
            except TimeoutError as exc:
                exceptions[device.name] = NotConnected(str(exc))
        # Raise exceptions if any were present
        if len(exceptions) > 0:
            raise NotConnected(exceptions)
        return new_devices

    async def load(self, connect: bool = True, device_classes: Mapping | None = None):
        """Load instrument specified in config files.

        Config files are read from the environmental variable
        HAVEN_CONFIG_FILES.

        Parameters
        ==========
        connect
          If true, establish connections for the devices now.
        device_classes
          A temporary set of device classes to use for this call
          only. Overrides any device classes given during
          initalization.

        """
        self.devices = []
        # Decide which config files to use
        env_key = "HAVEN_CONFIG_FILES"
        if env_key in os.environ.keys():
            file_paths = os.environ.get("HAVEN_CONFIG_FILES", "")
            file_paths = [Path(fp) for fp in file_paths.split(":")]
        else:
            file_paths = [Path(__file__).parent.resolve() / "iconfig_testing.toml"]
        # Load the instrument from config files
        old_classes = self.device_classes
        try:
            # Temprary override of device classes
            if device_classes is not None:
                self.device_classes = device_classes
            # Parse TOML files
            for fp in file_paths:
                with open(fp, mode="tr", encoding="utf-8") as fd:
                    self.parse_toml_file(fd)
        finally:
            self.device_classes = old_classes
        # Connect the devices
        if connect:
            new_devices = await self.connect(mock=not self.hardware_is_present)
        else:
            new_devices = self.devices
        # Registry devices
        for device in new_devices:
            self.registry.register(device)
