from unittest import mock

import pytest

from firefly.ion_chamber import IonChamberDisplay


@pytest.fixture()
def display(I0, qtbot):
    display = IonChamberDisplay(macros={"IC": I0.name})
    qtbot.addWidget(display)
    display.launch_caqtdm = mock.MagicMock()
    return display


def test_caqtdm_actions(display):
    assert len(display.caqtdm_actions) == 3
    # Check the details for the caQtDM actions
    actions = display.caqtdm_actions
    assert actions[0].text() == "&Scaler caQtDM"
    assert actions[1].text() == "&MCS caQtDM"
    assert actions[2].text() == "&Preamp caQtDM"
    # Check the slots are connected properly


def test_preamp_caqtdm_macros(display):
    # Check that the various caqtdm calls set up the right macros
    display.launch_preamp_caqtdm()
    assert display.launch_caqtdm.called
    assert (
        display.launch_caqtdm.call_args[1]["ui_file"]
        == "/net/s25data/xorApps/epics/synApps_6_2_1/support/ip-GIT/ipApp/op/ui/autoconvert/SR570.ui"
    )
    assert display.launch_caqtdm.call_args[1]["macros"] == {
        "P": "preamp_ioc:",
        "A": "SR04:",
    }


# def test_mcs_caqtdm_macros(display):
#     # Check that the various caqtdm calls set up the right macros
#     display.launch_mcs_caqtdm()
#     assert display.launch_caqtdm.called
#     assert (
#         display.launch_caqtdm.call_args[1]["ui_file"]
#         == "/APSshare/epics/synApps_6_2_1/support/mca-R7-9//mcaApp/op/ui/autoconvert/SIS38XX.ui"
#     )
#     assert display.launch_caqtdm.call_args[1]["macros"] == {"P": "scaler_ioc:"}


@pytest.mark.skip(reason="Causes CI to hang. Not sure why.")
def test_scaler_caqtdm_macros(display):
    # Check that the various caqtdm calls set up the right macros
    display.launch_scaler_caqtdm()
    assert display.launch_caqtdm.called
    assert (
        display.launch_caqtdm.call_args[1]["ui_file"]
        == "/net/s25data/xorApps/ui/scaler32_full_offset.ui"
    )
    assert display.launch_caqtdm.call_args[1]["macros"] == {
        "P": "scaler_ioc:",
        "S": "scaler1",
    }
