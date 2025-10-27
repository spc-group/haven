import pytest
import pytest_asyncio

from .qserver import QserverInfo
from .tiled_server import TiledServerInfo

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


DEVICES_CONFIG = """
[[ "ophyd_async.sim.SimMotor" ]]
name = "sim_async_motor"

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
        fp.write(DEVICES_CONFIG)
    return iconfig_file


@pytest.fixture()
def iconfig_tiled(iconfig_file):
    with open(iconfig_file, mode="a") as fp:
        fp.write(BASE_CONFIG)
        fp.write(TILED_CONFIG)
    return iconfig_file


TILED_PROFILES = """
tiled_read_only:
  uri: {uri}
tiled_writable:
  uri: {uri}?api_key={api_key}
"""


@pytest.fixture()
def tiled_server(tmp_path, mocker):
    server_info = TiledServerInfo(tmp_path)
    # Start the tiled server
    # Set up the profiles corresponding to the server
    profile_dir = tmp_path / "tiled" / "profiles"
    profile_dir.mkdir(parents=True)
    mocker.patch("tiled.profiles.paths", [profile_dir])
    with open(profile_dir / "default.yml", mode="w") as fp:
        fp.write(
            TILED_PROFILES.format(uri=server_info.uri, api_key=server_info.api_key)
        )
    try:
        server_info.start()
        # Execute tests
        yield server_info
    finally:
        # Make sure the server gets cleaned up when we're done
        server_info.stop()


@pytest_asyncio.fixture()
async def qserver(tmp_path, monkeypatch, redisdb, iconfig_simple):
    monkeypatch.setenv("BLUESKY_DIR", str(tmp_path))

    # Execute tests
    server_info = QserverInfo(bluesky_dir=tmp_path)
    try:
        # Start the tiled server
        server_info.start()
        server_info.open_environment()
        # server_info = await start_qserver(bluesky_dir=tmp_path, redisdb=redisdb)
        yield server_info
    finally:
        server_info.stop()


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
