import pytest
from ophyd.sim import make_fake_device

from firefly.kb_mirrors import KBMirrorsDisplay
from haven.devices.mirrors import KBMirrors


@pytest.fixture()
async def kb_mirrors(sim_registry):
    """A fake set of slits using the 4-blade setup."""
    kb = KBMirrors(
        prefix="255idc:KB:",
        name="kb_mirrors",
        horiz_upstream_motor="255idc:m1",
        vert_upstream_motor="255idc:m2",
        horiz_downstream_motor="255idc:m3",
        vert_downstream_motor="255idc:m4",
    )
    return kb


@pytest.fixture()
def kb_bendable_mirrors(sim_registry):
    """A fake set of slits using the 4-blade setup."""
    FakeMirrors = make_fake_device(KBMirrors)
    kb = FakeMirrors(
        prefix="255idc:Long_KB:",
        name="kb_bendable_mirrors",
        horiz_upstream_motor="255idc:m5",
        vert_upstream_motor="255idc:m6",
        horiz_downstream_motor="255idc:m7",
        vert_downstream_motor="255idc:m8",
        horiz_upstream_bender="255idc:m21",
        vert_upstream_bender="255idc:m22",
        horiz_downstream_bender="255idc:m23",
        vert_downstream_bender="255idc:m24",
    )
    sim_registry.register(kb)
    return kb


@pytest.fixture()
def display(kb_mirrors, qtbot):
    disp = KBMirrorsDisplay(macros={"DEVICE": kb_mirrors.name})
    qtbot.addWidget(disp)
    return disp


def test_bender_widgets(qtbot, kb_bendable_mirrors):
    display = KBMirrorsDisplay(macros={"DEVICE": kb_bendable_mirrors.name})
    qtbot.addWidget(display)
    # Check that the bender control widgets were enabled
    assert display.ui.horizontal_upstream_display.isEnabled()
    assert display.ui.horizontal_downstream_display.isEnabled()
    assert display.ui.vertical_upstream_display.isEnabled()
    assert display.ui.vertical_downstream_display.isEnabled()


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
