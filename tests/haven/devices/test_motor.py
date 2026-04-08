import pytest

from haven.devices.motor import Motor, load_motors, short_name
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


names = [
    ("aerotech-horizontal", "AerotechH"),
    ("camera-upstream", "CamUS"),
    ("secondary_mono-bragg", "SecMonoBragg"),
    ("downstream_table-upstream", "DSTableUS"),
    ("sample_wheel", "SamWheel"),
    ("DXAFS_detector_horizontal", "DxafsDetH"),
    ("beryllium_lens_rotation", "BeLensRot"),
    # Other candidates:
    # Slt Top
    # Slt Bottom
    # Slt_OutB
    # Slt InB
    # kb_upstream-horiz-downstream
    # kb_upstream-horiz-upstream
    # kb_upstream-vert-downstream
    # kb_upstream-vert-upstream
    # upstream_table-horizontal
    # upstream_table-vertical
    # cam_V
    # cam_H
    # cam_in_out
    # motor 14
    # motor 15
    # det_ge_in_out
    # sam_beam
    # polyCrys_bend
    # I0_H
    # I0_V
    # sam_inout_ADC
    # sam_vert_ADC
    # sam_beam_ADC
    # Si_rot
    # split_ion_chamber_H
    # split_ion_chamber_V
    # DXAS_detHoriz
    # lensRot
    # lens_V
    # lens_H
    # sam_chi
    # polyCrys_horiz
    # secondary_mono-bragg
    # sam_wheel
    # polyCrys_horiz
    # polyCrys_rot
    # ion_V
    # foil_wheel
    # polyCrys_vert
    # bad for NO
    # downstream_table-horizontal
    # downstream_table-upstream
    # downstream_table-downstream
    # I0_V_Cds
    # Slt Top Cds
    # Slt OutB Cds
    # Slt InB Cds
    # Slt Bottom Cds
    # kb_downstream-horiz-downstream
    # kb_downstream-horiz-upstream
    # kb_downstream-horiz-bender_downstream
    # kb_downstream-horiz-bender_upstream
    # kb_downstream-vert-bender_downstream
    # kb_downstream-vert-bender_upstream
    # kb_downstream-vert-downstream
    # kb_downstream-vert-upstream
    # sam_h_cds
    # sam_beam_cds
    # sam_v_cds
    # I0_H_Cds
    # mini_vertical
    # mini_beam
    # DXAS_detHoriz
]


@pytest.mark.parametrize("full,short", names)
def test_short_name(full: str, short: str):
    assert short_name(full) == short


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
