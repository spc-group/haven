from unittest.mock import AsyncMock

import pytest
from bluesky.protocols import Flyable

from haven.devices.motor import HavenMotor
from haven.devices.motor import Motor as AsyncMotor
from haven.devices.motor import load_motors


@pytest.fixture()
async def motor(sim_registry):
    motor = AsyncMotor("255idVME:m1", name="motor_1")
    await motor.connect(mock=True)
    return motor


@pytest.mark.asyncio
async def test_load_motors(sim_registry, monkeypatch):
    # Load the Ophyd motor definitions
    motors = load_motors(prefix="255idVME:", num_motors=3)
    # Were the motors imported correctly
    assert len(motors) == 3
    # assert type(motors[0]) is HavenMotor
    motor_names = [m.name for m in motors]
    assert "255idVME_m1" in motor_names
    assert "255idVME_m2" in motor_names
    assert "255idVME_m3" in motor_names
    # Check that the IOC name is set in labels
    motor1 = motors[0]
    assert "extra_motors" in motor1._ophyd_labels_


def test_motor_signals():
    m = HavenMotor("motor_ioc", name="test_motor")
    assert m.description.pvname == "motor_ioc.DESC"
    assert m.tweak_value.pvname == "motor_ioc.TWV"
    assert m.tweak_forward.pvname == "motor_ioc.TWF"
    assert m.tweak_reverse.pvname == "motor_ioc.TWR"
    assert m.soft_limit_violation.pvname == "motor_ioc.LVIO"


def test_async_motor_signals():
    m = AsyncMotor("motor_ioc", name="test_motor")
    assert m.description.source == "ca://motor_ioc.DESC"
    assert m.motor_is_moving.source == "ca://motor_ioc.MOVN"
    assert m.motor_done_move.source == "ca://motor_ioc.DMOV"
    assert m.high_limit_switch.source == "ca://motor_ioc.HLS"
    assert m.low_limit_switch.source == "ca://motor_ioc.LLS"
    assert m.high_limit_travel.source == "ca://motor_ioc.HLM"
    assert m.low_limit_travel.source == "ca://motor_ioc.LLM"
    assert m.direction_of_travel.source == "ca://motor_ioc.TDIR"
    assert m.soft_limit_violation.source == "ca://motor_ioc.LVIO"


def test_motor_flyer(motor):
    """Check that the haven motor implements the flyer interface."""
    assert motor is not None
    assert isinstance(motor, Flyable)


@pytest.mark.asyncio
async def test_auto_naming_default(monkeypatch):
    motor = AsyncMotor(prefix="255idVME:m1")
    monkeypatch.setattr(
        motor.description, "get_value", AsyncMock(return_value="motor_1")
    )
    await motor.connect(mock=True)
    assert motor.name == "motor_1"
    assert motor.user_setpoint.name == "motor_1-user_setpoint"


@pytest.mark.asyncio
async def test_auto_naming(monkeypatch):
    motor = AsyncMotor(prefix="255idVME:m1", name="not_the_final_name", auto_name=True)
    monkeypatch.setattr(
        motor.description, "get_value", AsyncMock(return_value="motor_1")
    )
    await motor.connect(mock=True)
    assert motor.name == "motor_1"
    assert motor.user_setpoint.name == "motor_1-user_setpoint"


@pytest.mark.asyncio
async def test_manual_naming(monkeypatch):
    motor = AsyncMotor(prefix="255idVME:m1", name="real_name", auto_name=False)
    await motor.connect(mock=True)
    assert motor.name == "real_name"
    assert motor.user_setpoint.name == "real_name-user_setpoint"


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
