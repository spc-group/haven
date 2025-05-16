#!/usr/bin/env python

"""
ophyd support for apsbss

EXAMPLE::

    apsbss = EpicsBssDevice("ioc:bss:", name="apsbss")

.. autosummary::

    ~EpicsBssDevice
    ~EpicsEsafDevice
    ~EpicsEsafExperimenterDevice
    ~EpicsProposalDevice
    ~EpicsProposalExperimenterDevice

"""

import asyncio

from ophyd_async.core import DeviceVector
from ophyd_async.core import StandardReadable
from ophyd_async.epics.core import epics_signal_rw

__all__ = ["BeamlineSchedulingSystem"]


class EpicsEsafExperimenterDevice(StandardReadable):
    """Ophyd-async device for experimenter info from APS ESAF.

    .. autosummary::

        ~clear

    """

    def __init__(self, prefix: str, *, name: str = ""):
        with self.add_children_as_readables():
            self.badge_number = epics_signal_rw(str, f"{prefix}badgeNumber")
            self.email = epics_signal_rw(str, f"{prefix}email")
            self.first_name = epics_signal_rw(str, f"{prefix}firstName")
            self.last_name = epics_signal_rw(str, f"{prefix}lastName")
        super().__init__(name=name)

    async def clear(self):
        """Clear the fields for this user."""
        await asyncio.gather(
            self.badge_number.set(""),
            self.email.set(""),
            self.first_name.set(""),
            self.last_name.set(""),
        )


class EpicsEsafDevice(StandardReadable):
    """
    Ophyd device for info from APS ESAF.

    .. autosummary::

        ~clear
        ~clear_users
    """

    def __init__(self, prefix: str, *, name: str = "", num_users: int = 9):
        with self.add_children_as_readables():
            self.aps_run = epics_signal_rw(str, f"{prefix}run")
            self.description = epics_signal_rw(str, f"{prefix}description")
            self.end_date = epics_signal_rw(str, f"{prefix}endDate")
            self.end_date_timestamp = epics_signal_rw(int, f"{prefix}endDate:timestamp")
            self.esaf_id = epics_signal_rw(int, f"{prefix}id")
            self.esaf_status = epics_signal_rw(str, f"{prefix}status")
            self.number_users_in_pvs = epics_signal_rw(int, f"{prefix}users_in_pvs")
            self.number_users_total = epics_signal_rw(int, f"{prefix}users_total")
            self.sector = epics_signal_rw(str, f"{prefix}sector")
            self.start_date = epics_signal_rw(str, f"{prefix}startDate")
            self.start_date_timestamp = epics_signal_rw(int, f"{prefix}startDate:timestamp")
            self.title = epics_signal_rw(str, f"{prefix}title")
            self.user_last_names = epics_signal_rw(str, f"{prefix}users")
            self.user_badges = epics_signal_rw(str, f"{prefix}userBadges")
            self.users = DeviceVector(
                {idx: EpicsEsafExperimenterDevice(f"{prefix}user{idx+1}:") for idx in range(num_users)}
            )
        self.raw = epics_signal_rw(str, f"{prefix}raw")

        super().__init__(name=name)

    async def clear(self):
        """
        Clear the most of the ESAF info.

        Do not clear these items:

        * ``aps_run``
        * ``esaf_id``
        * ``sector``
        """
        await asyncio.gather(
            # self.aps_run.put(""),    # user controls this
            self.description.set(""),
            self.end_date.set(""),
            self.end_date_timestamp.set(0),
            # self.esaf_id.set(""),      # user controls this
            self.esaf_status.set(""),
            # self.sector.set(""),
            self.start_date.set(""),
            self.start_date_timestamp.set(0),
            self.title.set(""),
            self.user_last_names.set(""),
            self.user_badges.set(""),
            self.clear_users(),
        )

    async def clear_users(self):
        """Clear the info for all users."""
        user_devices = [user.clear() for user in self.users.values()]
        await asyncio.gather(*user_devices)


