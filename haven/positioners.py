"""Holds motor descriptions and assignments to EPICS PVs."""

from ophyd.epics_motor import EpicsMotor

slits_V = EpicsMotor("mini:slit:motor", name="slits_V")

ion_chambers = [
    EpicsMotor("", name="Ipre_slit"),
    EpicsMotor("", name="I0"),
    EpicsMotor("", name="It"),
    EpicsMotor("", name="Iref"),
]
