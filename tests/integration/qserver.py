import shutil
import subprocess
import time
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


@dataclass()
class QserverInfo:
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


# def ensure_server_not_running(uri):
#     # Make sure the server is not running already
#     try:
#         httpx.get(uri)
#     except httpx.ConnectError:
#         pass
#     else:
#         raise RuntimeError(f"Tiled server already running at {uri}.")


def connect_to_server(info: QserverInfo, timeout=10):
    api = REManagerAPI()
    t0 = time.monotonic()
    while (time.monotonic() - t0) < timeout:
        try:
            response = api.ping()
        except RequestTimeoutError:
            continue
        break
    else:
        raise RuntimeError(
            f"Tiled server at {info.control_addr} ({info.info_addr}) did not start with {timeout} seconds."
        )
    return api


def open_environment(qserver_info: QserverInfo):
    environment_is_open = None
    if qserver_info.api is None:
        raise TypeError("Cannot open environment on qserver that was not started.")
    while not environment_is_open:
        if environment_is_open is None:
            result = qserver_info.api.environment_open()
            assert result["success"]
        time.sleep(0.5)
        environment_is_open = qserver_info.api.status()["worker_environment_exists"]


async def start_qserver(bluesky_dir: Path, redisdb) -> QserverInfo:
    """Start a simple bluesky queue server for testing."""
    server_info = QserverInfo()
    # Write the configuration file
    # config_str = CONFIG.format(
    #     catalog_path=catalog_path,
    #     storage_path=storage_path,
    #     port=server_info.port,
    #     host=server_info.host,
    #     api_key=server_info.api_key,
    # )
    # config_file = storage_path / "server_config.yml"
    # with open(config_file, mode="w") as fd:
    #     fd.write(config_str)
    # ensure_server_not_running(server_info.uri)
    # Launch the Tiled server
    # cmd = [sys.executable, "-m", "haven_qserver.launch_queueserver"]
    # server_info.Popen = subprocess.Popen(
    #     cmd, env={"BLUESKY_DIR": str(bluesky_dir)}
    # )
    qserver_cmd = shutil.which("start-re-manager")
    if qserver_cmd is None:
        raise RuntimeError("Could not locate binary for `start-re-manager`.")
    script_dir = Path(__file__).parent.parent.parent / "src" / "haven_qserver"
    cmds: Sequence[str] = [
        qserver_cmd,
        "--config",
        str(script_dir / "qs_config.yml"),
        "--existing-plans-devices",
        str(bluesky_dir / "queueserver_existing_plans_and_devices.yaml"),
        "--user-group-permissions",
        str(script_dir / "queueserver_user_group_permissions.yaml"),
        "--redis-addr",
        "localhost:6379",
        "--redis-name-prefix",
        "qserver_tests",
    ]
    # server_info.Popen = asyncio.ensure_future(asyncio.to_thread(launch_queueserver))
    server_info.Popen = subprocess.Popen(cmds)
    # Wait for the server to spin up
    server_info.api = connect_to_server(server_info, timeout=30)
    open_environment(server_info)
    return server_info


def stop_qserver(server_info: QserverInfo):
    """End a Tiled server started with *start_server()*."""
    print("STOPPING")
    # server_info.task.cancel()
    # try:
    #     await server_info.task
    # except asyncio.CancelledError:
    #     print("Cleaned up")
    #     raise
    qserver_process = server_info.Popen
    if qserver_process is None:
        raise TypeError("Cannot stop server that was not started.")
    qserver_process.terminate()
    try:
        qserver_process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        # Something went wrong, kill it the hard way
        qserver_process.kill()


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
