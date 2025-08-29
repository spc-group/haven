import logging

import IPython
from apsbits.core.run_engine_init import init_RE
from bluesky import Msg
from bluesky import RunEngine as BlueskyRunEngine
from bluesky.bundlers import maybe_await
from bluesky.callbacks.best_effort import BestEffortCallback
from bluesky.utils import ProgressBarManager, register_transform

from haven import load_config
from haven.catalog import tiled_client
from haven.tiled_writer import TiledWriter

log = logging.getLogger(__name__)


async def _calibrate(msg: Msg):
    """
    Calibrate an objects requested value to its true value.

    Expected message object is:

        Msg('calibrate', obj, truth, target, relative)

    """
    # actually _calibrate_ the object
    await maybe_await(msg.obj.calibrate(*msg.args, **msg.kwargs))


def run_engine(
    *,
    connect_tiled: bool = False,
    use_bec: bool = False,
    **kwargs,
) -> BlueskyRunEngine:
    """Build a bluesky RunEngine() for Haven.

    Parameters
    ==========
    connect_tiled
      The run engine will have a callback for writing to the default
      tiled client.
    use_bec
      The run engine will have the bluesky BestEffortCallback
      subscribed to it.

    """
    config = load_config()
    # Add the best-effort callback if needed
    bec = BestEffortCallback() if use_bec else None
    # Create the run engine
    RE, *_ = init_RE(config, bec_instance=bec, **kwargs)
    # Add custom verbs
    RE.register_command("calibrate", _calibrate)
    # Install suspenders
    # try:
    #     aps = beamline.devices["APS"]
    # except ComponentNotFound:
    #     log.warning("APS device not found, suspenders not installed.")
    # else:
    #     # Suspend when shutter permit is disabled
    #     # Re-enable when the APS shutter permit signal is better understood
    #     pass
    #     # RE.install_suspender(
    #     #     suspenders.SuspendWhenChanged(
    #     #         signal=aps.shutter_permit,
    #     #         expected_value="PERMIT",
    #     #         allow_resume=True,
    #     #         sleep=3,
    #     #         tripped_message="Shutter permit revoked.",
    #     #     )
    #     # )
    # Add a shortcut for using the run engine more efficiently
    RE.waiting_hook = ProgressBarManager()
    if (ip := IPython.get_ipython()) is not None:
        register_transform("RE", prefix="<", ip=ip)
    # Install database connections
    if connect_tiled:
        tiled_config = config["tiled"]
        client = tiled_client(
            profile=tiled_config["writer_profile"],
            cache_filepath=None,
            structure_clients="numpy",
        )
        client.include_data_sources()
        tiled_writer = TiledWriter(
            client,
            backup_directory=tiled_config.get("writer_backup_directory"),
            batch_size=tiled_config.get("writer_batch_size", 100),
        )
        RE.subscribe(tiled_writer)
    return RE


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
