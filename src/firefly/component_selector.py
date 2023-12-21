import logging
from pprint import pprint

from qtpy.QtWidgets import QWidget, QComboBox, QHBoxLayout, QVBoxLayout, QPushButton, QDialog, QTreeView, QToolButton
from qtpy.QtCore import Qt
from qtpy.QtGui import QStandardItemModel, QStandardItem
import qtawesome as qta
from ophyd import sim

log = logging.getLogger(__name__)


class TreeComponent():
    """Representation of an ophyd Component/Device in a tree view."""
    child_components: list
    dotted_name: str
    component_item: QStandardItem
    type_item: QStandardItem
    
    def __init__(self, *args, device, text, parent, registry=None, **kwargs):
        self.device = device
        self.text = text
        self.parent = parent
        # Set the associated
        self.set_items()
        self.add_children()

    def __str__(self):
        return self.dotted_name

    def component_from_dotted_name(self, name):
        if name == self.dotted_name:
            # It's this component, so just return
            return self
        if self.dotted_name not in name:
            # It's not in this branch of the tree, so raise an exception
            raise KeyError(name)
        # See if we can find the dotted name farther down the tree
        for cpt in self.child_components:
            try:
                return cpt.component_from_dotted_name(name)
            except KeyError:
                continue
        raise KeyError(name)

    @property
    def dotted_name(self):
        names = []
        obj = self.device
        while obj.parent is not None:
            names.append(obj.attr_name)
            obj = obj.parent
        # Add the root devices name
        names.insert(0, obj.name)
        return ".".join(names)

    def set_items(self):
        """Add model items to the parent item."""
        self.component_item = QStandardItem(self.text)
        self.parent.appendRow(self.component_item)
        row = self.component_item.row()
        # Create an item for the type of component
        type_name = type(self.device).__name__
        self.type_item = QStandardItem(type_name)
        column = 1
        self.parent.setChild(row, column, self.type_item)
        # Decide on an icon for this component
        icons = {
            "mdi.cog-clockwise": {"SynAxis"},
            "mdi.connection": {"_ReadbackSignal", "_SetpointSignal", "Signal", "SynSignal", "EnumSignal"},
            "mdi.tape-drive": {},
            "mdi.router-network": {"SynGauss", },
        }
        for icon, types in icons.items():
            if type_name in types:
                self.type_item.setIcon(qta.icon(icon))
                break
        # Keep a reference to the component that created the items
        self.component_item.setData(self)
        self.type_item.setData(self)

    def add_children(self):
        """Add components of the device as branches on the tree."""
        child_names = getattr(self.device, "component_names", [])
        self.child_components = []
        # Add the children
        for name in child_names:
            child = self.__class__(device=getattr(self.device, name), text=name, parent=self.component_item)
            self.child_components.append(child)


class ComponentTreeModel(QStandardItemModel):
    Component: type = TreeComponent
    root_components: list

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.root_components = []

    def component_from_dotted_name(self, name):
        for cpt in self.root_components:
            try:
                return cpt.component_from_dotted_name(name)
            except KeyError:
                pass
        raise KeyError(name)

    def component_from_index(self, index):
        item = self.itemFromIndex(index)
        return item.data()
    
    def update_devices(self, registry):
        parent_item = self.invisibleRootItem()
        self.root_components = []
        for device in registry.root_devices():
            cpt = self.Component(device=device, text=device.name, parent=parent_item, registry=registry)
            self.root_components.append(cpt)


class ComboBoxComponent(TreeComponent):
    def set_items(self):
        """Add model items to the parent item."""
        self.component_item = QStandardItem(self.text)
        self.parent.appendRow(self.component_item)

    def add_children(self):
        """Add components of the device as extra options."""
        child_names = getattr(self.device, "component_names", [])
        self.child_components = []
        # Add the children
        for name in child_names:
            dotted_name = ".".join([self.text, name])
            child = self.__class__(device=getattr(self.device, name), text=dotted_name, parent=self.parent)
            self.child_components.append(child)
        


class ComponentComboBoxModel(ComponentTreeModel):
    Component: type = ComboBoxComponent            


class TreeDialog(QDialog):
    def __init__(self, *args, model, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model
        self.add_widgets()
        self.connect_signals()

    def connect_signals(self):
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def add_widgets(self):
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        # Add the tree view
        tree_view = QTreeView(parent=self)
        tree_view.setModel(self.model)
        main_layout.addWidget(tree_view)
        # Add accept/reject buttons
        buttons_layout = QHBoxLayout()
        main_layout.addLayout(buttons_layout)
        ok_button = QPushButton(parent=self)
        ok_button.setText("OK")
        ok_button.setIcon(qta.icon("fa5s.check"))
        self.ok_button = ok_button
        buttons_layout.addWidget(ok_button)
        cancel_button = QPushButton(parent=self)
        cancel_button.setText("Cancel")
        cancel_button.setIcon(qta.icon("fa5s.times"))
        self.cancel_button = cancel_button
        buttons_layout.addWidget(cancel_button)


class ComponentSelector(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.create_models()
        self.add_widgets()
        self.connect_signals()
        self.make_fake_motors()

    def current_component(self):
        return self.combo_box.currentText()

    def create_models(self):
        self.tree_model = ComponentTreeModel(0, 2)
        self.tree_model.setHorizontalHeaderLabels(["Component", "Type"])
        self.combo_box_model = ComponentComboBoxModel(0, 1)

    def make_fake_motors(self):

        """Only for testing."""
        from unittest import mock
        registry = mock.MagicMock()
        registry.root_devices.return_value = [sim.motor1, sim.motor2, sim.motor3, sim.det]
        self.update_devices(registry)

    def connect_signals(self):
        self.tree_button.toggled.connect(self.tree_view.setVisible)
        self.combo_box.currentTextChanged.connect(self.update_tree_model)
        self.tree_view.selectionModel().currentChanged.connect(self.update_combo_box_model)

    def update_tree_model(self, new_name):
        log.debug(f"Updating tree: {new_name=}")
        selection = self.tree_view.selectionModel()
        try:
            component = self.tree_model.component_from_dotted_name(new_name)
        except KeyError:
            # It's not a real component, so give up
            print(f"Could not find component for {new_name}, skipping.")
            return
        log.debug(f"Selecting combobox entry: {component.component_item.text()}")
        selection.setCurrentIndex(component.component_item.index(), selection.ClearAndSelect | selection.Rows)

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

    def update_devices(self, registry):
        devices = registry.root_devices()
        self.combo_box_model.update_devices(registry)
        self.tree_model.update_devices(registry)

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
        # Create a modal dialog (we won't show it until needed later)
        # tree_dialog = TreeDialog(parent=self, model=self.tree_model)
        # # tree_dialog.setWindowModality(Qt.ApplicationModal)
        # tree_dialog.setWindowModality(Qt.WindowModal)
        # self.tree_dialog = tree_dialog
