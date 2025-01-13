import gc

import databroker
import pytest
from bluesky import RunEngine
from ophyd.sim import instantiate_fake_device

from haven import run_engine
from haven.devices.aps import ApsMachine


@pytest.fixture()
def aps(sim_registry):
    aps = instantiate_fake_device(ApsMachine, name="advanced_photon_source")


def test_subscribers_garbage_collection(monkeypatch, aps):
    """Tests for regression of a bug in databroker.

    Since databroker uses a weak reference to the insert function, it
    can be subject to garbage collection and no longer able to save
    data.

    """
    monkeypatch.setattr(databroker, "catalog", {"bluesky": databroker.temp()})
    RE = run_engine(
        use_bec=False, connect_tiled=False, connect_databroker=True, connect_kafka=False
    )
    assert len(RE.dispatcher.cb_registry.callbacks) == 12
    gc.collect()
    assert len(RE.dispatcher.cb_registry.callbacks) == 12


def test_run_engine_preprocessors(aps):
    RE = run_engine(
        use_bec=False,
        connect_databroker=False,
        connect_tiled=False,
        connect_kafka=False,
    )
    assert len(RE.preprocessors) > 0


def test_run_engine_created(aps):
    RE = run_engine(
        use_bec=False,
        connect_databroker=False,
        connect_tiled=False,
        connect_kafka=False,
    )
    assert isinstance(RE, RunEngine)


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
