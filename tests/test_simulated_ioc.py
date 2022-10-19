import pytest
from caproto import ChannelType
from caproto.server import (
    PVGroup,
    template_arg_parser,
    pvproperty,
    run,
    records,
    PvpropertyDouble,
)
from epics import caget, caput

from haven.simulated_ioc import simulated_ioc


class UndulatorIOC(PVGroup):
    """
    An IOC that looks like an undulator.

    E.g. "25IDds:Energy"

    """

    m1 = pvproperty(value=0, doc="horiz")


@pytest.fixture
def ioc_undulator():
    with simulated_ioc(UndulatorIOC, prefix="id_ioc:") as pvdb:
        yield pvdb


class MonoIOC(PVGroup):
    """
    An IOC with some motor records, similar to those found in a VME crate.

    """

    m1 = pvproperty(value=0, doc="horiz", record=records.MotorFields)
    m2 = pvproperty(value=0, doc="vert", record=records.MotorFields)
    m3 = pvproperty(value=0, doc="bragg", record=records.MotorFields)
    m4 = pvproperty(value=0, doc="gap", record=records.MotorFields)
    m5 = pvproperty(value=0, doc="roll2", record=records.MotorFields)
    m6 = pvproperty(value=0, doc="pitch2", record=records.MotorFields)
    m7 = pvproperty(value=0, doc="roll-int", record=records.MotorFields)
    m8 = pvproperty(value=0, doc="pi-int", record=records.MotorFields)
    Energy = pvproperty(value=10000.0, doc="Energy", record=records.MotorFields)


@pytest.fixture
def ioc_mono():
    with simulated_ioc(MonoIOC, prefix="mono_ioc:") as pvdb:
        yield pvdb


class MotorIOC(PVGroup):
    """
    An IOC with some motor records, similar to those found in a VME crate.

    E.g. "25idcVME:m1.VAL"

    """

    m1 = pvproperty(value=5000.0, doc="SLT V Upper", record=records.MotorFields)
    m2 = pvproperty(value=5000.0, doc="SLT V Lower", record=records.MotorFields)
    m3 = pvproperty(value=5000.0, doc="SLT H Inb", record=records.MotorFields)


@pytest.fixture
def ioc_motor():
    with simulated_ioc(MotorIOC, prefix="vme_crate_ioc:") as pvdb:
        yield pvdb


class SR570IOC(PVGroup):
    """An IOC with an SR570 pre-amplifier.

    E.g.

    - 25idc:SR01:IpreSlit:sens_num.VAL"
    - 25idc:SR01:IpreSlit:sens_unit.VAL

    """

    sens_num = pvproperty(
        value="5",
        enum_strings=["1", "2", "5", "10", "20", "50", "100", "200", "500"],
        record="mbbi",
        dtype=ChannelType.ENUM,
    )
    sens_unit = pvproperty(
        value="nA/V",
        enum_strings=["pA/V", "nA/V", "uA/V", "mA/V"],
        record="mbbi",
        dtype=ChannelType.ENUM,
    )


@pytest.fixture
def ioc_ion_chamber():
    with simulated_ioc(SR570IOC, prefix="preamp_ioc:") as pvdb:
        yield pvdb


class SimpleIOC(PVGroup):
    """
    An IOC with three uncoupled read/writable PVs

    Scalar PVs
    ----------
    A (int)
    B (float)

    Vectors PVs
    -----------
    C (vector of int)
    """

    A = pvproperty(value=1, doc="An integer")
    B = pvproperty(value=2.0, doc="A float")
    C = pvproperty(value=[1, 2, 3], doc="An array of integers")


@pytest.fixture
def ioc_simple():
    with simulated_ioc(SimpleIOC, prefix="simple:") as pvdb:
        yield pvdb


class VortexIOC(PVGroup):
    """
    An IOC with three uncoupled read/writable PVs

    Scalar PVs
    ----------
    A (int)
    B (float)

    Vectors PVs
    -----------
    C (vector of int)
    """

    NumImages = pvproperty(value=1, doc="Number of images to capture total.")
    TriggerMode = pvproperty(value=1, doc="Operation mode for triggering the detector")
    Acquire = pvproperty(value=0, doc="Acquire the data")
    Erase = pvproperty(
        value=0, doc="Erases the data in preparation for collecting new data"
    )


@pytest.fixture
def ioc_vortex():
    with simulated_ioc(VortexIOC, prefix="xspress:") as pvdb:
        yield pvdb


def test_simulated_ioc(ioc_simple):
    assert caget("simple:B") == 2.0
    caput("simple:A", 5)
    assert caget("simple:A") == 5
