import asyncio

from ophyd import Device, Component as Cpt
from apstools.synApps import TransformRecord

from .._iconfig import load_config
from haven import HavenMotor, RegexComponent as RCpt, exceptions
from .device import aload_devices, make_device


class HighHeatLoadMirror(Device):
    pass


class KBMirror(Device):
    """A single mirror in a KB mirror set."""

    pitch = Cpt(HavenMotor, "pitch")
    normal = Cpt(HavenMotor, "height")

    # The pseudo motor transform records have
    # a missing ':', so we need to remove it.
    drive_transform = RCpt(
        TransformRecord, "Drive", pattern=":([HV]):", repl=r"\1:", kind="config"
    )
    readback_transform = RCpt(
        TransformRecord, "Readback", pattern=":([HV]):", repl=r"\1:", kind="config"
    )


class KBMirrors(Device):
    horiz = Cpt(KBMirror, "H:", labels={"mirrors"})
    vert = Cpt(KBMirror, "V:", labels={"mirrors"})


def load_mirror_coros(config=None):
    if config is None:
        config = load_config()
    # Create two-bounce KB mirror sets
    for name, kb_config in config.get("kb_mirrors", {}).items():
        yield make_device(
            KBMirrors, prefix=kb_config["prefix"], name=name, labels={"kb_mirrors"}
        )
    # Create single-bounce mirrors
    for name, mirror_config in config.get("mirrors", {}).items():
        DeviceClass = globals().get(mirror_config["device_class"])
        # Check that it's a valid device class
        if DeviceClass is None:
            msg = f"mirrors.{name}.device_class={mirror_config['device_class']}"
            raise exceptions.UnknownDeviceConfiguration(msg)
        yield make_device(
            DeviceClass, prefix=mirror_config["prefix"], name=name, labels={"mirrors"}
        )


def load_mirrors(config=None):
    asyncio.run(aload_devices(*load_mirror_coros(config=config)))
