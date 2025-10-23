import importlib
from pathlib import Path

import pytest
from bluesky import RunEngine
from bluesky.callbacks.tiled_writer import TiledWriter

ICONFIG_DIR = Path(__file__).parent / "iconfig"
REPO_DIR = Path(__file__).parent.parent.parent
STARTUP_FILE = REPO_DIR / "src" / "haven" / "startup.py"


BASE_CONFIG = """
area_detector_root_path = "/tmp"

# Metadata from the beamline scheduling system (BSS)
####################################################

[bss]
uri = "https://localhost:12345/dm"
beamline = "255-ID-Z"
station_name = "255IDZ"
username = "s255idzuser"
password = "abc123"


##############
# Acquisition
##############

# This section describes how to connect to the queueserver and how
# queueserver data reaches the database. It does not generate any
# devices, but is intended to be read by the queueserver and Firefly
# GUI application to determine how to interact with the queue.

[ RUN_ENGINE.DEFAULT_METADATA ]
# Additional metadata to inject in every scan
facility = "Advanced Photon Source"
beamline = "SPC Beamline (sector unknown)"
xray_source = "2.8 mm planar undulator"
"""


TILED_CONFIG = """
[tiled]
default_catalog = "tiled_read_only"
cache_filepath = "/tmp/tiled/http_response_cache.db"
writer_profile = "tiled_writable"
# writer_backup_directory = "/tmp/tiled_writer_backup"
# writer_batch_size = 5
"""


@pytest.fixture()
def iconfig_file(monkeypatch, tmp_path):
    cfg_file = tmp_path / "iconfig.toml"
    monkeypatch.setenv("HAVEN_CONFIG_FILES", str(cfg_file))
    return cfg_file


@pytest.fixture()
def iconfig_simple(iconfig_file):
    with open(iconfig_file, mode="a") as fp:
        fp.write(BASE_CONFIG)
    return iconfig_file


@pytest.fixture()
def iconfig_tiled(iconfig_file):
    with open(iconfig_file, mode="a") as fp:
        fp.write(BASE_CONFIG)
        fp.write(TILED_CONFIG)
    return iconfig_file


@pytest.mark.slow
def test_loads_run_engine(iconfig_simple):
    # Load the startup module
    spec = importlib.util.spec_from_file_location("startup", STARTUP_FILE)
    startup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(startup)
    # Check that the run engine was created
    assert isinstance(startup.RE, RunEngine)


@pytest.mark.slow
def test_loads_tiled(iconfig_tiled, tiled_server):
    # Load the startup module
    spec = importlib.util.spec_from_file_location("startup", STARTUP_FILE)
    startup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(startup)
    # Check that 1 tiled writer was added
    callback_maps = [
        cbs.values() for cbs in startup.RE.dispatcher.cb_registry.callbacks.values()
    ]
    callbacks = {proxy.func for cbs in callback_maps for proxy in cbs}
    tiled_writers = [cb for cb in callbacks if isinstance(cb, TiledWriter)]
    assert len(tiled_writers) == 1
    writer = list(tiled_writers)[0]
    assert writer.client.context.api_uri == f"{tiled_server.uri}/api/v1/"
    writer.client.context.close()


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
