from collections import OrderedDict
from unittest import mock

import numpy as np
import pytest
from ophyd import StatusBase

from haven import exceptions
from haven.devices.aerotech import AerotechMotor, AerotechStage, ureg


@pytest.fixture()
async def aerotech():
    stage = AerotechStage(
        horizontal_prefix="255idc:m1",
        vertical_prefix="255idc:m2",
        name="aerotech",
    )
    await stage.connect(mock=True)
    return stage


@pytest.fixture()
def aerotech_axis(aerotech):
    m = aerotech.horiz
    yield m


def test_aerotech_flyer(sim_registry):
    aeroflyer = AerotechMotor(
        prefix="255idc:m1", name="aerotech_flyer", axis="@0", encoder=6
    )
    assert aeroflyer is not None


async def test_aerotech_stage(sim_registry):
    fly_stage = AerotechStage(
        vertical_prefix="255idc:m1",
        horizontal_prefix="255idc:m2",
        name="aerotech",
    )
    assert fly_stage is not None
    # assert fly_stage.asyn.ascii_output.pvname == "motor_ioc:asynEns.AOUT"


@pytest.mark.skip(reason="Aerotech support needs to be re-written for new hardware")
def test_aerotech_fly_params_forward(aerotech_flyer):
    flyer = aerotech_flyer
    # Set some example positions
    flyer.motor_egu.put("micron")
    flyer.acceleration.put(0.5)  # sec
    flyer.encoder_resolution.put(0.001)  # µm
    flyer.flyer_start_position.put(10.0)  # µm
    flyer.flyer_end_position.put(20.0)  # µm
    flyer.flyer_num_points.put(101)  # µm
    flyer.flyer_dwell_time.put(1)  # sec

    # Check that the fly-scan parameters were calculated correctly
    assert flyer.pso_start.get(use_monitor=False) == 9.95
    assert flyer.pso_end.get(use_monitor=False) == 20.05
    assert flyer.flyer_slew_speed.get(use_monitor=False) == 0.1  # µm/sec
    assert flyer.flyer_taxi_start.get(use_monitor=False) == 9.85  # µm
    assert flyer.flyer_taxi_end.get(use_monitor=False) == pytest.approx(20.0875)  # µm
    assert flyer.encoder_step_size.get(use_monitor=False) == 100
    assert flyer.encoder_window_start.get(use_monitor=False) == -5
    assert flyer.encoder_window_end.get(use_monitor=False) == 10105
    i = 10.0
    pixel = []
    while i <= 20.03:
        pixel.append(i)
        i = i + 0.1
    np.testing.assert_allclose(flyer.pixel_positions, pixel)


@pytest.mark.skip(reason="Aerotech support needs to be re-written for new hardware")
def test_aerotech_fly_params_reverse(aerotech_flyer):
    flyer = aerotech_flyer
    # Set some example positions
    flyer.motor_egu.put("micron")
    flyer.acceleration.put(0.5)  # sec
    flyer.encoder_resolution.put(0.001)  # µm
    flyer.flyer_start_position.put(20.0)  # µm
    flyer.flyer_end_position.put(10.0)  # µm
    flyer.flyer_num_points.put(101)  # µm
    flyer.flyer_dwell_time.put(1)  # sec

    # Check that the fly-scan parameters were calculated correctly
    assert flyer.pso_start.get(use_monitor=False) == 20.05
    assert flyer.pso_end.get(use_monitor=False) == 9.95
    assert flyer.flyer_slew_speed.get(use_monitor=False) == 0.1  # µm/sec
    assert flyer.flyer_taxi_start.get(use_monitor=False) == pytest.approx(20.15)  # µm
    assert flyer.flyer_taxi_end.get(use_monitor=False) == 9.9125  # µm
    assert flyer.encoder_step_size.get(use_monitor=False) == 100
    assert flyer.encoder_window_start.get(use_monitor=False) == 5
    assert flyer.encoder_window_end.get(use_monitor=False) == -10105


@pytest.mark.skip(reason="Aerotech support needs to be re-written for new hardware")
def test_aerotech_fly_params_no_window(aerotech_flyer):
    """Test the fly scan params when the range is too large for the PSO window."""
    flyer = aerotech_flyer
    # Set some example positions
    flyer.motor_egu.put("micron")
    flyer.acceleration.put(0.5)  # sec
    flyer.encoder_resolution.put(0.001)  # µm
    flyer.flyer_start_position.put(0)  # µm
    flyer.flyer_end_position.put(9000)  # µm
    flyer.flyer_num_points.put(90001)  # µm
    flyer.flyer_dwell_time.put(1)  # sec

    # Check that the fly-scan parameters were calculated correctly
    assert flyer.pso_start.get(use_monitor=False) == -0.05
    assert flyer.pso_end.get(use_monitor=False) == 9000.05
    assert flyer.flyer_taxi_start.get(use_monitor=False) == pytest.approx(-0.15)  # µm
    assert flyer.flyer_taxi_end.get(use_monitor=False) == 9000.0875  # µm
    assert flyer.encoder_step_size.get(use_monitor=False) == 100
    assert flyer.encoder_window_start.get(use_monitor=False) == -5
    assert flyer.encoder_window_end.get(use_monitor=False) == 9000105
    assert flyer.encoder_use_window.get(use_monitor=False) is False


