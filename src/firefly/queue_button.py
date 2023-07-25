"""A QPushButton that responds to the state of the queue server."""

from qtpy import QtWidgets, QtGui
import qtawesome as qta

from firefly import FireflyApplication


class QueueButton(QtWidgets.QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Listen for changes to the run engine
        app = FireflyApplication.instance()
        app.queue_status_changed.connect(self.handle_queue_status_change)

    def handle_queue_status_change(self, status: dict):
        print(f"Received {status}")
        if status['worker_environment_exists']:
            self.setEnabled(True)
        else:
            # Should be disabled because the queue is closed
            self.setDisabled(True)
        # Coloration for the whether the item would get run immediately
        app = FireflyApplication.instance()
        if status['re_state'] == "idle" and app.queue_autoplay_action.isChecked():
            # Will play immediately
            self.setStyleSheet("background-color: rgb(25, 135, 84);\n"
                               "border-color: rgb(25, 135, 84);")
            self.setIcon(qta.icon("fa5s.play"))
        elif status['worker_environment_exists']:
            # Will be added to the queue
            self.setStyleSheet("background-color: rgb(0, 123, 255);\n"
                               "border-color: rgb(0, 123, 255);")
            self.setIcon(qta.icon("fa5s.list"))
        else:
            # Regular old (probably disabled) button
            self.setStyleSheet("")
            self.setIcon(QtGui.QIcon())
