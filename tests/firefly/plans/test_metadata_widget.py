import pytest

from firefly.display import SampleMetadata
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
    md = SampleMetadata(
        is_standard=True,
        chemical_formula="Xe260",
        sample_name="Xenonite",
        dm_experiment="cabana-2026-C3",
    )
    widget.update_sample_metadata(md)
    assert widget.ui.sample_combo_box.currentText() == "Xenonite"
    assert widget.ui.standard_check_box.isChecked()
    assert widget.ui.formula_combo_box.currentText() == "Xe260"
    assert widget.ui.dm_experiment_combo_box.currentText() == "cabana-2026-C3"
