import pytest
import pytest_asyncio

from firefly.devices.attenuators import AttenuatorsDisplay
from haven.devices import PFCUFilterBank


@pytest_asyncio.fixture()
async def filters(sim_registry):
    filter_bank = PFCUFilterBank("255id:PFCU0:", name="filter_bank")
    await filter_bank.connect(mock=True)
    sim_registry.register(filter_bank)
    return [filter_bank.filters[0], filter_bank.filters[1]]


@pytest.mark.asyncio
async def test_embedded_display_widgets(qtbot, filters, sim_registry):
    """Test that the display creates a new embedded display widget for
    each filter.

    """
    # Load the display
    display = AttenuatorsDisplay()
    qtbot.addWidget(display)
    await display.update_devices(sim_registry)
    # Check that the embedded display widgets get added correctly
    assert hasattr(display, "_filter_displays")
    assert len(display._filter_displays) == 4
    assert display.filters_layout.count() == 4
    # Check that the embedded display widgets have the correct macros
    emb_disp = display._filter_displays[0]
    disp = emb_disp.open_file(force=True)
    macros = disp.macros()
    assert macros["DEV"].startswith("filter_bank-filters-")


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2024, UChicago Argonne, LLC
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
