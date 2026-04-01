import pytest_asyncio

from haven.devices import SplitIonChamberSet


@pytest_asyncio.fixture()
async def ion_chamber():
    ic = SplitIonChamberSet(prefix="255id:tetra:QUAD1:", name="Ipreslit")
    await ic.connect(mock=True)
    return ic


async def test_reading_signals(ion_chamber):
    await ion_chamber.trigger()
    reading = await ion_chamber.read()
    assert set(reading.keys()) == {
        # Global
        "Ipreslit-current",
        # Sets of ion chamber channels
        "Ipreslit-vertical-current",
        "Ipreslit-vertical-difference",
        "Ipreslit-vertical-position",
        "Ipreslit-horizontal-current",
        "Ipreslit-horizontal-difference",
        "Ipreslit-horizontal-position",
        # Individual channels
        "Ipreslit-vertical-positive_plate-current",
        "Ipreslit-vertical-negative_plate-current",
        "Ipreslit-horizontal-negative_plate-current",
        "Ipreslit-horizontal-positive_plate-current",
    }


async def test_hinted_signals(ion_chamber):
    await ion_chamber.trigger()
    hints = set(ion_chamber.hints["fields"])
    assert hints == {
        "Ipreslit-current",
    }

    # Hints
    hints = set(ion_chamber.hints["fields"])
    assert hints == {
        "Ipreslit-current",
    }


async def test_configuration_signals(ion_chamber):
    await ion_chamber.trigger()
    hints = set(ion_chamber.hints["fields"])
    assert hints == {
        "Ipreslit-current",
    }

    # Hints
    config = await ion_chamber.read_configuration()
    assert set(config.keys()) == {
        "Ipreslit-driver-acquire_mode",
        "Ipreslit-driver-bias_interlock",
        "Ipreslit-driver-bias_voltage",
        "Ipreslit-driver-bias_voltage_actual",
        "Ipreslit-driver-current_range",
        "Ipreslit-driver-firmware",
        "Ipreslit-driver-geometry",
        "Ipreslit-driver-model",
        "Ipreslit-driver-read_format",
        "Ipreslit-driver-sample_time",
        "Ipreslit-driver-trigger_mode",
        "Ipreslit-driver-trigger_polarity",
        "Ipreslit-vertical-position_offset",
        "Ipreslit-vertical-position_scale",
        "Ipreslit-vertical-precision",
        "Ipreslit-horizontal-position_offset",
        "Ipreslit-horizontal-position_scale",
        "Ipreslit-horizontal-precision",
        "Ipreslit-vertical-positive_plate-offset",
        "Ipreslit-vertical-positive_plate-scale",
        "Ipreslit-vertical-positive_plate-precision",
        "Ipreslit-vertical-negative_plate-offset",
        "Ipreslit-vertical-negative_plate-scale",
        "Ipreslit-vertical-negative_plate-precision",
        "Ipreslit-horizontal-positive_plate-offset",
        "Ipreslit-horizontal-positive_plate-scale",
        "Ipreslit-horizontal-positive_plate-precision",
        "Ipreslit-horizontal-negative_plate-offset",
        "Ipreslit-horizontal-negative_plate-scale",
        "Ipreslit-horizontal-negative_plate-precision",
    }


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
