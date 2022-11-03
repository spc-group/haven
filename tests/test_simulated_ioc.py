import logging
import time
from pathlib import Path

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

from haven.simulated_ioc import simulated_ioc, ResponsiveMotorFields


log = logging.getLogger(__name__)


ioc_dir = Path(__file__).parent.resolve() / "iocs"


class UndulatorIOC(PVGroup):
    """
    An IOC that looks like an undulator.

    E.g. "25IDds:Energy"

    """

    ScanEnergy = pvproperty(value=0, doc="ID Energy Scan Input", dtype=PvpropertyDouble)
    Energy = pvproperty(value=0, doc="", record=ResponsiveMotorFields, dtype=PvpropertyDouble)
    Busy = pvproperty(value=0, doc="")
    Stop = pvproperty(value=0, doc="")


@pytest.fixture
def ioc_undulator():
    with simulated_ioc(fp=ioc_dir / "undulator.py") as pvdb:
    # with simulated_ioc([UndulatorIOC], prefixes=["id_ioc:"]) as pvdb:
        yield pvdb

# @pytest.fixture
# def ioc_mono_undulator():
#     # with simulated_ioc([MonoIOC, UndulatorIOC], prefixes=["mono_ioc:", "id_ioc:"]) as pvdb:
#     with simulated_ioc([MonoIOC, UndulatorIOC], prefixes=["mono_ioc:", "id_ioc:"]) as pvdb:
#         yield pvdb


# class MonoIOC(PVGroup):
#     """
#     An IOC with some motor records, similar to those found in a VME crate.

#     """

#     m1 = pvproperty(value=0, doc="horiz", record=ResponsiveMotorFields)
#     m2 = pvproperty(value=0, doc="vert", record=ResponsiveMotorFields)
#     m3 = pvproperty(value=0, doc="bragg", record=ResponsiveMotorFields)
#     m4 = pvproperty(value=0, doc="gap", record=ResponsiveMotorFields)
#     m5 = pvproperty(value=0, doc="roll2", record=ResponsiveMotorFields)
#     m6 = pvproperty(value=0, doc="pitch2", record=ResponsiveMotorFields)
#     m7 = pvproperty(value=0, doc="roll-int", record=ResponsiveMotorFields)
#     m8 = pvproperty(value=0, doc="pi-int", record=ResponsiveMotorFields)
#     Energy = pvproperty(value=10000.0, doc="Energy", record=ResponsiveMotorFields)


@pytest.fixture
def ioc_mono():
    with simulated_ioc(fp=ioc_dir / "mono.py") as pvdb:
    # with simulated_ioc([MonoIOC], prefixes=["mono_ioc:"]) as pvdb:
        yield pvdb


# class ScalerIOC(PVGroup):
#     """An IOC mimicing a scaler connected to a VME crate."""

#     S2 = pvproperty(name=".S2", value=21000000, doc="It")
#     CNT = pvproperty(name=".CNT", value=1)
#     TP = pvproperty(name=".TP", value=1.)
#     calc2 = pvproperty(name="_calc2.VAL", value=2.35)


@pytest.fixture
def ioc_scaler():
    with simulated_ioc(fp=ioc_dir / "scaler.py") as pvdb:
    # with simulated_ioc([ScalerIOC], prefixes=["vme_crate_ioc"]) as pvdb:
        yield pvdb


# class MotorIOC(PVGroup):
#     """
#     An IOC with some motor records, similar to those found in a VME crate.

#     E.g. "25idcVME:m1.VAL"

#     """

#     m1 = pvproperty(value=5000.0, doc="SLT V Upper", record=ResponsiveMotorFields)
#     m2 = pvproperty(value=5000.0, doc="SLT V Lower", record=ResponsiveMotorFields)
#     m3 = pvproperty(value=5000.0, doc="SLT H Inb", record=ResponsiveMotorFields)


@pytest.fixture
def ioc_motor():
    with simulated_ioc(fp=ioc_dir / "motor.py") as pvdb:
    # with simulated_ioc([MotorIOC], prefixes=["vme_crate_ioc:"]) as pvdb:
        yield pvdb


# class SR570IOC(PVGroup):
#     """An IOC with an SR570 pre-amplifier.

#     E.g.

#     - 25idc:SR01:IpreSlit:sens_num.VAL"
#     - 25idc:SR01:IpreSlit:sens_unit.VAL

#     """

