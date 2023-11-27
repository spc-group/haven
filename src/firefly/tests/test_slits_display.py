from unittest import mock
import pytest

from firefly.slits import SlitsDisplay


@pytest.fixture()
def display(ffapp, slits):
    disp = SlitsDisplay(macros={"DEVICE": slits.name})
    return disp


def test_slit_caqtdm(display, slits):
    display._open_caqtdm_subprocess = mock.MagicMock()
    # Launch the caqtdm display
    display.launch_caqtdm()
    assert display._open_caqtdm_subprocess.called
    # Check that the right macros are sent
    cmds = display._open_caqtdm_subprocess.call_args[0][0]
    macros = [cmds[i+1] for i in range(len(cmds)) if cmds[i] == "-macro"][0]
    assert macros == 'P=255idc:,SLIT=KB_slits,H=KB_slitsH,V=KB_slitsV'
