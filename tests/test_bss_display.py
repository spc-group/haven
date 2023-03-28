import pytest
from qtpy.QtGui import QStandardItemModel
from qtpy.QtCore import Qt
from epics import caget, caput

from haven.instrument.aps import load_aps
from firefly.bss import BssDisplay
from firefly.main_window import FireflyMainWindow


@pytest.fixture()
def bss_api(mocker):
    api = mocker.MagicMock()
    api.getCurrentEsafs.return_value = [{
        'description': 'We will perform some K-edge and L-edge XAFS measurements of '
        'some transition metal nanoparticle powder samples such as '
        'silver, palladium, gold, copper and platinum. \r\n'
        '\r\n'
        'Some of the measurements will need in situ gas adsorption '
        'and/or heating conditions. Standard beamline temperature '
        'controller and power supply will be used to heat samples to '
        '100C. Some of the samples may be in solution phase. We will '
        'also perform Au L2 edge XAFS measurement in HERFD mode of '
        'some metal nanoparticle samples. The nanoparticle samples '
        'are all unbound nanostructured materials. Samples will be '
        'encapsulated in Kapton tape or prepared by using capillaries '
        'and quartz wool. For solution phase measurements, the Teflon '
        'sample holder will be used.',
        'esafId': 269238,
        'esafStatus': 'Pending',
        'esafTitle': 'A Partner User Proposal to Continue the Successful '
        'Collaboration between the Canadian Light Source Inc. and the '
        'Advanced Photon Source',
        'experimentEndDate': '2023-03-31 08:00:00',
        'experimentStartDate': '2023-03-28 08:00:00',
        'experimentUsers': [{'badge': '86423',
                             'badgeNumber': '86423',
                             'email': 'peng.zhang@dal.ca',
                             'firstName': 'Peng',
                             'lastName': 'Zhang',
                             'piFlag': 'Yes'},
                            {'badge': '302308',
                             'badgeNumber': '302308',
                             'email': 'yannachen@anl.gov',
                             'firstName': 'Yanna',
                             'lastName': 'Chen',
                             'piFlag': 'No'},
                            {'badge': '299574',
                             'badgeNumber': '299574',
                             'email': 'dmeira@anl.gov',
                             'firstName': 'Debora',
                             'lastName': 'Motta Meira',
                             'piFlag': 'No'},
                            {'badge': '300051',
                             'badgeNumber': '300051',
                             'email': 'zy916874@dal.ca',
                             'firstName': 'Ziyi',
                             'lastName': 'Chen',
                             'piFlag': 'No'}],
        'sector': '25'}]
        
    api.getCurrentProposals.return_value = [
        {'title': 'A Partner User Proposal to Continue the Successful Collaboration between the Canadian Light Source Inc. and the Advanced Photon Source',
         'id': 74163,
         'experimenters': [{'id': 521867,
                            'badge': '307373',
                            'email': 'gianluigi.botton@lightsource.ca',
                            'piFlag': 'Y',
                            'instId': 3949,
                            'firstName': 'Gianluigi',
                            'lastName': 'Botton',
                            'institution': 'Canadian Light Source'},
                           {'id': 488536,
                            'badge': '242561',
                            'email': 'chithra.karunakaran@lightsource.ca',
                            'instId': 3949,
                            'firstName': 'Chithra',
                            'lastName': 'Karunakaran',
                            'institution': 'Canadian Light Source'},
                           {'id': 488508,
                            'badge': '299574',
                            'email': 'dmeira@anl.gov',
                            'instId': 3949,
                            'firstName': 'Debora',
                            'lastName': 'Motta Meira',
                            'institution': 'Canadian Light Source'}],
         'activities': [{'startTime': '2023-02-14 08:00:00-06:00',
                         'endTime': '2023-02-17 08:00:00-06:00',
                         'duration': 259200},
                        {'startTime': '2023-03-28 08:00:00-05:00',
                         'endTime': '2023-03-31 08:00:00-05:00',
                         'duration': 259200}],
         'submittedDate': '2021-03-04 13:20:06-06:00',
         'proprietaryFlag': 'N',
         'startTime': '2023-02-14 08:00:00-06:00',
         'endTime': '2023-03-31 08:00:00-05:00',
         'duration': 518400,
         'cycle': '2023-1'}]
    yield api


def test_bss_proposal_model(qtbot, ffapp, bss_api):
    display = BssDisplay(api=bss_api)
    assert display.ui_filename() == "bss.ui"
    # Check model construction
    assert isinstance(display.proposal_model, QStandardItemModel)
    assert display.proposal_model.rowCount() > 0
    # Check that the view has the model attached
    assert display.ui.proposal_view.model() is display.proposal_model


