import pytest
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


class MotorIOC(PVGroup):
    """
    An IOC with some motor records, similar to those found in a VME crate.

    """

    "25idcVME:m1.VAL"
    m1 = pvproperty(value=5000.0, doc="SLT V Upper", record=records.MotorFields)
    m2 = pvproperty(value=5000.0, doc="SLT V Lower", record=records.MotorFields)
    m3 = pvproperty(value=5000.0, doc="SLT H Inb", record=records.MotorFields)


@pytest.fixture
def ioc_motor():
    with simulated_ioc(MotorIOC, prefix="vme_crate_ioc:") as pvdb:
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
