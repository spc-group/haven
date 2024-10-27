from unittest.mock import MagicMock

import pandas as pd

from firefly.run_browser.widgets import Browser1DPlotWidget


async def test_plot_1d_runs(qtbot):
    widget = Browser1DPlotWidget()
    qtbot.addWidget(widget)
    assert len(widget.data_items) == 0
    # Set some runs
    widget.plot_runs({"hello": pd.Series(data=[10, 20, 30], index=[1, 2, 3])})
    assert "hello" in widget.data_items.keys()
    # Now update it again and check that the data item is reused
    mock_data_item = MagicMock()
    widget.data_items["hello"] = mock_data_item
    widget.plot_runs({"hello": pd.Series(data=[40, 50], index=[4, 5])})
    assert widget.data_items["hello"] is mock_data_item
    mock_data_item.setData.assert_called_once()




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

