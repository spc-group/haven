import asyncio

from ophyd import Device, Component as Cpt, Kind
from apstools.synApps import TransformRecord

from .._iconfig import load_config
from .motor import HavenMotor
from .. import exceptions
from .device import aload_devices, make_device, RegexComponent as RCpt


class HighHeatLoadMirror(Device):
    bendable = False
    # Physical motors
    transverse = Cpt(HavenMotor, "m1")
    roll = Cpt(HavenMotor, "m2")
    upstream = Cpt(HavenMotor, "m3")
    downstream = Cpt(HavenMotor, "m4")

    # Pseudo motors
    pitch = Cpt(HavenMotor, "coarsePitch", kind=Kind.hinted)
    normal = Cpt(HavenMotor, "lateral", kind=Kind.hinted)

    # Standard transform records for the pseudo motors
    drive_transform = Cpt(
        TransformRecord, "lats:Drive", kind=Kind.config
    )
    readback_transform = Cpt(
        TransformRecord, "lats:Readback", kind=Kind.config
    )


class BendableHighHeatLoadMirror(HighHeatLoadMirror):
    bendable = True
    bender = Cpt(HavenMotor, "m5")


class KBMirror(Device):
    """A single mirror in a KB mirror set."""

    pitch = Cpt(HavenMotor, "pitch")
    normal = Cpt(HavenMotor, "height")

    # The pseudo motor transform records have
    # a missing ':', so we need to remove it.
    drive_transform = RCpt(
        TransformRecord, "Drive", pattern=":([HV]):", repl=r"\1:", kind=Kind.config
    )
    readback_transform = RCpt(
        TransformRecord, "Readback", pattern=":([HV]):", repl=r"\1:", kind=Kind.config
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
        # Decide which base class of mirror to use
        class_name = mirror_config["device_class"]
        if mirror_config.get('bendable', False):
            class_name = f"Bendable{class_name}"
        DeviceClass = globals().get(class_name)
        # Check that it's a valid device class
        if DeviceClass is None:
            msg = f"mirrors.{name}.device_class={mirror_config['device_class']}"
            raise exceptions.UnknownDeviceConfiguration(msg)
        yield make_device(
            DeviceClass, prefix=mirror_config["prefix"], name=name, labels={"mirrors"}
        )


def load_mirrors(config=None):
    asyncio.run(aload_devices(*load_mirror_coros(config=config)))
