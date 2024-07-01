from unittest import mock

import pytest

from firefly.slits import SlitsDisplay


@pytest.fixture()
def display(qtbot, blade_slits):
    disp = SlitsDisplay(macros={"DEVICE": blade_slits.name})
    qtbot.addWidget(disp)
    return disp


def test_blade_slit_caqtdm(display, blade_slits):
    display._open_caqtdm_subprocess = mock.MagicMock()
    # Launch the caqtdm display
    display.launch_caqtdm()
    assert display._open_caqtdm_subprocess.called
    cmds = display._open_caqtdm_subprocess.call_args[0][0]
    # Check that the right macros are sent
    macros = [cmds[i + 1] for i in range(len(cmds)) if cmds[i] == "-macro"][0]
    assert "P=255idc:" in macros
    assert "SLIT=KB_slits" in macros
    assert "H=KB_slitsH" in macros
    assert "V=KB_slitsV" in macros
    # Check that the right UI file is being used
    ui_file = cmds[-1]
    assert ui_file.split("/")[-1] == "4slitGraphic.ui"


def test_aperture_slit_caqtdm(display, aperture_slits):
    display._open_caqtdm_subprocess = mock.MagicMock()
    display.device = aperture_slits
    # Launch the caqtdm display
    display.launch_caqtdm()
    assert display._open_caqtdm_subprocess.called
    cmds = display._open_caqtdm_subprocess.call_args[0][0]
    # Check that the right macros are sent
    macros = [cmds[i + 1] for i in range(len(cmds)) if cmds[i] == "-macro"][0]
    assert "P=255ida:slits:" in macros
    assert "SLITS=US" in macros
    assert "HOR=m1" in macros
    assert "DIAG=m2" in macros
    assert "PITCH=m3" in macros
    assert "YAW=m4" in macros
    # Check that the right UI file is being used
    ui_file = cmds[-1]
    assert ui_file.split("/")[-1] == "maskApertureSlit.ui"
    # To-do: get the remaining macros for caQtDM
    # Full command should be:
    # /net/s25data/xorApps/epics/synApps_6_2/ioc/25ida/25idaApp/op/ui/maskApertureSlit.ui
    # macro: P=25ida:slits:,SLITS=US,HOR=m1,DIAG=m2,PITCH=m3,YAW=m4


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
