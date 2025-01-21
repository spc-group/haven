import importlib
import os
from pathlib import Path

from haven import _iconfig
from haven._iconfig import load_config, print_config_value


def test_default_values():
    config = load_config()
    assert "beamline" in config.keys()


def test_loading_a_file():
    test_file = Path(__file__).resolve().parent / "test_iconfig.toml"
    config = load_config(file_paths=(test_file,))
    assert config["beamline"]["pv_prefix"] == "spam"


def test_config_files_from_env():
    # Set the environmental variable with the path to a test TOML file
    test_file = Path(__file__).resolve().parent / "test_iconfig.toml"
    old_env = os.environ["HAVEN_CONFIG_FILES"]
    os.environ["HAVEN_CONFIG_FILES"] = str(test_file)
    importlib.reload(_iconfig)
    try:
        # Load the configuration
        importlib.reload(_iconfig)
        config = _iconfig.load_config()
        # Check that the test file was loaded
        assert config["beamline"]["pv_prefix"] == "spam"
    finally:
        # Reset the old configuration to avoid breaking future tests
        os.environ["HAVEN_CONFIG_FILES"] = old_env
        importlib.reload(_iconfig)


def test_merging_dicts():
    """Do the entries from multiple dictioneries merge properly?"""
    this_dir = Path(__file__).resolve().parent
    default_files = [
        this_dir.parent / "iconfig_testing.toml",
    ]
    test_file = this_dir / "test_iconfig.toml"
    config = load_config(file_paths=(*default_files, test_file))
    assert "prefix" in config["area_detector"][0].keys()


def test_haven_config_cli(capsys):
    """Test the function used as a CLI way to get config values."""
    print_config_value(["xray_source.prefix"])
    # Check stdout for config value
    captured = capsys.readouterr()
    assert captured.out == "ID255ds:\n"


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
