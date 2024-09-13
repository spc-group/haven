import logging
import time
import warnings
from typing import Mapping, Optional

from bluesky_queueserver_api import comm_base
from bluesky_queueserver_api.zmq.aio import REManagerAPI
from qasync import asyncSlot
from qtpy.QtCore import QObject, QTimer, Signal

from haven import load_config
from haven.exceptions import InvalidConfiguration

log = logging.getLogger()


def queueserver_api():
    try:
        config = load_config()["queueserver"]
        ctrl_addr = f"tcp://{config['control_host']}:{config['control_port']}"
        info_addr = f"tcp://{config['info_host']}:{config['info_port']}"
    except KeyError as e:
        raise InvalidConfiguration(str(e))
    api = REManagerAPI(zmq_control_addr=ctrl_addr, zmq_info_addr=info_addr)
    return api


class QueueClient(QObject):
    api: REManagerAPI
    _last_queue_status: Optional[dict] = None
    last_update: float = -1
    timeout: float = 0.2
    min_timeout: float = 0.2
    timer: QTimer

    # Signals responding to queue changes
    status_changed = Signal(dict)
    length_changed = Signal(int)
    in_use_changed = Signal(bool)  # If length > 0, or queue is running
    autostart_changed = Signal(bool)
    queue_stop_changed = Signal(bool)  # If a queue stop has been requested
    environment_opened = Signal(bool)  # Opened (True) or closed (False)
    environment_state_changed = Signal(str)  # New state
    manager_state_changed = Signal(str)  # New state
    re_state_changed = Signal(str)  # New state
    devices_changed = Signal(dict)

    def start(self):
        self.timer.start(int(self.timeout * 1000))

    def __init__(self, *args, api, **kwargs):
        self.api = api
        super().__init__(*args, **kwargs)
        self._last_queue_status = {}
        # Setup timer for updating the queue
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)

    @asyncSlot(bool)
    async def open_environment(self, to_open):
        if to_open:
            result = await self.api.environment_open()
        else:
            result = await self.api.environment_close()
        if result["success"]:
            self.environment_opened.emit(to_open)
        else:
            log.error(f"Failed to open/close environment: {result['msg']}")

    @asyncSlot()
    async def update(self):
        now = time.monotonic()
        if now >= self.last_update + self.timeout:
            if not load_config()["beamline"]["is_connected"]:
                log.warning("Beamline not connected, skipping queue client update.")
                self.timeout = 60  # Just update every 1 minute
                self.last_update = now
                return
            log.debug("Updating queue client.")
            try:
                await self._check_queue_status()
            except comm_base.RequestTimeoutError as e:
                # If we can't reach the server, wait for a minute and retry
                self.timeout = min(60, self.timeout * 2)
                log.warn(str(e))
                warnings.warn(str(e))
                log.info(f"Retrying in {self.timeout} seconds.")
            else:
                # Update succeeded, so wait for a bit
                self.timeout = self.min_timeout
            finally:
                self.last_update = now

    @asyncSlot(bool)
    async def request_pause(self, *args, defer: bool = True, **kwargs):
        """Ask the queueserver run engine to pause.

        Parameters
        ==========
        defer
          If true, the run engine will be paused at the next
          checkpoint. Otherwise, it will pause now.

        """
        option = "deferred" if defer else "immediate"
        await self.api.re_pause(option=option)

    @asyncSlot(object)
    async def add_queue_item(self, item):
        log.info(f"Client adding item to queue: {item}")
        try:
            result = await self.api.item_add(item=item)
            self.check_result(result)
        except (RuntimeError, comm_base.RequestFailedError) as ex:
            # Request failed, so force a UI update
            await self.check_queue_status(force=True)
            raise
        else:
            await self.check_queue_status(force=False)

    @asyncSlot(bool)
    async def toggle_autostart(self, enable: bool):
        log.debug(f"Toggling auto-start: {enable}")
        try:
            result = await self.api.queue_autostart(enable)
            self.check_result(result, task="toggle auto-start")
        except (RuntimeError, comm_base.RequestFailedError):
            # Request failed, so force a UI update
            await self.check_queue_status(force=True)
        else:
            await self.check_queue_status(force=False)

    @asyncSlot(bool)
    async def stop_queue(self, stop: bool):
        """Turn on/off whether the queue will stop after the current plan."""
        # Determine which call to usee
        if stop:
            api_call = self.api.queue_stop()
        else:
            api_call = self.api.queue_stop_cancel()
        # Execute the call
        try:
            result = await api_call
            self.check_result(result, task="toggle stop queue")
        except (RuntimeError, comm_base.RequestFailedError):
            # Request failed, so force a UI update
            await self.check_queue_status(force=True)
        else:
            await self.check_queue_status(force=False)

    @asyncSlot()
    async def start_queue(self):
        result = await self.api.queue_start()
        self.check_result(result, task="start queue")

    @asyncSlot()
    async def resume_runengine(self):
        result = await self.api.re_resume()
        self.check_result(result, task="resume run engine")

    @asyncSlot()
    async def stop_runengine(self):
        result = await self.api.re_stop()
        self.check_result(result, task="stop run engine")

    @asyncSlot()
    async def abort_runengine(self):
        result = await self.api.re_abort()
        self.check_result(result, task="abort run engine")

    @asyncSlot()
    async def halt_runengine(self):
        result = await self.api.re_halt()
        self.check_result(result, task="halt run engine")

    def check_result(self, result: Mapping, task: str = "control queue server"):
        """Send the result of an API call to the correct logger.

        Expects *result* to have at least the "success" key.

        """
        # Report results
        if result["success"] is True:
            log.debug(f"{task}: {result}")
        else:
            msg = f"Failed to {task}: {result}"
            log.error(msg)
            raise RuntimeError(msg)

    @asyncSlot()
    async def check_queue_status(self, force=False, *args, **kwargs):
        """Get an update queue status from queue server and notify slots.

        Parameters
        ==========
        force
          If false (default), the ``queue_status_changed`` signal will
          be emitted only if the queue status has changed since last
          check.
        *args, *kwargs
          Unused arguments from qt widgets

        Emits
        =====
        self.status_changed
          With the updated queue status.

        """
        try:
            await self._check_queue_status(force=force)
        except comm_base.RequestTimeoutError as e:
            log.warning(str(e))
            warnings.warn(str(e))

    async def _check_queue_status(self, force: bool = False):
        """Get an update queue status from queue server and notify slots.

        Similar to ``check_queue_status`` but without the exception
        handling.

        Parameters
        ==========
        force
          If false (default), the ``queue_status_changed`` signal will
          be emitted only if the queue status has changed since last
          check.

        Emits
        =====
        self.status_changed
          With the updated queue status.

        """
        new_status = await self.api.status()
        # Add a new key for whether the queue is busy (length > 0 or running)
        has_queue = new_status["items_in_queue"] > 0
        is_running = new_status["manager_state"] in [
            "paused",
            "starting_queue",
            "executing_queue",
            "executing_task",
        ]
        new_status.setdefault("in_use", has_queue or is_running)
        # Check individual components of the status if they've changed
        signals_to_check = [
            # (status key, signal to emit)
            ("worker_environment_exists", self.environment_opened),
            ("worker_environment_state", self.environment_state_changed),
            ("manager_state", self.manager_state_changed),
            ("re_state", self.re_state_changed),
            ("items_in_queue", self.length_changed),
            ("in_use", self.in_use_changed),
            ("queue_stop_pending", self.queue_stop_changed),
            ("queue_autostart_enabled", self.autostart_changed),
        ]
        if force:
            log.debug(f"Forcing queue server status update: {new_status}")
        for key, signal in signals_to_check:
            is_new = key not in self._last_queue_status
            has_changed = new_status[key] != self._last_queue_status.get(key)
            if is_new or has_changed or force:
                signal.emit(new_status[key])
        # Check for new available devices
        if new_status["devices_allowed_uid"] != self._last_queue_status.get(
            "devices_allowed_uid"
        ):
            await self.update_devices()
        # check the whole status to see if it's changed
        has_changed = new_status != self._last_queue_status
        if has_changed or force:
            self.status_changed.emit(new_status)
            self._last_queue_status = new_status

    async def update_devices(self):
        "Emit the latest dict of available devices."
        response = await self.api.devices_allowed()
        if response["success"]:
            devices = response["devices_allowed"]
            self.devices_changed.emit(devices)
        else:
            log.warning(
                "Could not poll devices_allowed:"
                f" {response.get('msg', 'reason unknown.')}"
            )


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2023, UChicago Argonne, LLC
#
# Distributed under the terms of the 3-Clause BSD License
#
# The full license is in the file LICENSE, distributed with this software.
#
# DISCLAIMER
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# -----------------------------------------------------------------------------
