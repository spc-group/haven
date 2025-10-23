import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

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
class TiledServerInfo:
    host: str = "127.0.0.1"
    port: str = "8719"
    Popen: subprocess.Popen | None = None
    scheme: str = "http://"
    api_key: str = "secret"

    @property
    def uri(self):
        return f"{self.scheme}{self.host}:{self.port}"


def ensure_server_not_running(uri):
    # Make sure the server is not running already
    try:
        httpx.get(uri)
    except httpx.ConnectError:
        pass
    else:
        raise RuntimeError(f"Tiled server already running at {uri}.")


def wait_for_server(uri: str, timeout=10):
    t0 = time.monotonic()
    while (time.monotonic() - t0) < timeout:
        try:
            response = httpx.get(uri)
        except httpx.ConnectError:
            continue
        else:
            response.raise_for_status()
            break
    else:
        raise RuntimeError(
            f"Tiled server at {uri} did not start with {timeout} seconds."
        )


def start_server(storage_path: Path) -> TiledServerInfo:
    """Start a simple empty tiled server for testing.

    catalog_path
      Where to create the sqlite catalog.

    """
    catalog_path = storage_path / "catalog.db"
    server_info = TiledServerInfo()
    # Write the configuration file
    config_str = CONFIG.format(
        catalog_path=catalog_path,
        storage_path=storage_path,
        port=server_info.port,
        host=server_info.host,
        api_key=server_info.api_key,
    )
    config_file = storage_path / "server_config.yml"
    with open(config_file, mode="w") as fd:
        fd.write(config_str)
    ensure_server_not_running(server_info.uri)
    # Launch the Tiled server
    tiled_exe = shutil.which("tiled")
    assert tiled_exe is not None
    tiled_cmd = [tiled_exe, "serve", "config"]
    server_info.Popen = subprocess.Popen(
        tiled_cmd, env={"TILED_CONFIG": str(config_file)}
    )
    # Wait for the server to spin up
    wait_for_server(server_info.uri, timeout=30)
    return server_info


def stop_server(server_info: TiledServerInfo):
    """End a Tiled server started with *start_server()*."""
    tiled_process = server_info.Popen
    if tiled_process is None:
        raise TypeError("Cannot stop server that was not started.")
    tiled_process.terminate()
    try:
        tiled_process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        # Something went wrong, kill it the hard way
        tiled_process.kill()


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