@pytest.mark.skip(reason="Aerotech support needs to be re-written for new hardware")
def test_aerotech_predicted_positions(aerotech_flyer):
    """Check that the fly-scan positions are calculated properly."""
    flyer = aerotech_flyer
    # Set some example positions
    flyer.motor_egu.put("micron")
    flyer.acceleration.put(0.5)  # sec
    flyer.encoder_resolution.put(0.001)  # µm
    flyer.flyer_start_position.put(10.05)  # µm
    flyer.flyer_end_position.put(19.95)  # µm
    flyer.flyer_num_points.put(100)  # µm
    flyer.flyer_dwell_time.put(1)  # sec

    # Check that the fly-scan parameters were calculated correctly
    i = 10.05
    pixel_positions = []
    while i <= 19.98:
        pixel_positions.append(i)
        i = i + 0.1
    num_pulses = len(pixel_positions) + 1
    pso_positions = np.linspace(10, 20, num=num_pulses)
    encoder_pso_positions = np.linspace(0, 10000, num=num_pulses)
    np.testing.assert_allclose(flyer.encoder_pso_positions, encoder_pso_positions)
    np.testing.assert_allclose(flyer.pso_positions, pso_positions)
    np.testing.assert_allclose(flyer.pixel_positions, pixel_positions)


@pytest.mark.skip(reason="Aerotech support needs to be re-written for new hardware")
def test_enable_pso(aerotech_flyer):
    flyer = aerotech_flyer
    # Set up scan parameters
    flyer.encoder_step_size.put(50)  # In encoder counts
    flyer.encoder_window_start.put(-5)  # In encoder counts
    flyer.encoder_window_end.put(10000)  # In encoder counts
    flyer.encoder_use_window.put(True)
    # Check that commands are sent to set up the controller for flying
    flyer.enable_pso()
    assert flyer.send_command.called
    commands = [c.args[0] for c in flyer.send_command.call_args_list]
    assert commands == [
        "PSOCONTROL @0 RESET",
        "PSOOUTPUT @0 CONTROL 1",
        "PSOPULSE @0 TIME 20, 10",
        "PSOOUTPUT @0 PULSE WINDOW MASK",
        "PSOTRACK @0 INPUT 6",
        "PSODISTANCE @0 FIXED 50",
        "PSOWINDOW @0 1 INPUT 6",
        "PSOWINDOW @0 1 RANGE -5,10000",
    ]


@pytest.mark.skip(reason="Aerotech support needs to be re-written for new hardware")
def test_enable_pso_no_window(aerotech_flyer):
    flyer = aerotech_flyer
    # Set up scan parameters
    flyer.encoder_step_size.put(50)  # In encoder counts
    flyer.encoder_window_start.put(-5)  # In encoder counts
    flyer.encoder_window_end.put(None)  # High end is outside the window range
    # Check that commands are sent to set up the controller for flying
    flyer.enable_pso()
    assert flyer.send_command.called
    commands = [c.args[0] for c in flyer.send_command.call_args_list]
    assert commands == [
        "PSOCONTROL @0 RESET",
        "PSOOUTPUT @0 CONTROL 1",
        "PSOPULSE @0 TIME 20, 10",
        "PSOOUTPUT @0 PULSE",
        "PSOTRACK @0 INPUT 6",
        "PSODISTANCE @0 FIXED 50",
        # "PSOWINDOW @0 1 INPUT 6",
        # "PSOWINDOW @0 1 RANGE -5,10000",
    ]


@pytest.mark.skip(reason="Aerotech support needs to be re-written for new hardware")
def test_pso_bad_window_forward(aerotech_flyer):
    """Check for an exception when the window is needed but not enabled.

    I.e. when the taxi distance is larger than the encoder step size."""
    flyer = aerotech_flyer
    # Set up scan parameters
    flyer.encoder_resolution.put(1)
    flyer.encoder_step_size.put(5 / flyer.encoder_resolution.get())  # In encoder counts
    flyer.encoder_window_start.put(-5)  # In encoder counts
    flyer.encoder_window_end.put(None)  # High end is outside the window range
    flyer.pso_end.put(100)
    flyer.flyer_taxi_end.put(110)
    # Check that commands are sent to set up the controller for flying
    with pytest.raises(exceptions.InvalidScanParameters):
        flyer.enable_pso()


