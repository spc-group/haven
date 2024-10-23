import logging
from collections import OrderedDict
from enum import IntEnum
from functools import lru_cache
from typing import Mapping, Sequence

import qtawesome as qta
from bluesky.protocols import HasName, Movable
from ophyd import Device, EpicsMotor, PositionerBase, Signal
from ophyd_async.core import Device as AsyncDevice
from ophyd_async.core import DeviceVector
from ophyd_async.core import Signal as AsyncSignal
from ophyd_async.epics.motor import Motor as EpicsAsyncMotor
from qasync import asyncSlot
from qtpy.QtGui import QColor, QFont, QStandardItem, QStandardItemModel
from qtpy.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QSizePolicy,
    QToolButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from haven.positioner import Positioner

log = logging.getLogger(__name__)


class Flavors(IntEnum):
    UNKNOWN = 0
    VANILLA_DEVICE = 1
    VANILLA_SIGNAL = 2
    ASYNC_DEVICE = 3
    ASYNC_SIGNAL = 4


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
            EpicsAsyncMotor: qta.icon("mdi.cog-clockwise"),
            Device: qta.icon("mdi.router-network"),
            AsyncDevice: qta.icon("mdi.router-network"),
            Signal: qta.icon("mdi.connection"),
            AsyncSignal: qta.icon("mdi.connection"),
        }
    )


class DeviceContainer:
    device_flavor: Flavors = Flavors.UNKNOWN

    def _asynchronous_children(self, device):
        for attr_name, child in device.children():
            dot_name = dotted_name(child)
            yield (dot_name, type(child), attr_name)
            yield from self._asynchronous_children(child)

    def _synchronous_children(self, device):
        # Get the subcomponents of the device
        components = getattr(device, "walk_components", lambda: [])()
        # Build the tree from the child components of the device
        for ancestors, dotted_name, cpt in components:
            dotted_name = ".".join([device.name, dotted_name])
            yield (dotted_name, cpt.cls, cpt.attr)


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
        positioner_classes = (PositionerBase, EpicsAsyncMotor, Positioner)
        is_positioner = any(
            issubclass(self.device_class, Klass) for Klass in positioner_classes
        )
        if is_positioner:
            font = QFont()
            font.setBold(True)
            self.name_item.setFont(font)
        # Decide on the row's color
        is_async_device = issubclass(self.device_class, AsyncDevice) and not issubclass(
            self.device_class, AsyncSignal
        )
        is_device = issubclass(self.device_class, Device) or is_async_device
        is_movable = issubclass(self.device_class, Movable)
        if not (is_movable or is_device):
            line_color = QColor("darkgrey")
        else:
            line_color = QColor("black")
        self.name_item.setForeground(line_color)
        self.type_item.setForeground(line_color)
        # Decide on an icon for this component
        for cls, icon in icons().items():
            if issubclass(self.device_class, cls):
                self.type_item.setIcon(icon)
                break
        # Hint non-movable entries
        is_movable = issubclass(self.device_class, Movable)
        if not is_movable:
            font = QFont()
            font.setItalic(True)
            self.name_item.setFont(font)
        # Keep a reference to the component that created the items
        self.name_item.setData(self)
        self.type_item.setData(self)


def dotted_name(obj: HasName) -> str:
    """Get the dotted attribute name of an ophyd_async object."""
    if obj.parent is None:
        # It's a root device, so just the device name
        return obj.name
    # Figure out the attr_name
    if isinstance(obj.parent, DeviceVector):
        attrs = obj.parent
    else:
        attrs = obj.parent.__dict__
    for attr, other_obj in attrs.items():
        if other_obj is obj:
            attr_name = attr
            break
    else:
        print(obj.parent.__class__)
        raise RuntimeError(f"Could not find attribute name for {obj.name}.")
    # siblings = list(attrs.values())
    # attr_names = list(attrs.keys())
    # idx = siblings.index(obj)
    # attr_name = attr_names[siblings.index(obj)]
    # attr_name = list(attrs.keys())[list(attrs.values()).index(obj)]
    # Attach our attr_name to the dotted name of the parent
    parent_name = dotted_name(obj.parent)
    return f"{parent_name}.{attr_name}"


def device_flavor(device):
    # Determine what flavor of device this is
    if isinstance(device, Device):
        return Flavors.VANILLA_DEVICE
    elif isinstance(device, Signal):
        return Flavors.VANILLA_SIGNAL
    elif isinstance(device, AsyncDevice):
        return Flavors.ASYNC_DEVICE
    elif isinstance(device, AsyncSignal):
        return Flavors.ASYNC_SIGNAL
    # Something else, *shrug*
    return Flavors.UNKNOWN


class DeviceTree(DeviceContainer, TreeNode):
    """Representation of an ophyd Component/Device in a tree view."""

    nodes: Mapping
    device_flavor: int = Flavors.UNKNOWN

    def __init__(self, device, *args, **kwargs):
        self.device = device
        self.device_flavor = device_flavor(device)
        # Determine the fully dotted attribute name
        dot_name = dotted_name(device)
        dot_name = kwargs.pop("dotted_name", dot_name)
        super().__init__(
            *args, device_class=type(device), dotted_name=dot_name, **kwargs
        )

    def component_from_dotted_name(self, name):
        return self.nodes[name]

    def add_children(self):
        """Add components of the device as branches on the tree."""
        # Create a place to store the nodes of the tree
        self.nodes = {self.device.name: self}
        # Get the device's children
        if self.device_flavor == Flavors.VANILLA_DEVICE:
            children = self._synchronous_children(self.device)
        elif self.device_flavor == Flavors.ASYNC_DEVICE:
            children = self._asynchronous_children(self.device)
        else:
            children = []
        # Build nodes for the children
        for dotted_name, child_cls, text in children:
            parent = dotted_name.rsplit(".", maxsplit=1)[0]
            parent = self.nodes[parent]
            node = TreeNode(
                parent_item=parent.name_item,
                text=text,
                device_class=child_cls,
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


class DeviceComboBoxModel(DeviceContainer, QStandardItemModel):
    valid_classes = [PositionerBase, Device, AsyncDevice]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.nodes = {}

    async def add_device(self, device):
        """Add components of the device as extra options."""
        # Add a node for the root device itself
        flavor = device_flavor(device)
        root_node = ComboBoxNode(
            text=device.name, device_class=type(device), dotted_name=device.name
        )
        self.nodes[device.name] = root_node
        self.appendRow(root_node.text_item)
        # Get the device's children
        if flavor == Flavors.VANILLA_DEVICE:
            children = self._synchronous_children(device)
        elif flavor == Flavors.ASYNC_DEVICE:
            children = self._asynchronous_children(device)
        else:
            children = []
        # Build the tree from the child components of the device
        # components = getattr(device, "walk_components", lambda: [])()
        # for ancestors, dotted_name, cpt in components:
        # Build nodes for the children
        for dotted_name, child_cls, text in children:
            # Only add a device if it's high-level (e.g. motor)
            is_valid = (issubclass(child_cls, cls) for cls in self.valid_classes)
            if not any(is_valid):
                continue
            # Create the node
            node = ComboBoxNode(
                text=dotted_name, device_class=child_cls, dotted_name=dotted_name
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
        if cpt_name == "":
            # Nothing selected
            return None
        else:
            # A device was selected
            return self.registry.find(name=cpt_name)

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
