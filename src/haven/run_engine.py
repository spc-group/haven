import logging

import IPython
from apsbits.core.run_engine_init import init_RE
from bluesky import Msg
from bluesky import RunEngine as BlueskyRunEngine
from bluesky.bundlers import maybe_await
from bluesky.callbacks.tiled_writer import TiledWriter
from bluesky.utils import ProgressBarManager, register_transform

from haven import load_config

log = logging.getLogger(__name__)


__all__ = ["run_engine"]


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
    tiled_writer: TiledWriter | None = None,
    **kwargs,
) -> BlueskyRunEngine:
    """Build a bluesky RunEngine() for Haven.

    Parameters
    ==========
    connect_tiled
      The run engine will have a callback for writing to the default
      tiled client.

    """
    config = load_config()
    # Create the run engine
    RE, *_ = init_RE(config, **kwargs)
    # Add custom verbs
    RE.register_command("calibrate", _calibrate)
    # Add a shortcut for using the run engine more efficiently
    RE.waiting_hook = ProgressBarManager()
    if (ip := IPython.get_ipython()) is not None:
        register_transform("RE", prefix="<", ip=ip)
    # Install database connections
    if tiled_writer is not None:
        RE.subscribe(tiled_writer)
    else:
        log.info("Tiled Writer not installed in run engine.")
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
