import time

from epics import caget

from haven.instrument.lerix import (
    RowlandPositioner,
    LERIXSpectrometer,
    load_lerix_spectrometers,
)
import haven


def test_rowland_circle_forward():
    rowland = RowlandPositioner(
        name="rowland", x_motor_pv="", y_motor_pv="", z_motor_pv="", z1_motor_pv=""
    )
    # Check one set of values
    result = rowland.forward(500, 60.0, 30.0)
    assert result == (
        500.0,  # x
        375.0,  # y
        216.50635094610968,  # z
        1.5308084989341912e-14,  # z1
    )
    # Check one set of values
    result = rowland.forward(500, 80.0, 0.0)
    assert result == (
        484.92315519647707,  # x
        0.0,  # y
        171.0100716628344,  # z
        85.5050358314172,  # z1
    )
    # Check one set of values
    result = rowland.forward(500, 70.0, 10.0)
    assert result == (
        484.92315519647707,  # x
        109.92315519647711,  # y
        291.6982175363274,  # z
        75.19186659021767,  # z1
    )
    # Check one set of values
    result = rowland.forward(500, 75.0, 15.0)
    assert result == (
        500.0,  # x
        124.99999999999994,  # y
        216.50635094610965,  # z
        2.6514380968122676e-14,  # z1
    )
    # Check one set of values
    result = rowland.forward(500, 71.0, 10.0)
    assert result == (
        487.7641290737884,  # x
        105.28431301548724,  # y
        280.42235703910393,  # z
        68.41033299999741,  # z1
    )


def test_rowland_circle_component(ioc_motor):
    lerix = LERIXSpectrometer(name="lerix")
    lerix.wait_for_connection()
    # Set pseudo axes
    statuses = [
        lerix.rowland.D.set(500.0),
        lerix.rowland.theta.set(60.0),
        lerix.rowland.alpha.set(30.0),
    ]
    # [s.wait() for s in statuses]  # <- this should work, need to come back to it
    time.sleep(0.1)
    # Check that the virtual axes were set
    result = lerix.rowland.get(use_monitor=False)
    assert caget("vme_crate_ioc:m1") == 500.0
    assert result.x.user_readback == 500.0
    assert caget("vme_crate_ioc:m2") == 375.0
    assert result.y.user_readback == 375.0
    assert caget("vme_crate_ioc:m3") == 216.50635094610968
    assert result.z.user_readback == 216.50635094610968
    assert caget("vme_crate_ioc:m4") == 1.5308084989341912e-14
    assert result.z1.user_readback == 1.5308084989341912e-14


def test_load_lerix_spectrometers(sim_registry):
    load_lerix_spectrometers()
    lerix = sim_registry.find(name="lerix")
    assert lerix.name == "lerix"
    assert lerix.x.prefix == "vme_crate_ioc:m1"
    assert lerix.y.prefix == "vme_crate_ioc:m2"
    assert lerix.z.prefix == "vme_crate_ioc:m3"
    assert lerix.z1.prefix == "vme_crate_ioc:m4"