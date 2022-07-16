"""Holds detector descriptions and assignments to EPICS PVs."""

from ophyd.signal import EpicsSignal
from ophyd import sim


I0 = sim.SynGauss(
    "I0",
    sim.motor,
    "motor",
    center=-0.5,
    Imax=1,
    sigma=1,
    labels={"ion_chambers"},
)
It = sim.SynGauss(
    "It",
    sim.motor,
    "motor",
    center=-0.5,
    Imax=1,
    sigma=1,
    labels={"ion_chambers"},
)
Iref = sim.SynGauss(
    "Iref",
    sim.motor,
    "motor",
    center=-0.5,
    Imax=1,
    sigma=1,
    labels={"ion_chambers"},
)
Ipre_slit = sim.SynGauss(
    "Ipre_slit",
    sim.motor,
    "motor",
    center=-0.5,
    Imax=1,
    sigma=1,
    labels={"ion_chambers"},
)


ion_chambers = [I0, It, Iref, Ipre_slit]

# EpicsSignal("...", name="Ipre_slit"),
# EpicsSignal("...", name="I0"),
# EpicsSignal("...", name="It"),
# EpicsSignal("...", name="Iref"),
