from unittest import mock

import pytest
from ophyd.sim import make_fake_device

from haven.instrument.mirrors import KBMirrors
from firefly.kb_mirrors import KBMirrorsDisplay


@pytest.fixture()
def kb_mirrors(sim_registry):
    """A fake set of slits using the 4-blade setup."""
    FakeMirrors = make_fake_device(KBMirrors)
    kb = FakeMirrors(prefix="255idc:KB:", name="kb_mirrors", labels={"kb_mirrors"})
    sim_registry.register(kb)
    return kb


@pytest.fixture()
def display(ffapp, kb_mirrors):
    disp = KBMirrorsDisplay(macros={"DEVICE": kb_mirrors.name})
    return disp


def test_kb_mirrors_caqtdm(display, kb_mirrors):
    display._open_caqtdm_subprocess = mock.MagicMock()
    # Launch the caqtdm display
    display.launch_caqtdm()
    assert display._open_caqtdm_subprocess.called
    cmds = display._open_caqtdm_subprocess.call_args[0][0]
    # Check that the right macros are sent
    # /net/s25data/xorApps/ui/KB_mirrors.ui, macro:
    # P=25idcVME:,PM=25idcVME:,KB=KB,KBH=KB:H,KBV=KB:V,KBHUS=m6,KBHDS=m5,KBVUS=m8,KBVDS=m7,KB1=KBH, KB2=KBV
    macros = [cmds[i + 1] for i in range(len(cmds)) if cmds[i] == "-macro"][0]
    assert "P=255idc:" in macros
    assert "KB=KB" in macros
    assert "KBH=KB:H" in macros
    assert "KBV=KB:V" in macros
    # Check that the right UI file is being used
    ui_file = cmds[-1]
    assert ui_file.split("/")[-1] == "KB_mirrors.ui"
