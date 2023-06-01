import time

from epics import caget
import pytest

from haven.instrument.lerix import (
    RowlandPositioner,
    LERIXSpectrometer,
    load_lerix_spectrometers,
)
import haven


um_per_mm = 1000


def test_rowland_circle_forward():
    rowland = RowlandPositioner(
        name="rowland", x_motor_pv="", y_motor_pv="", z_motor_pv="", z1_motor_pv=""
    )
    # Check one set of values
    um_per_mm
    result = rowland.forward(500, 60.0, 30.0)
    assert result == pytest.approx(
        (
            500.0 * um_per_mm,  # x
            375.0 * um_per_mm,  # y
            216.50635094610968 * um_per_mm,  # z
            1.5308084989341912e-14 * um_per_mm,  # z1
        )
    )
    # Check one set of values
    result = rowland.forward(500, 80.0, 0.0)
    assert result == pytest.approx(
        (
            484.92315519647707 * um_per_mm,  # x
            0.0 * um_per_mm,  # y
            171.0100716628344 * um_per_mm,  # z
            85.5050358314172 * um_per_mm,  # z1
        )
    )
    # Check one set of values
    result = rowland.forward(500, 70.0, 10.0)
    assert result == pytest.approx(
        (
            484.92315519647707 * um_per_mm,  # x
            109.92315519647711 * um_per_mm,  # y
            291.6982175363274 * um_per_mm,  # z
            75.19186659021767 * um_per_mm,  # z1
        )
    )
    # Check one set of values
    result = rowland.forward(500, 75.0, 15.0)
    assert result == pytest.approx(
        (
            500.0 * um_per_mm,  # x
            124.99999999999994 * um_per_mm,  # y
            216.50635094610965 * um_per_mm,  # z
            2.6514380968122676e-14 * um_per_mm,  # z1
        )
    )
    # Check one set of values
    result = rowland.forward(500, 71.0, 10.0)
    assert result == pytest.approx(
        (
            487.7641290737884 * um_per_mm,  # x
            105.28431301548724 * um_per_mm,  # y
            280.42235703910393 * um_per_mm,  # z
            68.41033299999741 * um_per_mm,  # z1
        )
    )


@pytest.mark.xfail
def test_rowland_circle_inverse():
    rowland = RowlandPositioner(
        name="rowland", x_motor_pv="", y_motor_pv="", z_motor_pv="", z1_motor_pv=""
    )
    # Check one set of values
    result = rowland.inverse(
        x=500.0,  # x
        y=375.0,  # y
        z=216.50635094610968,  # z
        z1=1.5308084989341912e-14,  # z1
    )
    assert result == pytest.approx((500, 60, 30))
    # # Check one set of values
    # result = rowland.forward(500, 80.0, 0.0)
    # assert result == pytest.approx((
    #     484.92315519647707 * um_per_mm,  # x
    #     0.0 * um_per_mm,  # y
    #     171.0100716628344 * um_per_mm,  # z
    #     85.5050358314172 * um_per_mm,  # z1
    # ))
    # # Check one set of values
    # result = rowland.forward(500, 70.0, 10.0)
    # assert result == pytest.approx((
    #     484.92315519647707 * um_per_mm,  # x
    #     109.92315519647711 * um_per_mm,  # y
    #     291.6982175363274 * um_per_mm,  # z
    #     75.19186659021767 * um_per_mm,  # z1
    # ))
    # # Check one set of values
    # result = rowland.forward(500, 75.0, 15.0)
    # assert result == pytest.approx((
    #     500.0 * um_per_mm,  # x
    #     124.99999999999994 * um_per_mm,  # y
    #     216.50635094610965 * um_per_mm,  # z
    #     2.6514380968122676e-14 * um_per_mm,  # z1
    # ))
    # # Check one set of values
    # result = rowland.forward(500, 71.0, 10.0)
    # assert result == pytest.approx((
    #     487.7641290737884 * um_per_mm,  # x
    #     105.28431301548724 * um_per_mm,  # y
    #     280.42235703910393 * um_per_mm,  # z
    #     68.41033299999741 * um_per_mm,  # z1
    # ))


@pytest.mark.xfail
def test_rowland_circle_component(ioc_motor):
    lerix = LERIXSpectrometer("255idVME", name="lerix")
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
    assert caget("255idVME:m1") == pytest.approx(500.0 * um_per_mm)
    assert result.x.user_readback == pytest.approx(500.0 * um_per_mm)
    assert caget("255idVME:m2") == pytest.approx(375.0 * um_per_mm)
    assert result.y.user_readback == pytest.approx(375.0 * um_per_mm)
    assert caget("255idVME:m3") == pytest.approx(216.50635094610968 * um_per_mm)
    assert result.z.user_readback == pytest.approx(216.50635094610968 * um_per_mm)
    assert caget("255idVME:m4") == pytest.approx(1.5308084989341912e-14 * um_per_mm)
    assert result.z1.user_readback == pytest.approx(1.5308084989341912e-14 * um_per_mm)


def test_load_lerix_spectrometers(sim_registry):
    load_lerix_spectrometers()
    lerix = sim_registry.find(name="lerix")
    assert lerix.name == "lerix"
    assert lerix.x.prefix == "255idVME:m1"
    assert lerix.y.prefix == "255idVME:m2"
    assert lerix.z.prefix == "255idVME:m3"
    assert lerix.z1.prefix == "255idVME:m4"
