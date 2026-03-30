import pytest
from bluesky import protocols
from ophyd_async.core import set_mock_value

from haven.devices.axilon_monochromator import AxilonMonochromator as Monochromator


async def mono():
    mono = Monochromator(prefix="255idMono:")
    await mono.connect(mock=True)
    return mono


async def test_signals(mono):
    reading = await mono.read()
    assert set(reading.keys()) == {
        "monochromator-beam_offset",
        "monochromator-bragg",
        "monochromator-energy",
        "monochromator-gap",
        "monochromator-horizontal",
        "monochromator-pitch2",
        "monochromator-roll2",
        "monochromator-vertical",
    }
    assert set(mono.hints["fields"]) == {
        "monochromator-bragg",
        "monochromator-energy",
    }
    config = await mono.read_configuration()
    assert set(config.keys()) == {
        "monochromator-bragg-description",
        "monochromator-bragg-motor_egu",
        "monochromator-bragg-offset",
        "monochromator-bragg-offset_dir",
        "monochromator-bragg-velocity",
        "monochromator-energy-description",
        "monochromator-energy-motor_egu",
        "monochromator-energy-offset",
        "monochromator-energy-offset_dir",
        "monochromator-energy-velocity",
        "monochromator-id_tracking",
        "monochromator-id_offset",
        "monochromator-d_spacing",
        "monochromator-d_spacing_unit",
        "monochromator-mode",
        "monochromator-transform_d_spacing",
        "monochromator-transform_direction",
        "monochromator-transform_offset",
    }


def test_mono_energy_signal(mono):
    # Check PVs are correct
    mono.energy.user_readback.source == "ca+mock://255idMono:Energy.RBV"


async def test_calibrate(mono):
    set_mock_value(mono.d_spacing, 3.134734)
    set_mock_value(mono.d_spacing_unit, "Angstroms")
    set_mock_value(mono.bragg.motor_egu, "arcsec")
    set_mock_value(mono.energy.motor_egu, "eV")
    # Pretend we're running 10eV higher than the true energy
    await mono.energy.calibrate(dial=8380, truth=8370)
    new_offset = await mono.transform_offset.get_value()
    assert new_offset == pytest.approx(59.84797)


async def test_calibrate_relative(mono):
    set_mock_value(mono.d_spacing, 3.134734)
    set_mock_value(mono.d_spacing_unit, "Angstroms")
    set_mock_value(mono.bragg.motor_egu, "arcsec")
    set_mock_value(mono.energy.motor_egu, "eV")
    set_mock_value(mono.transform_offset, 20)
    # Pretend we're running 10eV higher than the true energy
    await mono.energy.calibrate(dial=8380, truth=8370, relative=True)
    new_offset = await mono.transform_offset.get_value()
    assert new_offset == pytest.approx(79.84797)


def test_interfaces(mono):
    assert isinstance(mono, protocols.Readable)


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
