from collections import OrderedDict

import pytest
from ophyd.sim import instantiate_fake_device
from ophyd.flyers import FlyerInterface
from ophyd import StatusBase
import numpy as np

from haven.instrument.motor import HavenMotor, load_motors


@pytest.fixture()
def mocked_device_names(mocker):
    # Mock the caget calls used to get the motor name
    async def resolve_device_names(defns):
        for defn, name in zip(defns, ["SLT V Upper", "SLT V Lower", "SLT H Inbound"]):
            defn["name"] = name

    mocker.patch(
        "haven.instrument.motor.resolve_device_names", new=resolve_device_names
    )


@pytest.fixture()
def motor(sim_registry):
    m1 = instantiate_fake_device(HavenMotor, name="m1")
    m1.user_setpoint._use_limits = False
    return m1


def test_load_vme_motors(sim_registry, mocked_device_names):
    # Load the Ophyd motor definitions
    load_motors()
    # Were the motors imported correctly
    motors = list(sim_registry.findall(label="motors"))
    assert len(motors) == 3
    # assert type(motors[0]) is HavenMotor
    motor_names = [m.name for m in motors]
    assert "SLT_V_Upper" in motor_names
    assert "SLT_V_Lower" in motor_names
    assert "SLT_H_Inbound" in motor_names
    # Check that the IOC name is set in labels
    motor1 = sim_registry.find(name="SLT_V_Upper")
    assert "VME_crate" in motor1._ophyd_labels_


def test_skip_existing_motors(sim_registry, mocked_device_names):
    """If a motor already exists from another device, don't add it to the
    motors group.

    """
    # Create an existing fake motor
    m1 = HavenMotor(
        "255idVME:m1", name="kb_mirrors_horiz_upstream", labels={"motors"}
    )
    # Load the Ophyd motor definitions
    load_motors()
    # Were the motors imported correctly
    motors = list(sim_registry.findall(label="motors"))
    print([m.prefix for m in motors])
    assert len(motors) == 3
    motor_names = [m.name for m in motors]
    assert "kb_mirrors_horiz_upstream" in motor_names
    assert "SLT_V_Upper" in motor_names
    assert "SLT_V_Lower" in motor_names
    # Check that the IOC name is set in labels
    motor1 = sim_registry.find(name="SLT_V_Upper")
    assert "VME_crate" in motor1._ophyd_labels_


def test_motor_signals():
    m = HavenMotor("motor_ioc", name="test_motor")
    assert m.description.pvname == "motor_ioc.DESC"
    assert m.tweak_value.pvname == "motor_ioc.TWV"
    assert m.tweak_forward.pvname == "motor_ioc.TWF"
    assert m.tweak_reverse.pvname == "motor_ioc.TWR"
    assert m.soft_limit_violation.pvname == "motor_ioc.LVIO"


def test_motor_flyer(motor):
    """Check that the haven motor implements the flyer interface."""
    assert motor is not None
    assert isinstance(motor, FlyerInterface)


def test_fly_params_forward(motor):
    """Test that the fly-scan parameters are correct when going from
    lower to higher positions.

    """
    # Set some example positions
    motor.motor_egu.set("micron").wait(timeout=3)
    motor.acceleration.set(0.5).wait(timeout=3)  # sec
    motor.start_position.set(10.).wait(timeout=3)  # µm
    motor.end_position.set(20.).wait(timeout=3)  # µm
    motor.encoder_resolution.set(0.001).wait(timeout=3)  # µm
    motor.flyer_num_points.set(101).wait(timeout=3)  # µm
    motor.flyer_dwell_time.set(1).wait(timeout=3)  # sec

    # Check that the fly-scan parameters were calculated correctly
    assert motor.slew_speed.get(use_monitor=False) == pytest.approx(0.1)  # µm/sec
    assert motor.taxi_start.get(use_monitor=False) == pytest.approx(9.9125)  # µm
    assert motor.taxi_end.get(use_monitor=False) == pytest.approx(20.0875)  # µm
    i = 10.
    pixel = []
    while i <= 20.005:
        pixel.append(i)
        i = i + 0.1
    np.testing.assert_allclose(motor.pixel_positions, pixel)


def test_fly_params_reverse(motor):
    """Test that the fly-scan parameters are correct when going from
    higher to lower positions.

    """
    # Set some example positions
    motor.motor_egu.set("micron").wait(timeout=3)
    motor.acceleration.set(0.5).wait(timeout=3)  # sec
    motor.start_position.set(20.0).wait(timeout=3)  # µm
    motor.end_position.set(10.0).wait(timeout=3)  # µm
    motor.flyer_num_points.set(101).wait(timeout=3)  # µm
    motor.flyer_dwell_time.set(1).wait(timeout=3)  # sec

    # Check that the fly-scan parameters were calculated correctly
    assert motor.slew_speed.get(use_monitor=False) == pytest.approx(0.1)  # µm/sec
    assert motor.taxi_start.get(use_monitor=False) == pytest.approx(20.0875)  # µm
    assert motor.taxi_end.get(use_monitor=False) == pytest.approx(9.9125)  # µm
    i = 20.0
    pixel = []
    while i >= 9.995:
        pixel.append(i)
        i = i - 0.1
    np.testing.assert_allclose(motor.pixel_positions, pixel)


def test_kickoff(motor):
    motor.flyer_dwell_time.set(1.0).wait(timeout=3)
    # Start flying
    status = motor.kickoff()
    # Check status behavior matches flyer interface
    assert isinstance(status, StatusBase)
    # Make sure the motor moved to its taxi position
    assert motor.user_setpoint.get() == motor.taxi_start


def test_complete(motor):
    # Set up fake flyer with mocked fly method
    assert motor.user_setpoint.get() == 0
    motor.taxi_end.set(10).wait(timeout=3)
    # Complete flying
    status = motor.complete()
    # Check that the motor was moved
    assert isinstance(status, StatusBase)
    assert motor.user_setpoint.get() == 10


def test_collect(motor):
    # Set up needed parameters
    motor.pixel_positions = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    # Set up some fake positions from camonitors
    motor._fly_data = [
        # timestamp, position
        (1.125, 0.5),
        (2.125, 1.5),
        (3.125, 2.5),
        (4.125, 3.5),
        (5.125, 4.5),
        (6.125, 5.5),
        (7.125, 6.5),
        (8.125, 7.5),
        (9.125, 8.5),
        (10.125, 9.5),
        (11.125, 10.5),
    ]
    expected_timestamps = [
        1.625,
        2.625,
        3.625,
        4.625,
        5.625,
        6.625,
        7.625,
        8.625,
        9.625,
        10.625,
    ]
    payload = list(motor.collect())
    # Confirm data have the right structure
    for datum, value, timestamp in zip(
        payload, motor.pixel_positions, expected_timestamps
    ):
        assert datum['data'] == {
            "m1": value,
            "m1_user_setpoint": value,
        }
        assert datum["timestamps"]['m1'] == pytest.approx(timestamp, abs=0.3)
        assert datum["time"] == pytest.approx(timestamp, abs=0.3)


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
