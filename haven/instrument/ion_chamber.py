"""Holds detector descriptions and assignments to EPICS PVs."""

from ophyd import Device, EpicsMotor, EpicsSignal, EpicsSignalRO, Component as Cpt
from apstools.devices import SRS570_PreAmplifier

from .instrument_registry import registry


@registry.register
class IonChamber(Device):
    """An ion chamber at a spectroscopy beamline.

    Also includes the pre-amplifier.

    """

    pre_amp = Cpt(SRS570_PreAmplifier, "PRE_AMP_PREFIX")
    sensitivity = Cpt(EpicsSignal, "PV")
    offset = Cpt(EpicsSignal, "PV")
    counts = Cpt(EpicsSignalRO, "PV")


I0 = IonChamber(
    "PV_PREFIX",
    name="I0",
    labels={
        "ion_chamber",
    },
)
It = IonChamber(
    "PV_PREFIX",
    name="It",
    labels={
        "ion_chamber",
    },
)
Iref = IonChamber(
    "PV_PREFIX",
    name="Iref",
    labels={
        "ion_chamber",
    },
)
Ipre_slit = IonChamber(
    "PV_PREFIX",
    name="Ipre_slit",
    labels={
        "ion_chamber",
    },
)
