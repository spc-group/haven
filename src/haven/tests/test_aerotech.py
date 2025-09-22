import asyncio
from collections import OrderedDict

import numpy as np
import pytest
from ophyd_async.testing import get_mock_put, set_mock_value

from haven.devices.aerotech import AerotechStage
from haven.plans._fly import FlyMotorInfo


@pytest.fixture()
async def aerotech():
    stage = AerotechStage(
        prefix="255idc",
        name="aerotech",
    )
    await stage.connect(mock=True)
    await asyncio.gather(
        stage.horizontal.velocity.set(5),
        stage.vertical.velocity.set(5),
    )
    return stage


@pytest.fixture()
def aerotech_axis(aerotech):
    m = aerotech.horizontal
    yield m


async def test_aerotech_signals(aerotech):
    reading = await aerotech.read()
    assert set(reading.keys()) == {
        "aerotech-vertical",
        "aerotech-horizontal",
    }
    config = await aerotech.read_configuration()
    assert set(config.keys()) == {
        "aerotech-horizontal-description",
        "aerotech-horizontal-motor_egu",
        "aerotech-horizontal-offset",
        "aerotech-horizontal-offset_dir",
        "aerotech-horizontal-velocity",
        "aerotech-vertical-description",
        "aerotech-vertical-motor_egu",
        "aerotech-vertical-offset",
        "aerotech-vertical-offset_dir",
        "aerotech-vertical-velocity",
        # Profile move parameters
        "aerotech-profile_move-point_count",
        "aerotech-profile_move-pulse_count",
        "aerotech-profile_move-move_mode",
        "aerotech-profile_move-pulse_range_start",
        "aerotech-profile_move-pulse_range_end",
        "aerotech-profile_move-time_mode",
        "aerotech-profile_move-dwell_time",
        "aerotech-profile_move-acceleration_time",
        "aerotech-profile_move-axis-0-enabled",
        "aerotech-profile_move-axis-0-positions",
        "aerotech-profile_move-axis-1-enabled",
        "aerotech-profile_move-axis-1-positions",
        "aerotech-profile_move-pulse_positions",
        # PSO parameters
        "aerotech-profile_move-pulse_mode",
        "aerotech-profile_move-pulse_direction",
        "aerotech-profile_move-pulse_length",
        "aerotech-profile_move-pulse_period",
        "aerotech-profile_move-pulse_source",
        "aerotech-profile_move-pulse_output",
        "aerotech-profile_move-pulse_axis",
    }


profile_positions = [
    # (start, stop, num, expected, direction)
    (-1000, 1000, 100, np.linspace(-1010, 1010, num=101), "Pos"),
    (1000, -1000, 100, np.linspace(1010, -1010, num=101), "Neg"),
]


@pytest.mark.parametrize("start,end,num,expected,direction", profile_positions)
async def test_prepare(aerotech, start, end, num, expected, direction):
    axis = aerotech.horizontal
    motor_info = FlyMotorInfo(
        start_position=start, end_position=end, time_for_move=120, point_count=num
    )
    # Set to busy to check the observe_value behavior
    set_mock_value(aerotech.profile_move.build_state, "Busy")
    # Prepare
    prepared = axis.prepare(motor_info)
    await asyncio.sleep(0.01)
    assert axis._fly_info is motor_info
    set_mock_value(aerotech.profile_move.build_status, "Success")
    set_mock_value(aerotech.profile_move.build_state, "Done")
    await prepared
    # Check that the aerotech profile move was setup properly
    get_mock_put(aerotech.profile_move.point_count).assert_called_once_with(
        101, wait=True
    )
    get_mock_put(aerotech.profile_move.pulse_count).assert_called_once_with(
        101, wait=True
    )
    get_mock_put(aerotech.profile_move.pulse_range_start).assert_called_once_with(
        0, wait=True
    )
    get_mock_put(aerotech.profile_move.pulse_range_end).assert_called_once_with(
        101, wait=True
    )
    get_mock_put(aerotech.profile_move.dwell_time).assert_called_once_with(
        1.2, wait=True
    )
    get_mock_put(aerotech.profile_move.pulse_direction).assert_called_once_with(
        direction, wait=True
    )
    get_mock_put(aerotech.profile_move.move_mode).assert_called_once_with(
        "Absolute", wait=True
    )
    get_mock_put(aerotech.profile_move.axis[0].enabled).assert_called_once_with(
        True, wait=True
    )
    get_mock_put(aerotech.profile_move.axis[1].enabled).assert_called_once_with(
        False, wait=True
    )
    mock_put = get_mock_put(aerotech.profile_move.axis[0].positions)
    assert mock_put.called
    assert np.all(mock_put.call_args.args[0] == expected)
    mock_put = get_mock_put(aerotech.profile_move.pulse_positions)
    assert mock_put.called
    assert np.all(mock_put.call_args.args[0] == expected)


