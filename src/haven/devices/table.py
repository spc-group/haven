from ophyd_async.core import Device, StandardReadable

from .motor import Motor
from .transform import TransformRecord


class Table(StandardReadable, Device):
    """A dynamic Ophyd device for an optical table.

    This device will have the components needed for the configuration
    of motors provided. For example, if *horizontal_motor* is
    provided, then the device will have a ``horizontal`` attribute
    that is the corresponding horizontal motor.

    There are several dynamic parameters when creating an object that
    control the structure of the resulting device. These are described
    individually below and are assumed relative to *prefix*. If
    *upstream_motor* and *downstream_motor* are not empty, then
    *vertical* and *pitch* will point to a pseudo motor who's PV is
    determined by *pseudo_motors* (the value of *vertical_motor* will
    be ignored in this case). For example:

    .. code:: python

        tbl = Table(
            pseudo_motors="255idcVME:table_us:",
            transforms="255idcVME:table_us_trans:",
            upstream_motor="255idcVME:m3",
            downstream_motor="255idcVME:m4",
            name="my_table",
        )

    will produce a table with the following components:

    - *upstream*: "255idcVME:m3"
    - *downstream*: "255idcVME:m4"
    - *vertical*: "255idcVME:table_us:height"
    - *pitch*: "255idcVME:table_us:pitch"
    - *drive*: transform "255idcVME:table_us_trans:Drive"
    - *readback*: transform "255idcVME:table_us_trans:Readback"

    Parameters
    ==========
    vertical_motor
      The suffix for the real motor controlling the height of the
      table (e.g. "255idVME:m1"). Ignored if *upstream_motor* and
      *downstream_motor* are provided.
    horizontal_motor
      The suffix for the real motor controlling the lateral movement
      of the table (e.g. "255idVME:m2").
    upstream_motor
      The suffix for the real motor controlling the height of the
      upstream leg of the table (e.g. "255idVME:m3").
    downstream_motor
      The suffix for the real motor controlling the height of the
      downstream leg of the table (e.g. "255idVME:m4").
    pseudo_motors
      The prefix for the pseudo motors controlling the orientation of
      the table. E.g. "255id:table_ds:". Creates the components: *height*
      and *pitch*.
    transforms
      The prefix for the pseudo motor transform records
      (e.g. "255idVME:table_ds_trans:"). Creates the components:
      *vertical_drive_transform" and "vertical_readback_transform".

    """

    _ophyd_labels_ = {"tables"}
    # These are the possible components that could be present
    vertical: Device
    horizontal: Device
    upstream: Device
    downstream: Device
    pitch: Device
    horizontal_drive_transform: Device
    horizontal_readback_transform: Device

    def __init__(
        self,
        *,
        vertical_prefix: str = "",
        horizontal_prefix: str = "",
        upstream_prefix: str = "",
        downstream_prefix: str = "",
        pseudo_motor_prefix: str = "",
        transform_prefix: str = "",
        name="",
    ):
        has_pseudo_motors = bool(upstream_prefix) and bool(downstream_prefix)
        with self.add_children_as_readables():
            # See if we have direct control over the vertical/horizontal positions
            if vertical_prefix != "":
                self.vertical = Motor(vertical_prefix, name="vertical")
            if horizontal_prefix != "":
                self.horizontal = Motor(horizontal_prefix, name="horizontal")
            if bool(upstream_prefix):
                self.upstream = Motor(upstream_prefix, name="upstream")
            if bool(downstream_prefix):
                self.downstream = Motor(downstream_prefix, name="downstream")

            # Check if we need to add the pseudo motors and tranforms
            if has_pseudo_motors:
                self.vertical = Motor(f"{pseudo_motor_prefix}height", name="vertical")
                self.pitch = Motor(f"{pseudo_motor_prefix}pitch", name="pitch")
                self.vertical_drive_transform = TransformRecord(
                    f"{transform_prefix}Drive", name="vertical_drive_transform"
                )
                self.vertical_readback_transform = TransformRecord(
                    f"{transform_prefix}Readback", name="vertical_readback_transform"
                )
        super().__init__(name=name)


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
