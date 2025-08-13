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