async def test_prepare_build_failed(aerotech):
    """Check that prepare fails if the build does not succeed."""
    axis = aerotech.horizontal
    motor_info = FlyMotorInfo(
        start_position=-1000, end_position=1000, time_for_move=120, point_count=100
    )
    # Set to busy to check the observe_value behavior
    set_mock_value(aerotech.profile_move.build_state, "Busy")
    # Prepare
    prepared = axis.prepare(motor_info)
    await asyncio.sleep(0.01)
    set_mock_value(aerotech.profile_move.build_status, "Failure")
    set_mock_value(aerotech.profile_move.build_state, "Done")
    with pytest.raises(Exception):
        await prepared


async def test_kickoff(aerotech):
    axis = aerotech.horizontal
    motor_info = FlyMotorInfo(
        start_position=-1000, end_position=1000, time_for_move=120, point_count=100
    )
    set_mock_value(aerotech.profile_move.build_status, "Success")
    await axis.prepare(motor_info)
    # Start flying
    status = axis.kickoff()
    await asyncio.sleep(0.01)
    set_mock_value(aerotech.profile_move.execute_state, "Executing")
    await status


async def test_complete(aerotech):
    axis = aerotech.horizontal
    motor_info = FlyMotorInfo(
        start_position=-1000, end_position=1000, time_for_move=120, point_count=100
    )
    set_mock_value(aerotech.profile_move.build_status, "Success")
    await axis.prepare(motor_info)
    # Complete flying
    status = axis.complete()
    set_mock_value(aerotech.profile_move.execute_state, "Done")
    set_mock_value(aerotech.profile_move.execute_status, "Success")
    await status


async def test_complete_execute_failed(aerotech):
    axis = aerotech.horizontal
    # Start flying
    status = axis.complete()
    await asyncio.sleep(0.01)
    set_mock_value(aerotech.profile_move.execute_status, "Failure")
    with pytest.raises(RuntimeError):
        await status


@pytest.mark.skip(reason="Aerotech support needs to be re-written for new hardware")
def test_collect(aerotech_flyer):
    flyer = aerotech_flyer
    # Set up needed parameters
    flyer.pixel_positions = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    flyer.starttime = 0
    flyer.endtime = flyer.starttime + 11.25
    flyer.acceleration.put(0.5)  # µm/s^2
    flyer.flyer_end_position.put(0.1)
    flyer.flyer_num_points.put(2)  # µm
    flyer.flyer_dwell_time.put(1)  # sec
    expected_timestamps = [
        1.125,
        2.125,
        3.125,
        4.125,
        5.125,
        6.125,
        7.125,
        8.125,
        9.125,
        10.125,
    ]
    payload = list(flyer.collect())
    # Confirm data have the right structure
    for datum, value, timestamp in zip(
        payload, flyer.pixel_positions, expected_timestamps
    ):
        assert datum == {
            "data": {
                "aerotech_horiz": value,
                "aerotech_horiz_user_setpoint": value,
            },
            "timestamps": {
                "aerotech_horiz": timestamp,
                "aerotech_horiz_user_setpoint": timestamp,
            },
            "time": timestamp,
        }


@pytest.mark.skip(reason="Aerotech support needs to be re-written for new hardware")
def test_describe_collect(aerotech_flyer):
    expected = {
        "positions": OrderedDict(
            [
                (
                    "aerotech_horiz",
                    {
                        "source": "SIM:aerotech_horiz",
                        "dtype": "integer",
                        "shape": [],
                        "precision": 3,
                    },
                ),
                (
                    "aerotech_horiz_user_setpoint",
                    {
                        "source": "SIM:aerotech_horiz_user_setpoint",
                        "dtype": "integer",
                        "shape": [],
                        "precision": 3,
                    },
                ),
            ]
        )
    }

    assert aerotech_flyer.describe_collect() == expected


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
