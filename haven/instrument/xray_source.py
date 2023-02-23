from apstools.devices.aps_undulator import ApsUndulator

from .instrument_registry import registry
from .._iconfig import load_config


def load_xray_sources(config=None):
    if config is None:
        config = load_config()
    # Determine the X-ray source type (undulator vs bending magnet)
    data = config["xray_source"]
    if data["type"] == "undulator":
        dev = ApsUndulator(data["prefix"], name="undulator", labels={"xray_sources"})
        registry.register(dev)
