from firefly.plans.xafs_scan import XafsScanDisplay


def test_region_number(qtbot):
    """Does changing the region number affect the UI?"""
    disp = XafsScanDisplay()
    qtbot.addWidget(disp)
    # Check that the display has the right number of rows to start with
    assert disp.ui.regions_spin_box.value() == 3
    assert hasattr(disp, "regions")
    assert len(disp.regions) == 3
    # Check that regions can be inserted and removed


def test_region(qtbot):
    """Does changing the region ui respond the way it should."""
    disp = XafsScanDisplay()
    qtbot.addWidget(disp)
    # Does the k-space checkbox enable the k-weight edit line
    region = disp.regions[0]
    region.k_space_checkbox.setChecked(True)
    assert region.k_weight_line_edit.isEnabled() is True


def test_E0_checkbox(qtbot):
    """Does selecting the E0 checkbox adjust the UI properly?"""
    disp = XafsScanDisplay()
    qtbot.addWidget(disp)
    # K-space checkboxes should be disabled when E0 is unchecked
    disp.ui.use_edge_checkbox.setChecked(False)
    assert not disp.regions[0].k_space_checkbox.isEnabled()
    # K-space checkbox should become re-enabled after E0 is checked
    disp.ui.use_edge_checkbox.setChecked(True)
    assert disp.regions[0].k_space_checkbox.isEnabled()
    # Checked k-space boxes should be unchecked when the E0 is disabled
    disp.regions[0].k_space_checkbox.setChecked(True)
    disp.ui.use_edge_checkbox.setChecked(False)
    disp.regions[0].k_space_checkbox.setChecked(False)
    assert not disp.regions[0].k_space_checkbox.isChecked()


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