def test_bss_proposal_updating(qtbot, ffapp, bss_api, ioc_bss):
    load_aps()
    display = BssDisplay(api=bss_api)
    # Set some base-line values on the IOC
    caput("99id:bss:proposal:id", "")
    # Change the proposal item
    selection_model = display.ui.proposal_view.selectionModel()
    item = display.proposal_model.item(0, 1)
    assert item is not None
    rect = display.proposal_view.visualRect(item.index())
    # See if the proposal PVs were updated
    with qtbot.waitSignal(display.proposal_selected):
        qtbot.mouseClick(display.proposal_view.viewport(), Qt.LeftButton, pos=rect.center())
    assert display.ui.update_proposal_button.isEnabled()
    pv_id = caget("99id:bss:proposal:id", use_monitor=False, as_string=True)
    assert pv_id != "74163"
    assert display._proposal_id == "74163"
    # Now update the PROPOSAL details
    with qtbot.waitSignal(display.proposal_changed):
        qtbot.mouseClick(display.ui.update_proposal_button, Qt.LeftButton)
    pv_id = caget("99id:bss:proposal:id", use_monitor=False, as_string=True)
    assert pv_id == "74163"
    bss_api.epicsUpdate.assert_called_once_with("99id:bss:")


def test_bss_proposals(ffapp, bss_api):
    window = FireflyMainWindow()
    display = BssDisplay(api=bss_api)
    # Check values
    api_proposal = bss_api.getCurrentProposals()[0]
    proposals = display.proposals
    proposal = proposals[0]
    from pprint import pprint
    pprint(proposal)
    assert proposal['Title'] == api_proposal['title']
    assert proposal["ID"] == api_proposal['id']
    assert proposal["Users"] == "Botton, Karunakaran, Motta Meira"
    assert proposal["Badges"] == "307373, 242561, 299574"
    assert proposal["Start"] == "2023-02-14 08:00:00-06:00"
    assert proposal["End"] == "2023-03-31 08:00:00-05:00"


def test_bss_esaf_model(qtbot, ffapp, bss_api):
    display = BssDisplay(api=bss_api)
    assert display.ui_filename() == "bss.ui"
    # Check model construction
    assert isinstance(display.esaf_model, QStandardItemModel)
    # assert display.esaf_model.rowCount() > 0
    bss_api.getCurrentEsafs.assert_called_once_with("99")
    # Check that the view has the model attached
    assert display.ui.esaf_view.model() is display.esaf_model


def test_bss_esaf_updating(qtbot, ffapp, bss_api, ioc_bss):
    load_aps()
    window = FireflyMainWindow()
    display = BssDisplay(api=bss_api)
    # Set some base-line values on the IOC
    caput("99id:bss:esaf:id", "")
    # Change the ESAF item
    selection_model = display.ui.esaf_view.selectionModel()
    item = display.esaf_model.item(0, 1)
    assert item is not None
    rect = display.esaf_view.visualRect(item.index())
    # Clicking a list entry should enable the update button
    with qtbot.waitSignal(display.esaf_selected):
        qtbot.mouseClick(display.esaf_view.viewport(), Qt.LeftButton, pos=rect.center())
    assert display.ui.update_esaf_button.isEnabled()
    pv_id = caget("99id:bss:esaf:id", use_monitor=False, as_string=True)
    assert pv_id != "269238"
    assert display._esaf_id == "269238"
    # Now update the ESAF details
    with qtbot.waitSignal(display.esaf_changed):
        qtbot.mouseClick(display.ui.update_esaf_button, Qt.LeftButton)
    pv_id = caget("99id:bss:esaf:id", use_monitor=False, as_string=True)
    assert pv_id == "269238"
    bss_api.epicsUpdate.assert_called_once_with("99id:bss:")


def test_bss_esafs(ffapp, bss_api):
    window = FireflyMainWindow()
    display = BssDisplay(api=bss_api)
    # Check values
    api_esaf = bss_api.getCurrentEsafs()[0]
    esafs = display.esafs
    esaf = esafs[0]
    assert esaf['Title'] == api_esaf['esafTitle']
    assert esaf["ID"] == api_esaf['esafId']
    assert esaf["Users"] == "Zhang, Chen, Motta Meira, Chen"
    assert esaf["Badges"] == "86423, 302308, 299574, 300051"
    assert esaf["Start"] == "2023-03-28 08:00:00"
    assert esaf["End"] == "2023-03-31 08:00:00"
