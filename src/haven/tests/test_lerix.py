import time

import pytest
from ophyd.sim import instantiate_fake_device

from haven.devices import lerix

um_per_mm = 1000


def test_rowland_circle_forward():
    rowland = lerix.RowlandPositioner(
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
    rowland = instantiate_fake_device(
        lerix.RowlandPositioner,
        name="rowland",
        x_motor_pv="",
        y_motor_pv="",
        z_motor_pv="",
        z1_motor_pv="",
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


def test_rowland_circle_component():
    device = instantiate_fake_device(
        lerix.LERIXSpectrometer, prefix="255idVME", name="lerix"
    )
    device.rowland.x.user_setpoint._use_limits = False
    device.rowland.y.user_setpoint._use_limits = False
    device.rowland.z.user_setpoint._use_limits = False
    device.rowland.z1.user_setpoint._use_limits = False
    # Set pseudo axes
    statuses = [
        device.rowland.D.set(500.0),
        device.rowland.theta.set(60.0),
        device.rowland.alpha.set(30.0),
    ]
    # [s.wait() for s in statuses]  # <- this should work, need to come back to it
    time.sleep(0.1)
    # Check that the virtual axes were set
    result = device.rowland.get(use_monitor=False)
    assert result.x.user_setpoint == pytest.approx(500.0 * um_per_mm)
    assert result.y.user_setpoint == pytest.approx(375.0 * um_per_mm)
    assert result.z.user_setpoint == pytest.approx(216.50635094610968 * um_per_mm)
    assert result.z1.user_setpoint == pytest.approx(1.5308084989341912e-14 * um_per_mm)


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2023, UChicago Argonne, LLC
#
# Distributed under the terms of the 3-Clause BSD License
#
# The full license is in the file LICENSE, distributed with this software.
#
# DISCLAIMER
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# -----------------------------------------------------------------------------
