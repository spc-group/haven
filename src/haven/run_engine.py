import logging
from collections.abc import Mapping
from uuid import uuid4 as uuid

import databroker
import IPython
from bluesky import Msg
from bluesky import RunEngine as BlueskyRunEngine
from bluesky.bundlers import maybe_await
from bluesky.callbacks.best_effort import BestEffortCallback
from bluesky.utils import ProgressBarManager, register_transform
from bluesky_kafka import Publisher

from haven import load_config
from haven.tiled_writer import TiledWriter

from .catalog import tiled_client
from .exceptions import ComponentNotFound
from .instrument import beamline

log = logging.getLogger(__name__)


catalog = None


async def _calibrate(msg: Msg):
    """
    Calibrate an objects requested value to its true value.

    Expected message object is:

        Msg('calibrate', obj, truth, target, relative)

    """
    # actually _calibrate_ the object
    await maybe_await(msg.obj.calibrate(*msg.args, **msg.kwargs))


def save_to_databroker(name: str, doc: Mapping):
    # This is a hack around a problem with garbage collection
    # Has been fixed in main, maybe released in databroker v2?
    # Create the databroker callback if necessary
    global catalog
    if catalog is None:
        catalog = databroker.catalog["bluesky"]
    # Save the document
    catalog.v1.insert(name, doc)


def kafka_publisher():
    config = load_config()
    publisher = Publisher(
        topic=config["kafka"]["topic"],
        bootstrap_servers=",".join(config["kafka"]["servers"]),
        producer_config={"enable.idempotence": True},
        flush_on_stop_doc=True,
        key=str(uuid()),
    )
    return publisher


def run_engine(
    *,
    connect_tiled: bool = False,
    connect_databroker: bool = False,
    connect_kafka: bool = False,
    use_bec: bool = False,
    **kwargs,
) -> BlueskyRunEngine:
    """Build a bluesky RunEngine() for Haven.

    Parameters
    ==========
    connect_tiled
      The run engine will have a callback for writing to the default
      tiled client.
    connect_databroker
      The run engine will have a callback for writing to the default
      databroker catalog.
    use_bec
      The run engine will have the bluesky BestEffortCallback
      subscribed to it.

    """
    RE = BlueskyRunEngine(**kwargs)
    RE.register_command("calibrate", _calibrate)
    # Add the best-effort callback
    if use_bec:
        RE.subscribe(BestEffortCallback())
    # Install suspenders
    try:
        aps = beamline.devices["APS"]
    except ComponentNotFound:
        log.warning("APS device not found, suspenders not installed.")
    else:
        # Suspend when shutter permit is disabled
        # Re-enable when the APS shutter permit signal is better understood
        pass
        # RE.install_suspender(
        #     suspenders.SuspendWhenChanged(
        #         signal=aps.shutter_permit,
        #         expected_value="PERMIT",
        #         allow_resume=True,
        #         sleep=3,
        #         tripped_message="Shutter permit revoked.",
        #     )
        # )
    # Add a shortcut for using the run engine more efficiently
    RE.waiting_hook = ProgressBarManager()
    if (ip := IPython.get_ipython()) is not None:
        register_transform("RE", prefix="<", ip=ip)
    # Install databroker connection
    if connect_databroker:
        RE.subscribe(save_to_databroker)
    if connect_tiled:
        tiled_config = load_config()["tiled"]
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
    if connect_kafka:
        RE.subscribe(kafka_publisher())
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