@pytest.mark.skip(reason="Aerotech support needs to be re-written for new hardware")
def test_pso_bad_window_reverse(aerotech_flyer):
    """Check for an exception when the window is needed but not enabled.

    I.e. when the taxi distance is larger than the encoder step size."""
    flyer = aerotech_flyer
    # Set up scan parameters
    flyer.encoder_resolution.put(1)
    flyer.flyer_end_position.put(5)
    flyer.flyer_num_points.put(2)
    flyer.encoder_step_size.put(
        flyer.flyer_step_size() / flyer.encoder_resolution.get()
    )  # In encoder counts
    flyer.encoder_window_start.put(114)  # In encoder counts
    flyer.encoder_window_start.put(None)  # High end is outside the window range
    flyer.pso_start.put(100)
    flyer.flyer_taxi_start.put(94)
    # Check that commands are sent to set up the controller for flying
    with pytest.raises(exceptions.InvalidScanParameters):
        flyer.enable_pso()


@pytest.mark.skip(reason="Aerotech support needs to be re-written for new hardware")
def test_arm_pso(aerotech_flyer):
    flyer = aerotech_flyer
    assert not flyer.send_command.called
    flyer.arm_pso()
    assert flyer.send_command.called
    command = flyer.send_command.call_args.args[0]
    assert command == "PSOCONTROL @0 ARM"


@pytest.mark.skip(reason="Aerotech support needs to be re-written for new hardware")
def test_motor_units(aerotech_flyer):
    """Check that the motor and flyer handle enginering units properly."""
    flyer = aerotech_flyer
    flyer.motor_egu.put("micron")
    unit = flyer.motor_egu_pint
    assert unit == ureg("1e-6 m")


@pytest.mark.skip(reason="Aerotech support needs to be re-written for new hardware")
def test_kickoff(aerotech_flyer):
    # Set up fake flyer with mocked fly method
    flyer = aerotech_flyer
    flyer.taxi = mock.MagicMock()
    flyer.flyer_dwell_time.put(1.0)
    # Start flying
    status = flyer.kickoff()
    # Check status behavior matches flyer interface
    assert isinstance(status, StatusBase)
    assert not status.done
    # Start flying and see if the status is done
    flyer.ready_to_fly.put(True)
    status.wait()
    assert status.done
    assert type(flyer.starttime) == float


@pytest.mark.skip(reason="Aerotech support needs to be re-written for new hardware")
def test_complete(aerotech_flyer):
    # Set up fake flyer with mocked fly method
    flyer = aerotech_flyer
    flyer.move = mock.MagicMock()
    assert flyer.user_setpoint.get() == 0
    flyer.flyer_taxi_end.put(10)
    # Complete flying
    status = flyer.complete()
    # Check that the motor was moved
    assert flyer.move.called_with(9)
    # Check status behavior matches flyer interface
    assert isinstance(status, StatusBase)
    status.wait(timeout=1)
    assert status.done


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


@pytest.mark.skip(reason="Aerotech support needs to be re-written for new hardware")
def test_fly_motor_positions(aerotech_flyer):
    flyer = aerotech_flyer
    # Arbitrary rest position
    flyer.user_setpoint.put(255)
    flyer.parent.delay.channel_C.delay.sim_put(1.5)
    flyer.parent.delay.output_CD.polarity.sim_put(1)
    # Set example fly scan parameters
    flyer.flyer_taxi_start.put(5)
    flyer.flyer_start_position.put(10)
    flyer.pso_start.put(9.5)
    flyer.flyer_taxi_end.put(105)
    flyer.encoder_use_window.put(True)
    # Mock the motor position so that it returns a status we control
    motor_status = StatusBase()
    motor_status.set_finished()
    mover = mock.MagicMock(return_value=motor_status)
    flyer.move = mover
    # Check the fly scan moved the motors in the right order
    flyer.taxi()
    flyer.fly()
    assert mover.called
    positions = [c.args[0] for c in mover.call_args_list]
    assert len(positions) == 3
    pso_arm, taxi, end = positions
    assert pso_arm == 9.5
    assert taxi == 5
    assert end == 105
    # Check that the delay generator is properly configured
    assert flyer.parent.delay.channel_C.delay.get(use_monitor=False) == 0.0
    assert flyer.parent.delay.output_CD.polarity.get(use_monitor=False) == 0


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
