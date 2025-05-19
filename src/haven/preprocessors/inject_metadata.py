from functools import partial
import getpass
import logging
import os
import socket
import warnings
from collections import ChainMap
import importlib
from typing import Mapping

import epics
from bluesky import plan_stubs as bps, Msg
from bluesky.preprocessors import plan_mutator
from bluesky.utils import make_decorator

from haven import __version__ as haven_version
from haven._iconfig import load_config
from haven.exceptions import ComponentNotFound
from haven.instrument import beamline

log = logging.getLogger()


def get_version(pkg_name):
    return importlib.metadata.version(pkg_name)


def version_md(config: Mapping | None):
    if config is None:
        config = load_config()
    # Prepare the metadata dictionary
    md = {
        # Software versions
        "version_apstools": get_version("apstools"),
        "version_bits": get_version("apsbits"),
        "version_bluesky": get_version("bluesky"),
        "version_epics_ca": epics.__version__,
        "version_epics": epics.__version__,
        "version_haven": haven_version,
        "version_ophyd": get_version("ophyd"),
        "version_ophyd_async": get_version("ophyd_async"),
        # Controls
        "EPICS_HOST_ARCH": os.environ.get("EPICS_HOST_ARCH"),
        "epics_libca": os.environ.get("PYEPICS_LIBCA"),
        "EPICS_CA_MAX_ARRAY_BYTES": os.environ.get("EPICS_CA_MAX_ARRAY_BYTES"),
        # Facility
        "beamline_id": config.get("beamline", {}).get("name"),
        "facility_id": config.get("synchrotron", {}).get("name"),
        "xray_source": config.get("xray_source", {}).get("type"),
        # Computer
        "login_id": f"{getpass.getuser()}@{socket.gethostname()}",
        "pid": os.getpid(),
    }
    return md


def _inject_md(msg, config: Mapping | None = None):
    if msg.command != "open_run":
        return (None, None)
    md = version_md(config=config)
    # Filter out `None` values since they were not found
    md = {key: val for key, val in md.items() if val not in [None, ""]}

    def md_gen():
        # Get metadata from the beamline scheduling system (bss)
        try:
            bss = beamline.devices["bss"]
        except ComponentNotFound:
            wmsg = "Could not find bss device, metadata may be missing."
            warnings.warn(wmsg)
            log.warning(wmsg)
        else:
            # bss_md = yield from bps.read(bss)
            bss_md = {}
            md_keys = [
                # (metadata key, device reading key)
                # ("proposal_id", "proposal-proposal_id"),
                # ("proposal_title", "proposal-title"),
                # ("prposal_users", "proposal-user_last_names"),
                # ("proposal_user_badges", "proposal-user_badges"),
            ]
            md.update(
                {
                    key: bss_md[f"{bss.name}-{data_key}"]['value']
                    for key, data_key in md_keys
                    # "proposal_id": bss_md[f'{bss.name}-proposal-proposal_id']['value'],
                    # "proposal_title": bss_md[f'{bss.name}-proposal-title']['value'],
                    # "proposal_users": bss_md[f'{bss.name}-proposal-user_last_names']['value'],
                    # "proposal_user_badges": bss_md[f'{bss.name}-proposal-user_badges']['value'],
                    # "esaf_id": bss_md[f'{bss.name}-esaf-esaf_id']['value'],
                    # "esaf_title": bss_md[f'{bss.name}-esaf-title']['value'],
                    # "esaf_users": bss_md[f'{bss.name}-esaf-user_last_names']['value'],
                    # "esaf_user_badges": bss_md[f'{bss.name}-esaf-user_badges']['value'],
                    # "esaf_aps_run": bss_md[f'{bss.name}-esaf.aps_run']['value'],
                    # "mail_in_flag": bss_md[f'{bss.name}-proposal-mail_in_flag']['value'],
                    # "proprietary_flag": bss_md[f'{bss.name}-proposal-proprietary_flag']['value'],
                    # "bss_beamline_name": bss_md[f'{bss.name}-proposal-beamline_name']['value'],
                }
            )
        # Update the message
        md.update(msg.kwargs)
        new_msg = msg._replace(kwargs={})
        print("===")
        print(id(msg), msg)
        print(id(new_msg), new_msg)
        print('---')
        new_msg = msg
        return (yield new_msg)
    return [md_gen(), None]



def inject_metadata_wrapper(plan, config: Mapping | None = None):
    """Inject additional metadata into a run.

    This takes precedences over the original metadata dict in the event of
    overlapping keys, but it does not mutate the original metadata dict.
    (It uses ChainMap.)

    Parameters
    ----------
    plan : iterable or iterator
        a generator, list, or similar containing `Msg` objects

    """
    return (yield from plan_mutator(plan, partial(_inject_md, config=config)))


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
