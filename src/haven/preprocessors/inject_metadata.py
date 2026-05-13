import getpass
import importlib
import logging
import os
import socket
from pathlib import Path
from typing import Any

import epics
from bluesky.preprocessors import msg_mutator
from bluesky.utils import make_decorator

from ..iconfig import load_config

log = logging.getLogger()


def get_version(pkg_name):
    return importlib.metadata.version(pkg_name)


def _get_hatch_version():
    """Compute the most up-to-date version number in a development environment.

    For more details, see <https://github.com/maresb/hatch-vcs-footgun-example/>.
    """
    from hatchling.metadata.core import ProjectMetadata
    from hatchling.plugin.manager import PluginManager
    from hatchling.utils.fs import locate_file

    pyproject_toml = locate_file(__file__, "pyproject.toml")
    if pyproject_toml is None:
        raise RuntimeError("pyproject.toml not found although hatchling is installed")
    root = Path(pyproject_toml).parent

    # Temporarily set cwd to project root for PEP 517 compliance.
    old_cwd = Path.cwd()
    os.chdir(root)
    try:
        metadata = ProjectMetadata(root=str(root), plugin_manager=PluginManager())
        # Version can be static in pyproject.toml or computed dynamically:
        return metadata.core.version or metadata.hatch.version.cached
    finally:
        os.chdir(old_cwd)


def version_md() -> dict[str, Any]:
    # Prepare the metadata dictionary
    md = {
        # Software versions
        "version_apstools": get_version("apstools"),
        "version_bits": get_version("apsbits"),
        "version_bluesky": get_version("bluesky"),
        "version_epics_ca": epics.__version__,
        "version_epics": epics.__version__,
        "version_haven": _get_hatch_version(),
        "version_ophyd": get_version("ophyd"),
        "version_ophyd_async": get_version("ophyd_async"),
        # Controls
        "EPICS_HOST_ARCH": os.environ.get("EPICS_HOST_ARCH"),
        "epics_libca": os.environ.get("PYEPICS_LIBCA"),
        "EPICS_CA_MAX_ARRAY_BYTES": os.environ.get("EPICS_CA_MAX_ARRAY_BYTES"),
        # Computer
        "login_id": f"{getpass.getuser()}@{socket.gethostname()}",
        "pid": os.getpid(),
    }
    return md


def _inject_md(msg):
    if msg.command != "open_run":
        # This is not a message with metadata, so let it pass as-is
        return msg
    md = version_md()
    # Add in metadata from configuration file dynamically
    config = load_config()
    md.update(config.run_engine.default_metadata.model_dump())
    if config.data_management is not None:
        md["dm_station_name"] = config.data_management.station_name
    # Filter out `None` values since they were not found
    md = {key: val for key, val in md.items() if val not in [None, ""]}
    # Update the message
    md.update(msg.kwargs)
    new_msg = msg._replace(kwargs=md)
    return new_msg


def inject_metadata_wrapper(plan):
    """Inject additional metadata into a run.

    This takes precedence over the original metadata dict in the event
    of overlapping keys, but it does not mutate the original metadata
    dict.

    Parameters
    ----------
    plan : iterable or iterator
        a generator, list, or similar containing `Msg` objects

    """
    return (yield from msg_mutator(plan, _inject_md))


inject_metadata_decorator = make_decorator(inject_metadata_wrapper)


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
