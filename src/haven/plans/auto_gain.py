import numpy as np
import pandas as pd
from bluesky import plan_stubs as bps
from bluesky import plans as bp
from bluesky.callbacks.core import CollectThenCompute
from bluesky.preprocessors import subs_decorator

from haven import instrument


class AutoGainCallback(CollectThenCompute):
    def __init__(self, devices, voltage_limits=(0.5, 4.5), *args, **kwargs):
        self.devices = devices
        self.best_sens_levels = {}
        self.llim = min(voltage_limits)
        self.hlim = max(voltage_limits)
        super().__init__(*args, **kwargs)

    def compute(self):
        # Empty dictionaries to hold results
        voltages = {dev.name: [] for dev in self.devices}
        sens_levels = {dev.name: [] for dev in self.devices}
        self.best_sens_levels = {}
        # Extract data from the events list
        for event in self._events:
            data = event["data"]
            for dev in self.devices:
                voltages[dev.name].append(data[f"{dev.name}_volts"])
                sens_levels[dev.name].append(data[f"{dev.name}_sensitivity_sens_level"])
        # Turn data into pandas series
        for device in self.devices:
            series = pd.Series(voltages[device.name], index=sens_levels[device.name])
            if (series < self.llim).all():
                best_level = series.index.max()
            elif (series > self.hlim).all():
                best_level = series.index.min()
            else:
                in_range_series = series[(series > self.llim) & (series < self.hlim)]
                best_level = in_range_series.idxmax()
                self.best_sens_levels[device.name] = best_level


def auto_gain(devices="ion_chambers"):
    """A plan to automatically set the gain on an ion chamber."""
    if isinstance(devices, str):
        devices = instrument.registry.findall(any=devices)
    # Prepare devices and device range arguments
    scan_args = []
    hints = []
    for device in devices:
        hints.append(device.sensitivity.sens_level.name)
        hints.append(device.volts.name)
        limits = device.sensitivity.sens_level.limits
        scan_args.extend(
            [device.sensitivity.sens_level, np.arange(limits[0], limits[1] + 1)]
        )
    # Hinting to make the best effort callback work properly
    _md = {
        "hints": {"dimensions": [(hints, "primary")]},
    }
    # Prepare detectors (we need to include the sensitivity level)
    detectors = [(dev, dev.volts, dev.sensitivity.sens_level) for dev in devices]
    detectors = [det for sublist in detectors for det in sublist]
    # Save motor kinds to restore later
    kinds = {dev.name: dev.sensitivity.kind for dev in devices}
    # Set up the callback to do the calculating
    cb = AutoGainCallback(devices=devices)
    plan_func = subs_decorator(cb)(bp.list_scan)
    try:
        # Set motor kinds so they get tracked during acquisition
        for dev in devices:
            dev.sensitivity.kind = "normal"
        yield from plan_func(detectors, *scan_args, md=_md)
    finally:
        for dev in devices:
            dev.sensitivity.kind = kinds[dev.name]
    # Update the devices with the new values
    mv_args = []
    for dev in devices:
        mv_args.append(dev.sensitivity.sens_level)
        mv_args.append(cb.best_sens_levels.get(dev.name, None))
    # For some reason, just doing to mv plan once doesn't set the values.
    # Should investigate more
    is_done = False
    while not is_done:
        is_done = True
        for dev in devices:
            best_level = cb.best_sens_levels.get(
                dev.name, dev.sensitivity.sens_level.get().readback
            )
            if dev.sensitivity.sens_level.get().readback != best_level:
                is_done = False
        yield from bps.mv(*mv_args)
