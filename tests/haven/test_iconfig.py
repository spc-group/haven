import importlib
import time
from pathlib import Path

import pytest

from haven import exceptions, iconfig
from haven.iconfig import Configuration, load_config
from haven.iconfig_schema import ConfigModel, FeatureFlag

next_month = time.time() + 30 * 24 * 3600


def test_default_values():
    """Do we set reasonable default values?"""
    config = load_config()
    assert config["area_detector_root_path"] == "/tmp"


def test_loading_a_file():
    test_file = Path(__file__).resolve().parent / "test_iconfig.toml"
    config = load_config(test_file)
    assert config["run_engine.default_metadata.facility"] == "Zero Gradient Synchrotron"


def test_config_files_from_env(monkeypatch):
    # Set the environmental variable with the path to a test TOML file
    test_file = Path(__file__).resolve().parent / "test_iconfig.toml"
    monkeypatch.setenv("HAVEN_CONFIG_FILES", str(test_file))
    importlib.reload(iconfig)
    # Load the configuration
    importlib.reload(iconfig)
    config = iconfig.load_config()
    # Check that the test file was loaded
    assert config["run_engine.default_metadata.facility"] == "Advanced Photon Source"


def test_nested_indexing():
    config = load_config(
        {
            "run_engine": {
                "default_metadata": {
                    "facility": "Advanced Light Source",
                },
            },
        }
    )
    print(config._model())
    assert config["run_engine.default_metadata"]["facility"] == "Advanced Light Source"


def test_iterate_keys():
    config = load_config({})
    iterated_keys = set([k for k in config])
    assert iterated_keys == {
        "run_engine",
        "area_detector_root_path",
        "bss",
        "tiled",
        "queueserver",
        "run_engine",
        "device_files",
        "feature_flags",
    }


class FeatureFlagConfig(ConfigModel):
    spam: bool = False


class BaseConfig(ConfigModel):
    feature_flags: FeatureFlagConfig = FeatureFlagConfig()


@pytest.fixture()
def config():
    config = Configuration(
        {
            "feature_flags": {
                "spam": True,
            },
        },
        model_class=BaseConfig,
        feature_flags={"spam": FeatureFlag(expires=next_month)},
    )
    return config


def test_feature_flag(config):
    assert config.feature_flag("spam") is True


def test_feature_flag_default():
    config = Configuration(
        {},
        model_class=BaseConfig,
        feature_flags={"spam": FeatureFlag(default=False, expires=next_month)},
    )
    assert config.feature_flag("spam") is False


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
        {"feature_flags": {"spam": True}},
        feature_flags={},
    )
    with pytest.raises(exceptions.UndeclaredFeatureFlag):
        config.feature_flag("spam")


def test_expired_feature_flag():
    now = time.time()
    config = Configuration(
        {},
        model_class=BaseConfig,
        feature_flags={"spam": FeatureFlag(default="eggs", expires=now - 3600)},
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
