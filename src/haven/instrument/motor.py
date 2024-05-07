import asyncio
import logging
import warnings
from typing import Mapping, Sequence

from aioca import CANothing, caget
from ophyd import Component as Cpt
from ophyd import EpicsMotor, EpicsSignal, EpicsSignalRO

from .._iconfig import load_config
from .device import make_device, resolve_device_names
from .instrument_registry import InstrumentRegistry
from .instrument_registry import registry as default_registry

log = logging.getLogger(__name__)


class HavenMotor(EpicsMotor):
    """The default motor for haven movement.

    Returns to the previous value when being unstaged.
    """

    description = Cpt(EpicsSignal, ".DESC", kind="omitted")
    tweak_value = Cpt(EpicsSignal, ".TWV", kind="omitted")
    tweak_forward = Cpt(EpicsSignal, ".TWF", kind="omitted", tolerance=2)
    tweak_reverse = Cpt(EpicsSignal, ".TWR", kind="omitted", tolerance=2)
    motor_stop = Cpt(EpicsSignal, ".STOP", kind="omitted", tolerance=2)
    soft_limit_violation = Cpt(EpicsSignalRO, ".LVIO", kind="omitted")

    def stage(self):
        super().stage()
        # Save starting position to restore later
        self._old_value = self.user_readback.value

    def unstage(self):
        super().unstage()
        # Restore the previously saved position after the scan ends
        self.set(self._old_value, wait=True)


def load_motors(
    config: Mapping = None, registry: InstrumentRegistry = default_registry
) -> Sequence:
    """Load generic hardware motors from IOCs.

    This loader will skip motor prefixes that already exist in the
    registry *registry*, so it is a good idea to run this loader after
    other devices have been created that might potentially use some of
    these motors (e.g. mirrors, tables, etc.).

    Parameters
    ==========
    config
      The beamline configuration. If omitted, will use the config
      provided by :py:func:`haven._iconfig.load_config()`.
    registry
      The instrument registry to check for existing motors. Existing
      motors will not be duplicated.

    Returns
    =======
    devices
      The newly create EpicsMotor devices.

    """
    if config is None:
        config = load_config()
    # Build up definitions of motors to load
    defns = []
    for section_name, config in config.get("motor", {}).items():
        prefix = config["prefix"]
        num_motors = config["num_motors"]
        log.info(
            f"Preparing {num_motors} motors from IOC: " "{section_name} ({prefix})"
        )
        for idx in range(num_motors):
            motor_prefix = f"{prefix}m{idx+1}"
            defns.append(
                {
                    "prefix": motor_prefix,
                    "desc_pv": f"{motor_prefix}.DESC",
                    "ioc_name": section_name,
                }
            )
    # Check that we're not duplicating a motor somewhere else (e.g. KB mirrors)
    existing_pvs = []
    for m in registry.findall(label="motors", allow_none=True):
        if hasattr(m, "prefix"):
            existing_pvs.append(m.prefix)
    defns = [defn for defn in defns if defn["prefix"] not in existing_pvs]
    duplicates = [defn for defn in defns if defn["prefix"] in existing_pvs]
    if len(duplicates) > 0:
        log.info(
            "The following motors already exist and will not be duplicated: ",
            ", ".join([m["prefix"] for m in duplicates]),
        )
    else:
        log.debug(f"No duplicated motors detected out of {len(defns)}")
    # Resolve the scaler channels into ion chamber names
    asyncio.run(resolve_device_names(defns))
    # Create the devices
    devices = []
    missing_channels = []
    unnamed_channels = []
    for defn in defns:
        # Check for motor without a name
        if defn["name"] == "":
            unnamed_channels.append(defn["prefix"])
        elif defn["name"] is None:
            missing_channels.append(defn["prefix"])
        else:
            # Create the device
            labels = {"motors", "extra_motors", "baseline", defn["ioc_name"]}
            devices.append(
                make_device(
                    HavenMotor, prefix=defn["prefix"], name=defn["name"], labels=labels
                )
            )
    # Notify about motors that have no name
    if len(missing_channels) > 0:
        msg = "Skipping unavailable motors: "
        msg += ", ".join([prefix for prefix in missing_channels])
        warnings.warn(msg)
        log.warning(msg)
    if len(unnamed_channels) > 0:
        msg = "Skipping unnamed motors: "
        msg += ", ".join([prefix for prefix in unnamed_channels])
        warnings.warn(msg)
        log.warning(msg)
    return devices


async def load_motor(prefix: str, motor_num: int, ioc_name: str = None):
    """Create the requested motor if it is reachable."""
    pv = f"{prefix}:m{motor_num+1}"
    # Get motor names
    config = load_config()
    # Get the motor name from the description PV
    try:
        name = await caget(f"{pv}.DESC")
    except (asyncio.exceptions.TimeoutError, CANothing):
        if not config["beamline"]["is_connected"]:
            # Beamline is not connected, so just use a generic name
            name = f"{prefix}_m{motor_num+1}"
        else:
            # Motor is unreachable, so skip it
            log.warning(f"Could not connect to motor: {pv}")
            return
    else:
        log.debug(f"Resolved motor {pv} to '{name}'")
    # Create the motor device
    unused_motor_names = [f"motor {motor_num+1}", ""]
    if name in unused_motor_names:
        # It's an unnamed motor, so skip it
        log.info(f"SKipping unnamed motor {pv}")
    else:
        # Create a new motor object
        labels = {"motors", "extra_motors", "baseline"}
        if ioc_name is not None:
            labels = set([ioc_name, *labels])
        return await make_device(HavenMotor, prefix=pv, name=name, labels=labels)


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
