import shutil
import subprocess
import time
import warnings
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from bluesky_queueserver_api.comm_base import RequestTimeoutError
from bluesky_queueserver_api.zmq import REManagerAPI

CONFIG = """
uvicorn:
  host: {host}
  port: {port}

authentication:
  allow_anonymous_access: true
  single_user_api_key: "{api_key}"

trees:
  - path: /
    tree: catalog
    args:
      uri: "sqlite:///{catalog_path}"
      writable_storage: "{storage_path}"
      # This creates the database if it does not exist. This is convenient, but in
      # a horizontally-scaled deployment, this can be a race condition and multiple
      # containers may simultaneously attempt to create the database.
      # If that is a problem, set this to false, and run:
      #
      # tiled catalog init URI
      #
      # separately.
      init_if_not_exists: true
"""


TICK = 0.2  # Seconds between check-ins with the server


@dataclass()
class QserverInfo:
    bluesky_dir: Path
    host: str = "127.0.0.1"
    control_port: str = "8719"
    info_port: str = ""
    Popen: subprocess.Popen | None = None
    api: REManagerAPI | None = None

    @property
    def control_addr(self):
        return f"tcp://{self.host}:{self.control_port}"

    @property
    def info_addr(self):
        return f"tcp://{self.host}:{self.info_port}"

    def start(self) -> None:
        """Start a simple bluesky queue server for testing."""
        qserver_cmd = shutil.which("start-re-manager")
        if qserver_cmd is None:
            raise RuntimeError("Could not locate binary for `start-re-manager`.")
        script_dir = Path(__file__).parent.parent.parent / "src" / "haven_qserver"
        cmds: Sequence[str] = [
            qserver_cmd,
            "--config",
            str(script_dir / "qs_config.yml"),
            "--existing-plans-devices",
            str(self.bluesky_dir / "queueserver_existing_plans_and_devices.yaml"),
            "--user-group-permissions",
            str(script_dir / "queueserver_user_group_permissions.yaml"),
            "--redis-addr",
            "localhost:6379",
            "--redis-name-prefix",
            "qserver_tests",
        ]
        self.Popen = subprocess.Popen(cmds)

    def connect(self, timeout: int | float = 30) -> REManagerAPI:
        if self.api is None:
            self.api = REManagerAPI()
        t0 = time.monotonic()
        while (time.monotonic() - t0) < timeout:
            try:
                response = self.api.ping()
            except RequestTimeoutError:
                time.sleep(TICK)
                continue
            break
        else:
            raise RuntimeError(
                f"queue server at {self.control_addr} ({self.info_addr}) did not start with {timeout} seconds."
            )
        return self.api

    def open_environment(self, timeout: int | float = 20) -> None:
        environment_is_open = None
        api = self.connect()
        result = api.environment_open()
        assert result["success"]
        # Poll the qserver until the environment is successfully opened
        t0 = time.monotonic()
        while (time.monotonic() - t0) < timeout:
            if api.status()["worker_environment_exists"]:
                break
            time.sleep(TICK)
        else:
            raise RuntimeError(
                f"Qserver environment at {self.control_addr} ({self.info_addr}) did not open with {timeout} seconds."
            )

    def stop(self) -> None:
        """End a Tiled server started with *start_server()*."""
        qserver_process = self.Popen
        if qserver_process is None:
            warnings.warn("Cannot stop server that was not started.")
            return
        qserver_process.terminate()
        try:
            qserver_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            # Something went wrong, kill it the hard way
            qserver_process.kill()

    def run_queue(self):
        result = self.api.queue_start()
        assert result["success"]
        is_idle = False
        tick = 0.1
        while not is_idle:
            is_idle = self.api.status()["manager_state"] == "idle"
            time.sleep(tick)


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2025, UChicago Argonne, LLC
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
