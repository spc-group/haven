import logging
from typing import Mapping, Optional

from bluesky_queueserver_api import comm_base
from bluesky_queueserver_api.zmq.aio import REManagerAPI
from qasync import asyncSlot
from qtpy.QtCore import QObject, QTimer, Signal

from haven import load_config
from haven.exceptions import InvalidConfiguration

log = logging.getLogger()


def is_in_use(status):
    # Add a new key for whether the queue is busy (length > 0 or running)
    has_queue = status.get("items_in_queue", 0) > 0
    is_running = status.get("manager_state") in [
        "paused",
        "starting_queue",
        "executing_queue",
        "executing_task",
    ]
    return has_queue or is_running


def queueserver_api():
    try:
        config = load_config()["queueserver"]
        ctrl_addr = f"tcp://{config['control_host']}:{config['control_port']}"
        info_addr = f"tcp://{config['info_host']}:{config['info_port']}"
    except KeyError as e:
        raise InvalidConfiguration(str(e))
    api = REManagerAPI(zmq_control_addr=ctrl_addr, zmq_info_addr=info_addr)
    return api


def queue_status(status_mapping: Mapping[str, str] = {}):
    """A generative coroutine that tracks the status of the queueserver.

    Parameters
    ==========
    status_mapping
      Maps the queuestatus parameters that are sent onto the update
      signal names to yield

    Yields
    ======
    to_update
      Dictionary with signals to emit as keys, and tuples of ``*args``
      to emit as values. So ``{self.status_changed: ("spam",
      "eggs")}`` results in ``self.status_changed.emit("spam",
      "eggs")``.

    Sends
    =====
    status
      The most recent updated status from the queueserver.

    """
    to_update = {}
    last_status = {}
    was_in_use = None
    while True:
        status = yield to_update
        to_update = {}
        if status != last_status:
            to_update["status_changed"] = (status,)
        # Check individual status items to see if they've changed
        status_diff = {
            key: val
            for key, val in status.items()
            if key not in last_status or val != last_status[key]
        }
        log.debug(f"Received updated queue status: {status_diff}")
        updated_params = {
            status_mapping[key]: (val,)
            for key, val in status_diff.items()
            if key in status_mapping
        }
        to_update.update(updated_params)
        # Decide if the queue is being used
        now_in_use = is_in_use(status)
        if now_in_use != was_in_use:
            to_update["in_use_changed"] = (now_in_use,)
            was_in_use = now_in_use
        # Stash this status for the next time around
        last_status = status


class QueueClient(QObject):
    api: REManagerAPI
    _last_queue_status: Optional[dict] = None
    last_update: float = -1
    timeout: float = 0.5
    timer: QTimer
    parameter_mapping: Mapping[str, str] = {
        "queue_autostart_enabled": "autostart_changed",
        "worker_environment_exists": "environment_opened",
        "worker_environment_state": "environment_state_changed",
        "manager_state": "manager_state_changed",
        "re_state": "re_state_changed",
        "devices_allowed_uid": "devices_allowed_changed",
    }

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

    def __init__(self, *args, api, **kwargs):
        self.api = api
        super().__init__(*args, **kwargs)
        self._last_queue_status = {}
        # Setup timer for updating the queue
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        # Create the generator to keep track of the queue states
        self.status = queue_status(status_mapping=self.parameter_mapping)
        next(self.status)  # Prime the generator

    def start(self):
        # Start the time so that it triggers status updates
        self.timer.start(int(self.timeout * 1000))

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
            raise
        finally:
            await self.update()

    @asyncSlot(bool)
    async def toggle_autostart(self, enable: bool):
        log.debug(f"Toggling auto-start: {enable}")
        try:
            result = await self.api.queue_autostart(enable)
            self.check_result(result, task="toggle auto-start")
        finally:
            await self.update()

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
        finally:
            await self.update()

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
    async def update(self):
        """Get an update queue status from queue server and notify slots.

        Emits
        =====
        self.status_changed
          With the updated queue status.

        """
        new_status = await self.queue_status()
        signals_changed = self.status.send(new_status)
        # Check individual components of the status if they've changed
        if signals_changed != {}:
            log.debug(f"Emitting changed signals: {signals_changed}")
        for signal_name, args in signals_changed.items():
            if hasattr(self, signal_name):
                signal = getattr(self, signal_name)
                signal.emit(*args)
        # Check for new available devices
        if "devices_allowed_changed" in signals_changed:
            await self.update_devices()

    async def queue_status(self) -> dict:
        """Get the latest queue status from the queue server.

        Parameters
        ==========
        status
          The response from the queueserver regarding its status. If
          the queueserver is not reachable, then
          ``status['manager_state']`` will be ``"disconnected"``.

        """

        try:
            status = await self.api.status()
        except comm_base.RequestTimeoutError as e:
            log.warning("Could not reach queueserver ZMQ.")
            status = {
                "manager_state": "N.C.",
                "worker_environment_state": "N.C.",
                "re_state": "N.C.",
            }
        return status

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
