import pytest

from firefly.plans.metadata import MetadataWidget


@pytest.fixture()
def widget(qtbot):
    widg = MetadataWidget()
    qtbot.addWidget(widg)
    return widg


def test_purpose_combobox(widget):
    combobox = widget.purpose_combo_box
    assert combobox.isEditable()
    assert combobox.lineEdit().placeholderText() == "e.g. commissioning, alignment…"


def test_update_bss_metadata(widget):
    md = {
        "esaf_title": "Xenonite XAFS",
        "esaf_id": "12345",
        "proposal_title": "New materials for interstellar space travel",
        "proposal_id": "5678",
    }
    widget.update_bss_metadata(md)
    assert widget.ui.proposal_id_label.text() == md["proposal_id"]
    assert widget.ui.proposal_title_label.text() == md["proposal_title"]
    assert widget.ui.esaf_id_label.text() == md["esaf_id"]
    assert widget.ui.esaf_title_label.text() == md["esaf_title"]
