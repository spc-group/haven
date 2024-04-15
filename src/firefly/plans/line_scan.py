import logging

from bluesky_queueserver_api import BPlan
from qtpy import QtWidgets

from firefly import display
from firefly.component_selector import ComponentSelector

log = logging.getLogger()


class LineScanRegion:
    def __init__(self):
        self.setup_ui()

    def setup_ui(self):
        self.layout = QtWidgets.QHBoxLayout()

        # First item, motor No.
        # self.motor_label = QtWidgets.QLabel()
        # self.motor_label.setText("1")
        # self.layout.addWidget(self.motor_label)

        # Second item, ComponentSelector
        self.motor_box = ComponentSelector()
        # self.stop_line_edit.setPlaceholderText("Stop…")
        self.layout.addWidget(self.motor_box)

        # Third item, start point
        self.start_line_edit = QtWidgets.QLineEdit()
        self.start_line_edit.setPlaceholderText("Start…")
        self.layout.addWidget(self.start_line_edit)

        # Forth item, stop point
        self.stop_line_edit = QtWidgets.QLineEdit()
        self.stop_line_edit.setPlaceholderText("Stop…")
        self.layout.addWidget(self.stop_line_edit)


class LineScanDisplay(display.FireflyDisplay):
    def customize_ui(self):
        # Remove the default XAFS layout from .ui file
        self.clearLayout(self.ui.region_template_layout)
        self.reset_default_regions()

        # disable the line edits in spin box
        self.ui.num_motor_spin_box.lineEdit().setReadOnly(True)
        self.ui.num_motor_spin_box.valueChanged.connect(self.update_regions)

        self.ui.run_button.setEnabled(True) #for testing
        self.ui.run_button.clicked.connect(self.queue_plan)

    def clearLayout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

    def reset_default_regions(self):
        default_num_regions = 1
        if not hasattr(self, "regions"):
            self.regions = []
            self.add_regions(default_num_regions)
        self.ui.num_motor_spin_box.setValue(default_num_regions)
        self.update_regions()

    def add_regions(self, num=1):
        for i in range(num):
            region = LineScanRegion()
            self.ui.regions_layout.addLayout(region.layout)
            # Save it to the list
            self.regions.append(region)

    def remove_regions(self, num=1):
        for i in range(num):
            layout = self.regions[-1].layout
            # iterate/wait, and delete all widgets in the layout in the end
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self.regions.pop()

    def update_regions(self):
        new_region_num = self.ui.num_motor_spin_box.value()
        old_region_num = len(self.regions)
        diff_region_num = new_region_num - old_region_num

        if diff_region_num < 0:
            self.remove_regions(abs(diff_region_num))
        elif diff_region_num > 0:
            self.add_regions(diff_region_num)

    def queue_plan(self, *args, **kwargs):
        """Execute this plan on the queueserver."""
        # Get scan parameters from widgets
        detectors = self.ui.detectors_list.selected_detectors()
        num_points = self.ui.scan_pts_spin_box.value()

        # get paramters from each rows of line regions:
        motor_lst, start_lst, stop_lst = [], [], []
        for region_i in self.regions:
            motor_lst.append(region_i.motor_box.combo_box.currentText())
            start_lst.append(float(region_i.start_line_edit.text()))
            stop_lst.append(float(region_i.stop_line_edit.text()))

        motor_args = [
            values
            for motor_i in zip(motor_lst, start_lst, stop_lst)
            for values in motor_i
        ]

        print(motor_args)

        if self.ui.relative_scan_checkbox.isChecked():
            if self.ui.log_scan_checkbox.isChecked():
                scan_type = 'rel_log_scan'
            else:
                scan_type = 'rel_scan'
        else:
            if self.ui.log_scan_checkbox.isChecked():
                scan_type = 'log_scan'
            else:
                scan_type = 'scan'
          
        md={'sample': self.ui.lineEdit_sample.text(),
            'purpose':self.ui.lineEdit_purpose.text()}

        # # Build the queue item
        item = BPlan(
            scan_type,
            detectors,
            *motor_args,
            num=num_points,
            # per_step=None,
            md=md,
        )
        print(item)

        # Submit the item to the queueserver
        from firefly.application import FireflyApplication

        app = FireflyApplication.instance()
        log.info("Add ``scan()`` plan to queue.")
        app.add_queue_item(item)

    def ui_filename(self):
        return "plans/line_scan.ui"
