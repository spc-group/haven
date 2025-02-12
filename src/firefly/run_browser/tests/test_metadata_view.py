import pytest
from qtpy.QtWidgets import QPlainTextEdit

from firefly.run_browser.metadata_view import MetadataView


@pytest.fixture()
def view(qtbot):
    md_view = MetadataView()
    qtbot.addWidget(md_view)
    return md_view


def test_load_ui(view):
    """Make sure widgets were loaded from the UI file."""
    assert isinstance(view.ui.metadata_textedit, QPlainTextEdit)


def test_display_metadata(view):
    metadata = {
        "58c7f8cd-5970-45d0-beff-a673386e52a8": {
            "start": {
                "plan_name": "xafs_scan",
            }
        },
    }
    view.display_metadata(metadata)
    new_text = view.ui.metadata_textedit.document().toPlainText()
    assert "# 58c7f8cd-5970-45d0-beff-a673386e52a8" in new_text
    assert "xafs_scan" in new_text
