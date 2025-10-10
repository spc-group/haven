from dataclasses import dataclass

import pytest
from qtpy.QtWidgets import QCheckBox, QGridLayout, QLineEdit, QWidget

from firefly.plans.regions import RegionsManager


class MockManager[WidgetsType](RegionsManager):

    @dataclass(frozen=True)
    class WidgetSet:
        active_checkbox: QCheckBox
        name: QLineEdit

    async def create_row_widgets(self, row: int) -> list[QWidget]:
        return [QLineEdit()]

    def widgets_to_region(self, widgets: WidgetSet) -> RegionsManager.Region:
        """Take a list of widgets in a row, and build a Region object.

        This method is meant be over-ridden by subclasses.

        """
        return self.Region(is_active=widgets.active_checkbox.isChecked())

    async def update_devices(self, registry=None, *, rows=None):
        pass


@pytest.fixture()
def manager(qtbot):
    parent = QWidget()
    layout = QGridLayout()
    parent.setLayout(layout)
    manager = MockManager[RegionsManager.WidgetSet](layout=layout, parent=parent)
    qtbot.addWidget(parent)
    yield manager


async def test_set_row_count(manager):
    assert len(manager) == 0
    # Increase the row count
    await manager.set_region_count(2)
    assert len(manager) == 2
    # Decrease the row count
    await manager.set_region_count(1)
    assert len(manager) == 1


async def test_new_row_devices(manager, sim_registry):
    """Do devices get added to new rows in the region?"""
    manager.update_devices(sim_registry)


async def test_regions_indexing(manager):
    """Can the regions be retrieved by index?"""
    await manager.set_region_count(2)
    assert len(manager) == 2
    assert isinstance(manager[0], RegionsManager.Region)
    assert isinstance(manager[1], RegionsManager.Region)
    assert isinstance(manager[-2], RegionsManager.Region)
    # Check out-of-bounds indexing
    with pytest.raises(IndexError):
        manager[2]
    with pytest.raises(IndexError):
        manager[-3]


async def test_regions_iterable(manager):
    """Can the regions be iterated over?"""
    await manager.set_region_count(2)
    assert len(list(manager)) == 2


async def test_inactive_regions(manager):
    await manager.set_region_count(2)
    manager.layout.itemAtPosition(1, 0).widget().setChecked(False)
    assert not manager[0].is_active
    assert manager[1].is_active


async def test_disable_region_widgets(manager):
    """Do the widgets in the region get deactivate when unchecked"""
    await manager.set_region_count(2)
    region_checkbox = manager.layout.itemAtPosition(1, 0).widget()
    assert region_checkbox.isChecked()
    # Make sure we have a widget to disable
    line_edit = manager.row_widgets(1).name
    manager.layout.addWidget(line_edit, 1, 1)
    assert line_edit.isEnabled()
    # Uncheck the box, do the widgets disable?
    region_checkbox.setChecked(False)
    assert not region_checkbox.isChecked()
    assert not line_edit.isEnabled()
