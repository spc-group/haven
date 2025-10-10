import pytest

from haven.devices.motor import Motor, load_motors
from haven.devices.undulator import TrajectoryMotorInfo


@pytest.fixture()
async def motor():
    m = Motor("motor_ioc", name="test_motor")
    await m.connect(mock=True)
    return m


def test_async_motor_signals(motor):
    assert motor.description.source == "mock+ca://motor_ioc.DESC"
    assert motor.motor_is_moving.source == "mock+ca://motor_ioc.MOVN"
    assert motor.motor_done_move.source == "mock+ca://motor_ioc.DMOV"
    assert motor.high_limit_switch.source == "mock+ca://motor_ioc.HLS"
    assert motor.low_limit_switch.source == "mock+ca://motor_ioc.LLS"
    assert motor.high_limit_travel.source == "mock+ca://motor_ioc.HLM"
    assert motor.low_limit_travel.source == "mock+ca://motor_ioc.LLM"
    assert motor.direction_of_travel.source == "mock+ca://motor_ioc.TDIR"
    assert motor.soft_limit_violation.source == "mock+ca://motor_ioc.LVIO"


def test_load_motors():
    m1, m2 = load_motors(m1="255idcVME:m1", m2="255idcVME:m2")
    assert m1.user_readback.source == "ca://255idcVME:m1.RBV"
    assert m2.user_readback.source == "ca://255idcVME:m2.RBV"


async def test_description_field_updates(motor):
    """Do the EPICS .DESC fields get set to the device name?"""
    assert (await motor.description.get_value()) == "test_motor"


async def test_prepare_trajectory(motor):
    """We should be able to prepare a trajectory scan, but have it just be a normal scan really."""
    tinfo = TrajectoryMotorInfo(positions=[], times=[])
    await motor.prepare(tinfo)


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
