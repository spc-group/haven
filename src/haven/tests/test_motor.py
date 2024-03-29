from haven.instrument import motor


def test_load_vme_motors(sim_registry, mocker):
    # Mock the caget calls used to get the motor name
    mocked_caget = mocker.patch.object(motor, "caget")
    mocked_caget.side_effect = ["SLT V Upper", "SLT V Lower", "SLT H Inbound"]
    # Load the Ophyd motor definitions
    motor.load_all_motors()
    # Were the motors imported correctly
    motors = list(sim_registry.findall(label="motors"))
    assert len(motors) == 3
    # assert type(motors[0]) is motor.HavenMotor
    motor_names = [m.name for m in motors]
    assert "SLT V Upper" in motor_names
    assert "SLT V Lower" in motor_names
    assert "SLT H Inbound" in motor_names
    # Check that the IOC name is set in labels
    motor1 = sim_registry.find(name="SLT V Upper")
    assert "VME_crate" in motor1._ophyd_labels_


def test_skip_existing_motors(sim_registry, mocker):
    """If a motor already exists from another device, don't add it to the
    motors group.

    """
    # Create an existing fake motor
    m1 = motor.HavenMotor(
        "255idVME:m1", name="kb_mirrors_horiz_upstream", labels={"motors"}
    )
    sim_registry.register(m1)
    # Mock the caget calls used to get the motor name
    mocked_caget = mocker.patch.object(motor, "caget")
    mocked_caget.side_effect = ["SLT V Upper", "SLT V Lower", "SLT H Inbound"]
    # Load the Ophyd motor definitions
    motor.load_all_motors()
    # Were the motors imported correctly
    motors = list(sim_registry.findall(label="motors"))
    assert len(motors) == 3
    # assert type(motors[0]) is motor.HavenMotor
    motor_names = [m.name for m in motors]
    assert "kb_mirrors_horiz_upstream" in motor_names
    assert "SLT V Upper" in motor_names
    assert "SLT V Lower" in motor_names
    # Check that the IOC name is set in labels
    motor1 = sim_registry.find(name="SLT V Upper")
    assert "VME_crate" in motor1._ophyd_labels_


def test_motor_signals():
    m = motor.HavenMotor("motor_ioc", name="test_motor")
    assert m.description.pvname == "motor_ioc.DESC"
    assert m.tweak_value.pvname == "motor_ioc.TWV"
    assert m.tweak_forward.pvname == "motor_ioc.TWF"
    assert m.tweak_reverse.pvname == "motor_ioc.TWR"
    assert m.soft_limit_violation.pvname == "motor_ioc.LVIO"


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
