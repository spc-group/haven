from haven.devices import (
    PTC10Controller,
    PTC10OutputChannel,
    PTC10RTDChannel,
    PTC10ThermocoupleChannel,
)


async def test_ptc10_output_signals():
    channel = PTC10OutputChannel(prefix="255idc:tc:", name="output")
    await channel.connect(mock=True)
    # Read signals
    reading = await channel.read()
    expected_signals = {
        "output-voltage",
        "output-setpoint",
        "output-ramp_temperature",
    }
    assert set(reading.keys()) == expected_signals
    # Config signals
    config = await channel.read_configuration()
    expected_config = {
        "output-high_limit",
        "output-low_limit",
        "output-io_type",
        "output-ramp_rate",
        "output-pid_enabled",
        "output-pid_mode",
        "output-P",
        "output-I",
        "output-D",
        "output-input_choice",
        "output-tune_lag",
        "output-tune_lag_step",
        "output-tune_mode",
        "output-tune_type",
    }
    assert set(config.keys()) == expected_config
    # Hints
    assert channel.hints == {}


async def test_ptc10_thermocouple_signals():
    tc = PTC10ThermocoupleChannel(prefix="255idc:tc:", name="tc")
    await tc.connect(mock=True)
    # Read signals
    reading = await tc.read()
    expected_signals = {
        "tc-temperature",
    }
    assert set(reading.keys()) == expected_signals
    # Config signals
    config = await tc.read_configuration()
    expected_config = {
        "tc-update_rate",
        "tc-description",
        "tc-sensor",
    }
    assert set(config.keys()) == expected_config
    # Hints
    assert set(tc.hints["fields"]) == {
        "tc-temperature",
    }


async def test_ptc10_rtd_signals():
    rtd = PTC10RTDChannel(prefix="255idc:tc:", name="rtd")
    await rtd.connect(mock=True)
    # Read signals
    reading = await rtd.read()
    expected_signals = {
        "rtd-temperature",
    }
    assert set(reading.keys()) == expected_signals
    # Config signals
    config = await rtd.read_configuration()
    expected_config = {
        "rtd-update_rate",
        "rtd-sensor",
        "rtd-range",
        "rtd-current",
        "rtd-power",
        "rtd-units",
    }
    assert set(config.keys()) == expected_config
    # Hints
    assert set(rtd.hints["fields"]) == {"rtd-temperature"}


async def test_ptc10_controller_signals():
    controller = PTC10Controller(prefix="255idc:tc:", name="controller")
    await controller.connect(mock=True)
    # Read signals
    reading = await controller.read()
    expected_signals = set()
    assert set(reading.keys()) == expected_signals
    # Config signals
    config = await controller.read_configuration()
    expected_config = {
        "controller-output_enable",
    }
    assert set(config.keys()) == expected_config
    # Hints
    assert controller.hints == {}


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
# ----------------------------------------------------------------------------
