import pytest

from .tiled_server import start_server, stop_server

TILED_PROFILES = """
tiled_read_only:
  uri: {uri}
tiled_writable:
  uri: {uri}?api_key={api_key}
"""


@pytest.fixture()
def tiled_server(tmp_path, mocker):
    # Start the tiled server
    server_info = start_server(tmp_path)
    # Set up the profiles corresponding to the server
    profile_dir = tmp_path / "tiled" / "profiles"
    profile_dir.mkdir(parents=True)
    mocker.patch("tiled.profiles.paths", [profile_dir])
    with open(profile_dir / "default.yml", mode="w") as fp:
        fp.write(
            TILED_PROFILES.format(uri=server_info.uri, api_key=server_info.api_key)
        )
    # Execute tests
    try:
        yield server_info
    finally:
        stop_server(server_info)


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
