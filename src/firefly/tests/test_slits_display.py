from unittest import mock

import pytest

from firefly.slits import SlitsDisplay


@pytest.fixture()
def display(ffapp, blade_slits):
    disp = SlitsDisplay(macros={"DEVICE": blade_slits.name})
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
    # Check that the right UI file is being used
    ui_file = cmds[-1]
    assert ui_file.split("/")[-1] == "maskApertureSlit.ui"
    
