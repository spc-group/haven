from unittest import mock

import pytest
from bluesky import Msg, RunEngine
from bluesky import plan_stubs as bps

from haven import load_config, run_engine


def test_run_engine_created():
    RE = run_engine(
        connect_tiled=False,
    )
    assert isinstance(RE, RunEngine)


@pytest.mark.slow
def test_calibrate_message():
    device = mock.AsyncMock()
    RE = run_engine(
        connect_tiled=False,
    )
    assert not device.calibrate.called
    RE([Msg("calibrate", device, truth=1304, target=1314)])
    assert device.calibrate.called


@pytest.mark.slow
def test_default_metadata():
    docs = []

    def stash_docs(name, doc):
        docs.append((name, doc))

    RE = run_engine(connect_tiled=False)
    RE.subscribe(stash_docs)

    RE(bps.open_run())
    start_doc = docs[0][1]
    # Check that metadata matches iconfig_testing.toml
    default_md = load_config()["RUN_ENGINE.DEFAULT_METADATA"]
    assert start_doc["facility"] == default_md["facility"]
    assert start_doc["beamline"] == default_md["beamline"]
    assert start_doc["xray_source"] == default_md["xray_source"]


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
