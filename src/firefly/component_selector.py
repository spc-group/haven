import logging
from collections import OrderedDict
from functools import lru_cache
from typing import Mapping, Sequence

import qtawesome as qta
from ophyd import Device, EpicsMotor, PositionerBase, Signal
from qasync import asyncSlot
from qtpy.QtGui import QFont, QStandardItem, QStandardItemModel
from qtpy.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QSizePolicy,
    QToolButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

log = logging.getLogger(__name__)


@lru_cache()
def icons():
    """Produce a dictionary of icons for specific device classes.

    Profiling shows that creating the qta.icon objects is
    slow. Since there are a lot of potential signals, it makes
    sense to cache the icons behind a static method to speed up
    window loading.

    """
    return OrderedDict(
        {
            EpicsMotor: qta.icon("mdi.cog-clockwise"),
            Device: qta.icon("mdi.router-network"),
            Signal: qta.icon("mdi.connection"),
        }
    )


class OphydNode:
    """A node in the Ophyd device hierarchy."""

    device_class: type
    text: str
    dotted_name: str

    def __init__(self, device_class: type, text: str, dotted_name: str):
        self.device_class = device_class
        self.text = text
        self.dotted_name = dotted_name
        # Set the associated
        self.set_items()

    def __str__(self):
        return f"{self.text} ({self.device_class})"

    def set_items(self):
        raise NotImplementedError


class TreeNode(OphydNode):
    parent_item: QStandardItem

    def __init__(self, *args, parent_item, **kwargs):
        self.parent_item = parent_item
        super().__init__(*args, **kwargs)

    def set_items(self):
        """Add model items to the parent item."""
        self.name_item = QStandardItem(self.text)
        parent = self.parent_item
        parent.appendRow(self.name_item)
        row = self.name_item.row()
        # Create an item for the type of component
        type_name = self.device_class.__name__
        self.type_item = QStandardItem(type_name)
        column = 1
        parent.setChild(row, column, self.type_item)
        # Make the component item bold if it's a positioner
        if issubclass(self.device_class, PositionerBase):
            font = QFont()
            font.setBold(True)
            self.name_item.setFont(font)
        # Decide on an icon for this component
        for cls, icon in icons().items():
            if issubclass(self.device_class, cls):
                self.type_item.setIcon(icon)
                break
        # Keep a reference to the component that created the items
        self.name_item.setData(self)
        self.type_item.setData(self)


class DeviceTree(TreeNode):
    """Representation of an ophyd Component/Device in a tree view."""

    nodes: Mapping

    def __init__(self, device, *args, **kwargs):
        self.device = device
        dotted_name = self.device.name
        dotted_name = kwargs.pop("dotted_name", dotted_name)
        super().__init__(
            *args, device_class=type(device), dotted_name=dotted_name, **kwargs
        )

    def component_from_dotted_name(self, name):
        return self.nodes[name]

    def add_children(self):
        """Add components of the device as branches on the tree."""
        # Create a place to store the nodes of the tree
        self.nodes = {self.device.name: self}
        # Get the subcomponents of the device
        components = getattr(self.device, "walk_components", lambda: [])()
        # Build the tree from the child components of the device
        for ancestors, dotted_name, cpt in components:
            dotted_name = ".".join([self.device.name, dotted_name])
            parent = dotted_name.rsplit(".", maxsplit=1)[0]
            parent = self.nodes[parent]
            node = TreeNode(
                parent_item=parent.name_item,
                text=cpt.attr,
                device_class=cpt.cls,
                dotted_name=dotted_name,
            )
            self.nodes[dotted_name] = node


class DeviceTreeModel(QStandardItemModel):
    trees: Sequence
    root_item: QStandardItem

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set up the root devices
        self.trees = []
        self.root_item = self.invisibleRootItem()

    def component_from_dotted_name(self, name):
        for tree in self.trees:
            try:
                return tree.component_from_dotted_name(name)
            except KeyError:
                pass
        raise KeyError(name)

    def component_from_index(self, index):
        item = self.itemFromIndex(index)
        return item.data()

    async def add_device(self, device):
        """Add a new root device to the tree."""
        tree = DeviceTree(
            device=device,
            text=device.name,
            parent_item=self.root_item,
        )
        tree.add_children()
        self.trees.append(tree)


class ComboBoxNode(OphydNode):
    def set_items(self):
        """Add model items to the parent item."""
        self.text_item = QStandardItem(self.text)


