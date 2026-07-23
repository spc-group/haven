import shutil
import signal
import subprocess
import warnings
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from mirakuru import TCPExecutor
from mirakuru.exceptions import TimeoutExpired

TICK = 0.2  # Seconds between check-ins with the server


@dataclass()
class QserverInfo:
    bluesky_dir: Path
    host: str = "127.0.0.1"
    control_port: str = "60715"
    info_port: str = "60725"
    Popen: subprocess.Popen | None = None
    executor: TCPExecutor | None = None

    @property
    def control_addr(self):
        return f"tcp://{self.host}:{self.control_port}"

    @property
    def info_addr(self):
        return f"tcp://{self.host}:{self.info_port}"

    def start(self) -> None:
        """Start a simple bluesky queue server for testing."""
        # if self.executor is not None:
        #     raise RuntimeError("qserver is already running")
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
            "localhost:6380",
            "--redis-name-prefix",
            "qserver_tests",
        ]
        cmd = " ".join(cmds)
        self.executor = TCPExecutor(
            cmd,
            host=self.host,
            port=int(self.control_port),
            timeout=60,
            stdout=1,  # For debugging
            stderr=2,  # For debugging
            stop_signal=signal.SIGINT,
            envvars={
                "QSERVER_ZMQ_CONTROL_ADDRESS_FOR_SERVER": self.control_addr,
                "QSERVER_ZMQ_INFO_ADDRESS_FOR_SERVER": self.info_addr,
            },
        )
        try:
            self.executor.start()
        except TimeoutExpired as exc:
            raise exc

    def stop(self) -> None:
        """End a Tiled server started with *start_server()*."""
        qserver_process = self.executor
        if qserver_process is None:
            warnings.warn("Cannot stop server that was not started.")
            return
        qserver_process.stop()


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
