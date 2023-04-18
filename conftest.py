import subprocess
from subprocess import Popen, PIPE
import shutil
import time

import pytest

from firefly.application import FireflyApplication


def tiled_is_running(port, match_command=True):
    lsof = subprocess.run(["lsof", "-i", f":{port}", "-F"], capture_output=True)
    assert lsof.stderr.decode() == ""
    stdout = lsof.stdout.decode().split("\n")
    is_running = len(stdout) >= 3
    if match_command:
        is_running = is_running and stdout[3] == "ctiled"
    return is_running


@pytest.fixture(scope="session")
def sim_tiled():
    """Start a tiled server using production data from 25-ID."""
    timeout = 20
    port = 8337
    if tiled_is_running(port, match_command=False):
        raise RuntimeError(f"Port {port} is already in use.")
    tiled_bin = shutil.which("tiled")
    process = Popen([tiled_bin, "serve", "pyobject", "--public", "--port", "8337", "haven.tests.tiled_example:tree"], stdout=PIPE, stderr=PIPE)
    # Wait for start to complete
    for i in range(timeout):
        if tiled_is_running(port):
            break
        time.sleep(1.)
    else:
        # Timeout finished without startup or error
        process.kill()
        raise TimeoutError
    yield process
    # Shut down
    process.terminate()
    # Wait for start to complete
    for i in range(timeout):
        if not tiled_is_running(port):
            break
        time.sleep(1.)
    else:
        process.kill()
        time.sleep(1)
