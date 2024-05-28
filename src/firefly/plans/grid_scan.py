import logging

from bluesky_queueserver_api import BPlan
from qtpy import QtWidgets

from firefly import display
from firefly.application import FireflyApplication
from firefly.component_selector import ComponentSelector
from firefly.plans.line_scan import LineScanDisplay

log = logging.getLogger()


class TitleRegion:
    def __init__(self):
        self.setup_ui()

    def setup_ui(self):
        self.layout = QtWidgets.QGridLayout()
        labels = ["Priority axis", "Motor", "Start", "Stop", "Snake", "Fly"]
        Qlabels_all = {}

        # add labels in the first row
        for i, label_i in enumerate(labels):
            Qlabel_i = QtWidgets.QLabel(label_i)
            self.layout.addWidget(Qlabel_i, 0, i)
            Qlabels_all[label_i] = Qlabel_i

        # fix widths so the labels are aligned with GridScanRegions
        Qlabels_all["Priority axis"].setFixedWidth(70)
        Qlabels_all["Motor"].setFixedWidth(100)
        Qlabels_all["Snake"].setFixedWidth(53)
        Qlabels_all["Fly"].setFixedWidth(43)

        # add labels in the second row
        label = QtWidgets.QLabel("fast -> slow")
        self.layout.addWidget(label, 1, 0)


class GridScanRegion:
    def __init__(self):
        self.setup_ui()

    def setup_ui(self):
        self.layout = QtWidgets.QHBoxLayout()

        # First item, motor No.
        # self.motor_label = QtWidgets.QLabel()
        # self.layout.addWidget(self.motor_label)

        # First item, motor No.
        self.motor_label = QtWidgets.QLCDNumber()
        self.motor_label.setStyleSheet(
            "QLCDNumber { background-color: white; color: red; }"
        )
        self.layout.addWidget(self.motor_label)

        # Second item, ComponentSelector
        self.motor_box = ComponentSelector()
        self.layout.addWidget(self.motor_box)

        # Third item, start point
        self.start_line_edit = QtWidgets.QLineEdit()
        self.start_line_edit.setPlaceholderText("Start…")
        self.layout.addWidget(self.start_line_edit)

        # Forth item, stop point
        self.stop_line_edit = QtWidgets.QLineEdit()
        self.stop_line_edit.setPlaceholderText("Stop…")
        self.layout.addWidget(self.stop_line_edit)

        # Fifth item, snake checkbox
        self.snake_checkbox = QtWidgets.QCheckBox()
        self.snake_checkbox.setText("Snake")
        self.snake_checkbox.setEnabled(True)
        self.layout.addWidget(self.snake_checkbox)

        # Sixth item, fly checkbox # not available right now
        self.fly_checkbox = QtWidgets.QCheckBox()
        self.fly_checkbox.setText("Fly")
        self.fly_checkbox.setEnabled(False)
        self.layout.addWidget(self.fly_checkbox)


class GridScanDisplay(LineScanDisplay):
    default_num_regions = 2

    def __init__(self, parent=None, args=None, macros=None, ui_filename=None, **kwargs):
        super().__init__(parent, args, macros, ui_filename, **kwargs)

    def customize_ui(self):
        super().customize_ui()
        # add title layout
        self.title_region = TitleRegion()
        self.ui.title_layout.addLayout(self.title_region.layout)
        # reset button
        self.ui.reset_pushButton.clicked.connect(self.reset_default_regions)

    def add_regions(self, num=1):
        for i in range(num):
            region = GridScanRegion()
            self.ui.regions_layout.addLayout(region.layout)
            # Save it to the list
            self.regions.append(region)

            # the num of motor
            num_motor_i = len(self.regions)
            # region.motor_label.setText(str(num_motor_i)) # when using label
            region.motor_label.display(num_motor_i)

    def update_regions(self):
        super().update_regions()

        # disable snake for the last region and enable the previous regions
        self.regions[-1].snake_checkbox.setEnabled(False)
        for region_i in self.regions[:-1]:
            region_i.snake_checkbox.setEnabled(True)

    def queue_plan(self, *args, **kwargs):
        """Execute this plan on the queueserver."""
        detectors, num_points, motor_args, repeat_scan_num, md = (
            self.get_scan_parameters()
        )

        # get snake axes, if all unchecked, set it None
        snake_axes = [
            i
            for i, region_i in enumerate(self.regions)
            if region_i.snake_checkbox.isChecked()
        ]
        if snake_axes == []:
            snake_axes = False

        if self.ui.relative_scan_checkbox.isChecked():
            scan_type = "rel_grid_scan"
        else:
            scan_type = "grid_scan"

        # # Build the queue item
        item = BPlan(
            scan_type,
            detectors,
            *motor_args,
            num=num_points,
            snake_axes=snake_axes,
            md=md,
        )

        # Submit the item to the queueserver
        app = FireflyApplication.instance()
        log.info("Added line scan() plan to queue.")
        # repeat scans
        for i in range(repeat_scan_num):
            app.add_queue_item(item)

    def ui_filename(self):
        return "plans/grid_scan.ui"
