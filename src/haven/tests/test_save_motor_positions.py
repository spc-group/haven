import datetime as dt
import logging
import re
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pandas as pd
import pytest
import time_machine
from ophyd_async.testing import set_mock_value
from pytest_httpx import IteratorStream
from tiled.serialization.table import serialize_arrow

from haven.devices import Motor
from haven.motor_position import (
    get_motor_position,
    get_motor_positions,
    list_current_motor_positions,
    list_motor_positions,
    recall_motor_position,
    save_motor_position,
)

log = logging.getLogger(__name__)

# Use a timezone we're not likely to be in for testing tz-aware behavior
fake_time = dt.datetime(2022, 8, 19, 19, 10, 51, tzinfo=ZoneInfo("Asia/Taipei"))


scan1_metadata = {
    "id": "scan1",
    "attributes": {
        "metadata": {
            "start": {
                "plan_name": "save_motor_position",
                "position_name": "Good position A",
                "uid": "scan1",
                "time": 1725897133,
            }
        }
    },
}


scan2_metadata = {
    "id": "scan2",
    "attributes": {
        "metadata": {
            "start": {
                "plan_name": "save_motor_position",
                "position_name": "Good position B",
                "uid": "scan2",
                "time": 150,
            }
        }
    },
}


@pytest.fixture()
def tiled_api(httpx_mock):
    httpx_mock.add_response(
        url=re.compile("^http://localhost:8000/api/v1/search/testing/"),
        json={
            "data": [scan1_metadata, scan2_metadata],
            "links": {"next": None},
        },
        is_optional=True,
    )
    httpx_mock.add_response(
        url=re.compile(
            "^http://localhost:8000/api/v1/metadata/testing%2Fscan[0-9]%2Fstreams%2Fprimary$"
        ),
        json={
            "data": {
                "attributes": {
                    "metadata": {
                        "data_keys": {
                            "motor_A": {"object_name": "motor_A"},
                            "motor_B": {"object_name": "motor_B"},
                        },
                    },
                },
            },
        },
        is_reusable=True,
    )
    httpx_mock.add_response(
        url=re.compile(
            "^http://localhost:8000/api/v1/metadata/testing%2Fscan[1-2]%2Fstreams%2Fprimary%2Finternal$"
        ),
        json={
            "data": {
                "attributes": {
                    "structure_family": "table",
                },
            },
        },
        is_reusable=True,
    )
    httpx_mock.add_response(
        url=re.compile(
            "^http://localhost:8000/api/v1/table/full/testing%2Fscan[1-2]%2Fstreams%2Fprimary%2Finternal$"
        ),
        stream=IteratorStream(
            [
                serialize_arrow(
                    pd.DataFrame(
                        {
                            "motor_A": [12.0],
                            "motor_B": [-113.25],
                        }
                    ),
                    metadata={},
                )
            ]
        ),
        is_reusable=True,
    )
    httpx_mock.add_response(
        url="http://localhost:8000/api/v1/metadata/testing%2Fscan1",
        json={"data": scan1_metadata},
        is_optional=True,
    )


@pytest.fixture
async def motors(sim_registry):
    # Create the motors
    motors = [
        Motor("", name="motor_A"),
        Motor("", name="motor_B"),
    ]
    for motor in motors:
        await motor.connect(mock=True)
        sim_registry.register(motor)
    return motors


def test_save_motor_position_by_device(motors):
    # Move to some other motor position so we can tell it saved the right one
    motorA, motorB = motors
    # Save the current motor position
    plan = save_motor_position(motorA, motorB, name="Sample center")
    # Check that the right read messages get emitted
    messages = list(plan)
    # Check that the motors got saved
    readA, readB = messages[6:8]
    assert readA.obj is motorA
    assert readB.obj is motorB


def test_save_motor_position_by_name(motors):
    # Check that no entry exists before saving it
    motorA, motorB = motors
    # Save the current motor position
    plan = save_motor_position(motorA.name, motorB.name, name="Sample center")
    # Check that the motors got saved
    # Check that the right read messages get emitted
    messages = list(plan)
    # Check that the motors got saved
    readA, readB = messages[6:8]
    assert readA.obj is motorA
    assert readB.obj is motorB


async def test_get_motor_position(tiled_api):
    uid = "scan1"
    result = await get_motor_position(uid=uid)
    assert result.name == "Good position A"
    assert result.motors[0].name == "motor_A"
    assert result.motors[0].readback == 12.0


async def test_get_motor_positions(tiled_api):
    results = get_motor_positions(after=1725897100, before=1725897200)
    results = [pos async for pos in results]
    assert len(results) == 2
    # Check the motor position details
    motorA, motorB = results
    assert motorA.uid == "scan1"


async def test_get_motor_positions_by_name(tiled_api):
    results = get_motor_positions(name=r"^.*good.+itio.+[AB]$", case_sensitive=False)
    results = [pos async for pos in results]
    assert len(results) == 2
    # Check the motor position details
    motorA, motorB = results
    assert motorA.uid == "scan1"


async def test_recall_motor_position(tiled_api, motors):
    # Re-set the previous value
    uid = "scan1"
    plan = recall_motor_position(uid=uid)
    wf_message = next(plan)
    assert wf_message.command == "wait_for"
    # Inject a valid motor position back in to mock the wait_for plan
    position = await get_motor_position(uid)
    task = MagicMock()
    task.result.return_value = position
    next_msg = plan.send((task,))
    messages = [next_msg, *plan]
    # Check the plan output
    msg0 = messages[0]
    assert msg0.obj.name == "motor_A"
    assert msg0.args[0] == 12.0
    msg1 = messages[1]
    assert msg1.obj.name == "motor_B"
    assert msg1.args[0] == -113.25


@time_machine.travel(fake_time, tick=True)
async def test_list_motor_positions(tiled_api, capsys):
    # Do the listing
    await list_motor_positions()
    # Check stdout for printed motor positions
    captured = capsys.readouterr()
    assert len(captured.out) > 0
    first_motor = captured.out.split("\n\n")[0]
    uid = "scan1"
    timestamp = "2024-09-09 23:52:13"
    expected = "\n".join(
        [
            f"Good position A",
            f'┃ uid="{uid}", {timestamp}',
            f"┣━motor_A: 12.0, offset: None",
            f"┗━motor_B: -113.25, offset: None",
        ]
    )
    # print(first_motor)
    # print("===")
    # print(expected)
    assert first_motor == expected


@time_machine.travel(fake_time, tick=True)
async def test_list_current_motor_positions(motors, capsys):
    # Get our simulated motors into the device registry
    motorA, motorB = motors
    with capsys.disabled():
        # Move to some other motor position so we can tell it saved the right one
        set_mock_value(motorA.user_readback, 11.0)
        set_mock_value(motorA.offset, 1.5)
        set_mock_value(motorB.user_readback, 23.0)
    # List the current motor position
    await list_current_motor_positions(motorA, motorB, name="Current motor positions")
    # Check stdout for printed motor positions
    captured = capsys.readouterr()
    assert len(captured.out) > 0
    timestamp = "2022-08-19 19:10:51"
    expected = "\n".join(
        [
            f"Current motor positions",
            f"┃ {timestamp}",
            f"┣━motor_A: 11.0, offset: 1.5",
            f"┗━motor_B: 23.0, offset: 0.0",
        ]
    )
    assert captured.out.strip("\n") == expected.strip("\n")


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
