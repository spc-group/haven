import logging
import time
from pathlib import Path

import pytest
from caproto.server import (
    PVGroup,
    pvproperty,
    PvpropertyDouble,
)
from epics import caget, caput

from haven.simulated_ioc import simulated_ioc


log = logging.getLogger(__name__)


ioc_dir = Path(__file__).parent.resolve() / "iocs"


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
    caput("mono_ioc:Energy", 10000.0)
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
        with simulated_ioc(fp=ioc_dir / "undulator.py"):
            caput("id_ioc:Energy", 100)
            new_value = caget("id_ioc:Energy", use_monitor=False)
        assert new_value == 100.0
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
