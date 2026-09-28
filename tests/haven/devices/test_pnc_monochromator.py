import pytest_asyncio
from bluesky import protocols
from ophyd_async.testing import assert_value

from haven.devices import PNCMonochromator as Monochromator

# Calibrate energy: 20bm:mono_cal.E


@pytest_asyncio.fixture()
async def mono():
    mono = Monochromator(
        prefix="255bm:",
        bragg_motor="255bm:m1",
        roll2_motor="255bm:m2",
        pitch2_motor="255bm:m2",
        xtal2_translation_motor="255bm:m2",
        name="monochromator",
    )
    await mono.connect(mock=True)
    return mono


async def test_signals(mono):
    reading = await mono.read()
    print(reading)
    assert set(reading.keys()) == {
        "monochromator-bragg",
        "monochromator-energy",
        "monochromator-pitch2",
        "monochromator-roll2",
        "monochromator-xtal2_translation",
    }
    assert set(mono.hints["fields"]) == {
        "monochromator-bragg",
        "monochromator-energy",
    }
    config = await mono.read_configuration()
    assert set(config.keys()) == {
        # Commented signals are copied from Axilon mono tests and
        # could be added later.
        "monochromator-bragg-description",
        "monochromator-bragg-motor_egu",
        "monochromator-bragg-offset",
        "monochromator-bragg-offset_dir",
        "monochromator-bragg-velocity",
        "monochromator-d_spacing",
        "monochromator-d_spacing_unit",
        "monochromator-bragg-encoder_resolution",
        "monochromator-bragg-motor_resolution",
        "monochromator-bragg-steps_per_revolution",
        "monochromator-bragg-units_per_revolution",
    }


async def test_mono_energy_mover(mono):
    # Check PVs are correct
    await mono.energy.set(8831)
    await assert_value(mono.energy.setpoint, 8831)


def test_interfaces(mono):
    assert isinstance(mono, protocols.Readable)


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2026, UChicago Argonne, LLC
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
