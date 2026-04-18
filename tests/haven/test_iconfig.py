import importlib
import time
from pathlib import Path
from textwrap import dedent

from haven import iconfig
from haven.iconfig import HavenConfig, load_config

next_month = time.time() + 30 * 24 * 3600


def test_default_values():
    """Do we set reasonable default values?"""
    config = load_config()
    assert config.area_detector_root_path == "/tmp"


def test_loading_a_file():
    test_file = Path(__file__).resolve().parent / "test_iconfig.toml"
    config = load_config(test_file)
    assert config.run_engine.default_metadata.facility == "Zero Gradient Synchrotron"


def test_resolve_device_file_paths(tmp_path):
    toml_file = tmp_path / "main.toml"
    with open(toml_file, mode="w") as fd:
        fd.write("device_files = ['./my_devices.toml', '/tmp/other_devices.toml']")
    cfg = load_config(toml_file)
    assert cfg.device_files == [
        str(tmp_path / "my_devices.toml"),
        "/tmp/other_devices.toml",
    ]


def test_device_parameters(tmp_path):
    devices0 = tmp_path / "devices-common.toml"
    with open(devices0, mode="w") as fp:
        fp.write(
            dedent(
                """
            [[ motors ]]
            m1 = "255idcVME:m1"

            [[ motors ]]
            m2 = "255idcVME:m2"
        """
            )
        )
    devices1 = tmp_path / "devices-specific.toml"
    with open(devices1, mode="w") as fp:
        fp.write(
            dedent(
                """
            [[ motors ]]
            m3 = "255idcVME:m2"
        """
            )
        )
    config = HavenConfig(device_files=[str(devices0), str(devices1)])
    # Check that the device parameters get loaded properly
    params = config.device_parameters()
    assert len(params["motors"]) == 3


def test_config_files_from_env(monkeypatch):
    # Set the environmental variable with the path to a test TOML file
    test_file = Path(__file__).resolve().parent / "test_iconfig.toml"
    monkeypatch.setenv("HAVEN_CONFIG", str(test_file))
    importlib.reload(iconfig)
    # Load the configuration
    importlib.reload(iconfig)
    config = iconfig.load_config()
    # Check that the test file was loaded
    assert config.run_engine.default_metadata.facility == "Zero Gradient Synchrotron"


# Logging config example taken from
# https://stackoverflow.com/a/7507842
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "default": {
            "level": "INFO",
            "formatter": "standard",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",  # Default is stderr
        },
    },
    "loggers": {
        "": {  # root logger
            "handlers": ["default"],
            "level": "WARNING",
            "propagate": False,
        },
        "my.packg": {"handlers": ["default"], "level": "INFO", "propagate": False},
        "__main__": {  # if __name__ == '__main__'
            "handlers": ["default"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}


def test_logging_config():
    # Check that the example logging dictconfig passes validation
    cfg = iconfig.load_config({"logging": LOGGING_CONFIG})
    assert cfg.logging.version == 1


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
