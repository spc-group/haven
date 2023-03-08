from qtpy.QtGui import QStandardItemModel

from firefly.bss import BssDisplay


def test_bss_window(qtbot, ffapp, mocker):
    api = mocker.MagicMock()
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
    display = BssDisplay(api=api)
    assert display.ui_filename() == "bss.ui"
    # Check model construction
    assert isinstance(display.proposal_model, QStandardItemModel)
    assert display.proposal_model.rowCount() > 0
    # Check that the view has the model attached
    # from pprint import pprint
    # pprint(dir(display.ui.proposal_view))
    assert display.ui.proposal_view.model() is display.proposal_model