#     sens_num = pvproperty(
#         value="5",
#         enum_strings=["1", "2", "5", "10", "20", "50", "100", "200", "500"],
#         record="mbbi",
#         dtype=ChannelType.ENUM,
#     )
#     sens_unit = pvproperty(
#         value="nA/V",
#         enum_strings=["pA/V", "nA/V", "uA/V", "mA/V"],
#         record="mbbi",
#         dtype=ChannelType.ENUM,
#     )

@pytest.fixture
def ioc_preamp():
    with simulated_ioc(fp=ioc_dir / "preamp.py") as pvdb:
        yield pvdb

# @pytest.fixture
# def ioc_ion_chamber():
#     with simulated_ioc([SR570IOC, ScalerIOC], prefixes=["preamp_ioc:", "vme_crate_ioc"]) as pvdb:
#         yield pvdb


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
    with simulated_ioc(fp=ioc_dir / "simple.py") as pvdb:
        yield pvdb


# class VortexIOC(PVGroup):
#     """
#     An IOC with three uncoupled read/writable PVs

#     Scalar PVs
#     ----------
#     A (int)
#     B (float)

#     Vectors PVs
#     -----------
#     C (vector of int)
#     """

#     NumImages = pvproperty(value=1, doc="Number of images to capture total.")
#     TriggerMode = pvproperty(value=1, doc="Operation mode for triggering the detector")
#     Acquire = pvproperty(value=0, doc="Acquire the data")
#     Erase = pvproperty(
#         value=0, doc="Erases the data in preparation for collecting new data"
#     )


@pytest.fixture
def ioc_vortex():
    # with simulated_ioc([VortexIOC], prefixes=["xspress:"]) as pvdb:
    with simulated_ioc(fp=ioc_dir / "vortex.py") as pvdb:
        yield pvdb


def test_simulated_ioc(ioc_simple):
    assert caget("simple:B", use_monitor=False) == 2.0
    caput("simple:A", 5)
    time.sleep(0.1)
    assert caget("simple:A", use_monitor=False) == 5


def test_motor_ioc(ioc_motor):
    assert caget("vme_crate_ioc:m1", use_monitor=False) == 5000.0
    # Change the value
    caput("vme_crate_ioc:m1", 4000.0)
    time.sleep(5)
    # Check that the record got updated
    assert caget("vme_crate_ioc:m1.VAL", use_monitor=False) == 4000.0
    assert caget("vme_crate_ioc:m1.RBV", use_monitor=False) == 4000.0


def test_mono_ioc(ioc_mono):
    # Test a regular motor
    caput("mono_ioc:m1", 0)
    assert caget("mono_ioc:m1", use_monitor=False) == 0.0
    # Change the value
    caput("mono_ioc:m1", 4000.0)
    time.sleep(0.1)
    # Check that the record got updated
    assert caget("mono_ioc:m1", use_monitor=False) == 4000.0
    assert caget("mono_ioc:m1.VAL", use_monitor=False) == 4000.0
    assert caget("mono_ioc:m1.RBV", use_monitor=False) == 4000.0
    # Test the energy motor
    caput("mono_ioc:Energy", 10000.)
    time.sleep(0.1)
    assert caget("mono_ioc:Energy", use_monitor=False) == 10000.0
    # Change the value
    caput("mono_ioc:Energy", 6000.0)
    time.sleep(0.1)
    # Check that the record got updated
    assert caget("mono_ioc:Energy.VAL", use_monitor=False) == 6000.0
    assert caget("mono_ioc:Energy.RBV", use_monitor=False) == 6000.0


def test_ioc_timing():
    """Check that the IOC's don't take too long to load."""
    # Launch the IOC numerous times to see how reproducible it is
    for pass_num in range(5):
        start = time.time()
        with simulated_ioc(fp=ioc_dir / "undulator.py") as pvdb:
            caput("id_ioc:Energy", 100)
            new_value = caget("id_ioc:Energy", use_monitor=False)
        assert new_value == 100.
        print(f"Finish pass {pass_num} in {time.time() - start} seconds.")
        pass_time = time.time() - start
        msg = f"Pass {pass_num} took {pass_time} seconds."
        assert pass_time < 4, msg


def test_mono_undulator_ioc_again(ioc_undulator):
    """Check that both mono and undulator IOC's can load in a second set
    of tests.
    
    This is in response to a specific test bug where this would fail.
    
    """
    pass

def test_mono_undulator_ioc_a_third_time(ioc_undulator):
    """Check that both mono and undulator IOC's can load in a second set
    of tests.

    This is in response to a specific test bug where this would fail.

    """
    pass
