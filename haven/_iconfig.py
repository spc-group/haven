"""
Provide information from the iconfig.toml file.

Example TOML configuration file::

    # simple key:value pairs

    ADSIM_IOC_PREFIX: "bdpad:"
    GP_IOC_PREFIX: "bdp:"
    catalog: bdp2022
"""

__all__ = [
    "load_config",
]

import logging
from typing import Sequence

import pathlib
import tomli

log = logging.getLogger(__name__)


CONFIG_FILES = [
    pathlib.Path("~/bluesky/").expanduser() / "iconfig.toml",
    pathlib.Path("~/bluesky/instrument").expanduser() / "iconfig.toml",
]

default_config = {
    # Defaults go here, then get updated by toml loader
    "beamline": {
        "name": "SPC Beamline (sector unknown)",
        "ioc_prefix": "",
        "vme_prefix": "",
        "is_connected": False,
    },
    "ion_chamber": {
        "scaler": {"ioc": "", "record": ""},
        "preamp": {"ioc": "preamp_ioc"},
        "I0": {"scaler_channel": 2,
               "preamp_record": "SR570_1",
               "voltage_pv": "40iddVME:userCalc1",
        },
    },
    "fluorescence_detectors": {
        "vortex": {
            "pv_prefix": "",
        },
    },
    "facility": {
        "name": "Advanced Photon Source",
        "xray_source": "insertion device",
    },
    "motor": {
        "ioc": "vme_crate_ioc",
    },
    "monochromator": {
        "ioc": "mono_ioc",
        "energy_ioc": "mono_ioc",
    },
    "undulator": {
        "ioc": "id_ioc",
    },
}


def load_config(file_paths: Sequence[pathlib.Path] = CONFIG_FILES):
    config = default_config.copy()
    for fp in file_paths:
        if fp.exists():
            with open(fp, mode="rb") as fp:
                config.update(tomli.load(fp))
            log.info(f"Loaded config file: {fp}")
        else:
            log.debug(f"Could not find config file, skipping: {fp}")
    return config
