import importlib
import time
from collections.abc import Mapping
from pathlib import Path

import pytest

from haven import _iconfig, exceptions
from haven._iconfig import Configuration, FeatureFlag, load_config, print_config_value

next_month = time.time() + 30 * 24 * 3600


def test_default_values():
    """Do we pull in the testing TOML file by default?"""
    config = load_config()
    assert "RUN_ENGINE" in config.keys()


def test_loading_a_file():
    test_file = Path(__file__).resolve().parent / "test_iconfig.toml"
    config = load_config(test_file)
    assert config["beamline"]["pv_prefix"] == "spam"


def test_config_files_from_env(monkeypatch):
    # Set the environmental variable with the path to a test TOML file
    test_file = Path(__file__).resolve().parent / "test_iconfig.toml"
    monkeypatch.setenv("HAVEN_CONFIG_FILES", str(test_file))
    importlib.reload(_iconfig)
    # Load the configuration
    importlib.reload(_iconfig)
    config = _iconfig.load_config()
    # Check that the test file was loaded
    assert config["beamline"]["pv_prefix"] == "spam"


def test_merging_dicts():
    """Do the entries from multiple dictioneries merge properly?"""
    this_dir = Path(__file__).resolve().parent
    default_files = [
        this_dir.parent.parent / "src" / "haven" / "iconfig_testing.toml",
    ]
    print(default_files)
    test_file = this_dir / "test_iconfig.toml"
    config = load_config(*default_files, test_file)
    assert "prefix" in config["area_detector"][0].keys()


def test_haven_config_cli(capsys):
    """Test the function used as a CLI way to get config values."""
    print_config_value(["RUN_ENGINE.DEFAULT_METADATA.xray_source"])
    # Check stdout for config value
    captured = capsys.readouterr()
    assert captured.out == "2.8\u202fmm planar undulator\n"


def test_loads_config_mapping():
    config = load_config({})
    assert isinstance(config, Mapping)


def test_dotted_indexing():
    config = load_config(
        {
            "spam": {
                "eggs": 5,
            },
        }
    )
    assert config["spam.eggs"] == 5


def test_dotted_get():
    config = load_config(
        {
            "spam": {
                "eggs": 5,
            },
        }
    )
    assert config.get("spam.eggs") == 5


def test_get_default():
    config = load_config(
        {
            "spam": {
                "eggs": 5,
            },
        }
    )
    assert config.get("spam.eggs") == 5


def test_nested_indexing():
    config = load_config(
        {
            "spam": {
                "eggs": {
                    "cheese": {
                        "shop": 5,
                    },
                },
            },
        }
    )
    assert config["spam.eggs"]["cheese.shop"] == 5


def test_dotted_keys():
    """What if a key actually has a dot in it?"""
    config = load_config(
        {
            "spam.eggs": {"cheese.shop": 5},
        },
    )
    assert config["spam.eggs.cheese.shop"] == 5


def test_iterate_keys():
    config = load_config({"hello": "spam"})
    iterated_keys = [k for k in config]
    assert iterated_keys == ["hello"]


def test_iterate_nested_keys():
    """We don't actually want to iterate over the nested keys, so just
    make sure we don't.

    """
    config = load_config({"hello": {"spam": "eggs"}})
    iterated_keys = [k for k in config]
    assert iterated_keys == ["hello"]


@pytest.fixture()
def config():
    config = Configuration(
        {
            "haven.feature_flags": {
                "spam": True,
            },
        },
        feature_flags={"spam": FeatureFlag(expires=next_month)},
    )
    return config


def test_feature_flag(config):
    assert config.feature_flag("spam") is True


def test_feature_flag_default():
    config = Configuration(
        feature_flags={"spam": FeatureFlag(default="eggs", expires=next_month)}
    )
    assert config.feature_flag("spam") == "eggs"


def test_feature_flag_decorator(mocker, config):
    mock = mocker.MagicMock()

    @config.with_feature_flag("spam", alternate=mock)
    def inner():
        assert False, "Feature flag not applied."

    inner("hello")
    mock.assert_called_once_with("hello")


def test_get_undeclared_feature_flag(config):
    """Do we raise an exception if getting a feature flag that is not declared?"""
    config._feature_flags = {}
    with pytest.raises(exceptions.UndeclaredFeatureFlag):
        config.feature_flag("spam")


def test_set_undeclared_feature_flag():
    """Do we raise an exception if we use a feature flag that is not declared?"""
    config = Configuration(
        {"haven.feature_flags": {"spam": True}},
        feature_flags={},
    )
    with pytest.raises(exceptions.UndeclaredFeatureFlag):
        config.feature_flag("spam")


def test_expired_feature_flag():
    now = time.time()
    config = Configuration(
        {}, feature_flags={"spam": FeatureFlag(default="eggs", expires=now - 3600)}
    )
    with pytest.warns(exceptions.ExpiredFeatureFlag):
        config.feature_flag("spam")


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
