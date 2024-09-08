import logging
from typing import Mapping

from ophyd_async.core import Device

from .._iconfig import load_config
from .device import connect_devices
from .instrument_registry import InstrumentRegistry
from .instrument_registry import registry as default_registry
from .motor import Motor

__all__ = ["XYStage", "load_stages"]


log = logging.getLogger(__name__)


class XYStage(Device):
    """An XY stage with two motors operating in orthogonal directions.

    Vertical and horizontal are somewhat arbitrary, but are expected
    to align with the orientation of a camera monitoring the stage.

    Parameters
    ==========

    vertical_prefix
      The prefix for the PV of the vertical motor.
    horizontal_prefix
      The prefix to the PV of the horizontal motor.
    """

    _ophyd_labels_ = {"stages"}

    def __init__(
        self,
        vertical_prefix: str,
        horizontal_prefix: str,
        name: str = "",
    ):
        self.vert = Motor(vertical_prefix)
        self.horiz = Motor(horizontal_prefix)
        super().__init__(name=name)


async def load_stages(
    config: Mapping = None,
    registry: InstrumentRegistry = default_registry,
    connect: bool = True,
):
    """Load the stages defined in the configuration files' ``[stage]``
    sections.

    """
    if config is None:
        config = load_config()
    devices = []
    for name, stage_data in config.get("stage", {}).items():
        prefix = stage_data["prefix"]
        devices.append(
            XYStage(
                name=name,
                vertical_prefix=f"{prefix}{stage_data['pv_vert']}",
                horizontal_prefix=f"{prefix}{stage_data['pv_horiz']}",
            )
        )
    if connect:
        devices = await connect_devices(
            devices, mock=not config["beamline"]["is_connected"], registry=registry
        )
    return devices


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