class EpicsProposalExperimenterDevice(StandardReadable):
    """
    Ophyd device for experimenter info from APS Proposal.

    .. autosummary::

        ~clear
    """

    def __init__(self, prefix: str, *, name: str = ""):
        with self.add_children_as_readables():
            self.badge_number = epics_signal_rw(str, f"{prefix}badgeNumber")
            self.email = epics_signal_rw(str, f"{prefix}email")
            self.first_name = epics_signal_rw(str, f"{prefix}firstName")
            self.institution = epics_signal_rw(str, f"{prefix}institution")
            self.institution_id = epics_signal_rw(int, f"{prefix}instId")
            self.last_name = epics_signal_rw(str, f"{prefix}lastName")
            self.pi_flag = epics_signal_rw(bool, f"{prefix}piFlag")
            self.user_id = epics_signal_rw(int, f"{prefix}userId")
        super().__init__(name=name)

    async def clear(self):
        """Clear the info for this user."""
        await asyncio.gather(
            self.badge_number.set(""),
            self.email.set(""),
            self.first_name.set(""),
            self.last_name.set(""),
            self.user_id.set(0),
            self.institution_id.set(0),
            self.institution.set(""),
            self.pi_flag.set(0),
        )


class EpicsProposalDevice(StandardReadable):
    """
    Ophyd device for info from APS Proposal.

    .. autosummary::

        ~clear
        ~clear_users
    """

    def __init__(self, prefix: str, *, name: str = "", num_users: int = 9):
        with self.add_children_as_readables():
            self.beamline_name = epics_signal_rw(str, f"{prefix}beamline")
            self.end_date = epics_signal_rw(str, f"{prefix}endDate")
            self.end_date_timestamp = epics_signal_rw(int, f"{prefix}endDate:timestamp")
            self.mail_in_flag = epics_signal_rw(str, f"{prefix}mailInFlag")
            self.number_users_in_pvs = epics_signal_rw(int, f"{prefix}users_in_pvs")
            self.number_users_total = epics_signal_rw(int, f"{prefix}users_total")
            self.proposal_id = epics_signal_rw(int, f"{prefix}id")
            self.proprietary_flag = epics_signal_rw(str, f"{prefix}proprietaryFlag")
            self.start_date = epics_signal_rw(str, f"{prefix}startDate")
            self.start_date_timestamp = epics_signal_rw(int, f"{prefix}startDate:timestamp")
            self.submitted_date = epics_signal_rw(str, f"{prefix}submittedDate")
            self.submitted_date_timestamp = epics_signal_rw(int, f"{prefix}submittedDate:timestamp")
            self.title = epics_signal_rw(str, f"{prefix}title")
            self.user_badges = epics_signal_rw(str, f"{prefix}userBadges")
            self.user_last_names = epics_signal_rw(str, f"{prefix}users")
            self.users = DeviceVector(
                {idx: EpicsProposalExperimenterDevice(f"{prefix}user{idx+1}:") for idx in range(num_users)}
            )
        self.raw = epics_signal_rw(str, f"{prefix}raw")
        super().__init__(name=name)

    async def clear(self):
        """
        Clear the most of the proposal info.

        Do not clear these items:

        * ``beamline_name``
        * ``proposal_id``
        """
        await asyncio.gather(
            # self.beamline_name.put(""),    # user controls this
            self.end_date.set(""),
            self.end_date_timestamp.set(0),
            self.mail_in_flag.set(0),
            # self.proposal_id.set(-1),      # user controls this
            self.proprietary_flag.set(0),
            self.start_date.set(""),
            self.start_date_timestamp.set(0),
            self.submitted_date.set(""),
            self.submitted_date_timestamp.set(0),
            self.title.set(""),
            self.user_last_names.set(""),
            self.user_badges.set(""),
            self.clear_users(),
        )

    async def clear_users(self):
        """Clear the info for all users."""
        aws = [user.clear() for user in self.users.values()]
        await asyncio.gather(*aws)


class BeamlineSchedulingSystem(StandardReadable):
    """
    Ophyd-async device for info from APS Proposal and ESAF databases.

    .. autosummary::

        ~_table
        ~addDeviceDataAsStream
        ~clear
    """

    def __init__(self, prefix: str, *, name: str = ""):
        with self.add_children_as_readables():
            self.esaf = EpicsEsafDevice(f"{prefix}esaf:")
            self.proposal = EpicsProposalDevice(f"{prefix}proposal:")

        self.ioc_host = epics_signal_rw(str, f"{prefix}ioc_host")
        self.ioc_user = epics_signal_rw(str, f"{prefix}ioc_user")
        self.status_msg = epics_signal_rw(str, f"{prefix}status")

        super().__init__(name=name)

    async def clear(self):
        """Clear the proposal and ESAF info."""
        await asyncio.gather(
            self.esaf.clear(),
            self.proposal.clear(),
        )
        await self.status_msg.set("Cleared")


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2025, UChicago Argonne, LLC
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