class DeviceComboBoxModel(QStandardItemModel):
    valid_classes = [PositionerBase, Device]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.nodes = {}

    async def add_device(self, device):
        """Add components of the device as extra options."""
        # Add a node for the root device itself
        root_node = ComboBoxNode(
            text=device.name, device_class=type(device), dotted_name=device.name
        )
        self.nodes[device.name] = root_node
        self.appendRow(root_node.text_item)
        # Get the subcomponents of the device
        components = getattr(device, "walk_components", lambda: [])()
        # Build the tree from the child components of the device
        for ancestors, dotted_name, cpt in components:
            # Only add a device if it's high-level (e.g. motor)
            device_class = cpt.cls
            is_valid = (issubclass(device_class, cls) for cls in self.valid_classes)
            if not any(is_valid):
                continue
            # Prepare some device info
            dotted_name = ".".join([device.name, dotted_name])
            parent = dotted_name.rsplit(".", maxsplit=1)[0]
            parent = self.nodes[parent]
            # Create the node
            node = ComboBoxNode(
                text=dotted_name, device_class=device_class, dotted_name=dotted_name
            )
            self.nodes[dotted_name] = node
            # Add the node's model items to the model
            self.appendRow(node.text_item)


class ComponentSelector(QWidget):
    registry = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.create_models()
        self.add_widgets()
        self.connect_signals()

    def current_component(self):
        cpt_name = self.combo_box.currentText()
        return self.registry[cpt_name]

    def create_models(self):
        self.tree_model = DeviceTreeModel(0, 2)
        self.tree_model.setHorizontalHeaderLabels(["Component", "Type"])
        self.combo_box_model = DeviceComboBoxModel(0, 1)

    def connect_signals(self):
        self.tree_button.toggled.connect(self.tree_view.setVisible)
        self.combo_box.currentTextChanged.connect(self.update_tree_model)
        self.tree_view.selectionModel().currentChanged.connect(
            self.update_combo_box_model
        )

    def update_tree_model(self, new_name):
        log.debug(f"Updating tree: {new_name=}")
        selection = self.tree_view.selectionModel()
        try:
            component = self.tree_model.component_from_dotted_name(new_name)
        except KeyError:
            # It's not a real component, so give up
            log.debug(f"Could not find component for {new_name}, skipping.")
            return
        log.debug(f"Selecting combobox entry: {component.name_item.text()}")
        selection.setCurrentIndex(
            component.name_item.index(), selection.ClearAndSelect | selection.Rows
        )

    def update_combo_box_model(self, index, previous):
        cpt = self.tree_model.component_from_index(index)
        self.combo_box.setCurrentText(cpt.dotted_name)
        log.debug(f"Updating combobox: {cpt.dotted_name=}")

    def select_tree_motor(self):
        if not self.tree_button.isChecked():
            return
        log.debug("Showing motor tree dialog.")
        # Prompt the user to choose a new motor/signal
        accepted = self.tree_dialog.exec()
        self.tree_button.setChecked(False)
        if not accepted:
            # Clicked "Cancel"
            log.debug("Motor tree dialog canceled")
            return
        # Change the current combobox entry
        log.debug("Changing selected motor.")

    @asyncSlot(object)
    async def update_devices(self, registry):
        self.registry = registry
        # Get the devices to add
        devices = sorted(registry.root_devices, key=lambda dev: dev.name.lower())
        for device in devices:
            await self.combo_box_model.add_device(device)
            await self.tree_model.add_device(device)
        # Clear the combobox text so it doesn't auto-select the first entry
        self.combo_box.setCurrentText("")

    def add_widgets(self):
        # Create a layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        row_layout = QHBoxLayout()
        layout.addLayout(row_layout)
        # Add a combobox
        combo_box = QComboBox(parent=self)
        combo_box.setModel(self.combo_box_model)
        combo_box.setSizePolicy(
            QSizePolicy.MinimumExpanding,
            QSizePolicy.Fixed,
        )
        row_layout.addWidget(combo_box)
        combo_box.setEditable(True)
        self.combo_box = combo_box
        # Add a button for launching the tree modal dialog
        tree_button = QToolButton(parent=self)
        tree_button.setIcon(qta.icon("mdi.file-tree"))
        tree_button.setCheckable(True)
        row_layout.addWidget(tree_button)
        self.tree_button = tree_button
        # Add a hidden tree view for selecting motors
        tree_view = QTreeView(parent=self)
        tree_view.setVisible(False)
        tree_view.setModel(self.tree_model)
        layout.addWidget(tree_view)
        self.tree_view = tree_view
