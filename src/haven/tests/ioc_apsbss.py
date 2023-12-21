#!/usr/bin/env python3
from caproto.server import (
    PVGroup,
    PvpropertyInteger,
    PvpropertyString,
    ioc_arg_parser,
    pvproperty,
    run,
)


class SimpleGroup(PVGroup):
    """
    An IOC that looks like an undulator.

    E.g. "25IDds:Energy"

    """

    esaf_cycle = pvproperty(value="2023-2", name="esaf:cycle")
    esaf_description = pvproperty(value="", name="esaf:description")
    esaf_enddate = pvproperty(value="", name="esaf:endDate")
    esaf_id = pvproperty(value="12345", name="esaf:id", dtype=PvpropertyString)
    esaf_status = pvproperty(value="", name="esaf:status")
    esaf_number_users_in_pvs = pvproperty(name="esaf:users_in_pvs", value="")
    esaf_number_users_total = pvproperty(name="esaf:users_total", value="")
    esaf_raw = pvproperty(name="esaf:raw", value="")
    esaf_sector = pvproperty(name="esaf:sector", value="")
    esaf_start_date = pvproperty(name="esaf:startDate", value="")
    esaf_title = pvproperty(name="esaf:title", value="Testing the wetness of water.")
    esaf_user_last_names = pvproperty(name="esaf:users", value="Bose, Einstein")
    esaf_user_badges = pvproperty(name="esaf:userBadges", value="287341, 339203, 59208")
    esaf_user1_badge_number = pvproperty(name="esaf:user1:badgeNumber", value="")
    esaf_user1_email = pvproperty(name="esaf:user1:email", value="")
    esaf_user1_first_name = pvproperty(name="esaf:user1:firstName", value="")
    esaf_user1_last_name = pvproperty(name="esaf:user1:lastName", value="")
    esaf_user2_badge_number = pvproperty(name="esaf:user2:badgeNumber", value="")
    esaf_user2_email = pvproperty(name="esaf:user2:email", value="")
    esaf_user2_first_name = pvproperty(name="esaf:user2:firstName", value="")
    esaf_user2_last_name = pvproperty(name="esaf:user2:lastName", value="")
    esaf_user3_badge_number = pvproperty(name="esaf:user3:badgeNumber", value="")
    esaf_user3_email = pvproperty(name="esaf:user3:email", value="")
    esaf_user3_first_name = pvproperty(name="esaf:user3:firstName", value="")
    esaf_user3_last_name = pvproperty(name="esaf:user3:lastName", value="")
    esaf_user4_badge_number = pvproperty(name="esaf:user4:badgeNumber", value="")
    esaf_user4_email = pvproperty(name="esaf:user4:email", value="")
    esaf_user4_first_name = pvproperty(name="esaf:user4:firstName", value="")
    esaf_user4_last_name = pvproperty(name="esaf:user4:lastName", value="")
    esaf_user5_badge_number = pvproperty(name="esaf:user5:badgeNumber", value="")
    esaf_user5_email = pvproperty(name="esaf:user5:email", value="")
    esaf_user5_first_name = pvproperty(name="esaf:user5:firstName", value="")
    esaf_user5_last_name = pvproperty(name="esaf:user5:lastName", value="")
    esaf_user6_badge_number = pvproperty(name="esaf:user6:badgeNumber", value="")
    esaf_user6_email = pvproperty(name="esaf:user6:email", value="")
    esaf_user6_first_name = pvproperty(name="esaf:user6:firstName", value="")
    esaf_user6_last_name = pvproperty(name="esaf:user6:lastName", value="")
    esaf_user7_badge_number = pvproperty(name="esaf:user7:badgeNumber", value="")
    esaf_user7_email = pvproperty(name="esaf:user7:email", value="")
    esaf_user7_first_name = pvproperty(name="esaf:user7:firstName", value="")
    esaf_user7_last_name = pvproperty(name="esaf:user7:lastName", value="")
    esaf_user8_badge_number = pvproperty(name="esaf:user8:badgeNumber", value="")
    esaf_user8_email = pvproperty(name="esaf:user8:email", value="")
    esaf_user8_first_name = pvproperty(name="esaf:user8:firstName", value="")
    esaf_user8_last_name = pvproperty(name="esaf:user8:lastName", value="")
    esaf_user9_badge_number = pvproperty(name="esaf:user9:badgeNumber", value="")
    esaf_user9_email = pvproperty(name="esaf:user9:email", value="")
    esaf_user9_first_name = pvproperty(name="esaf:user9:firstName", value="")
    esaf_user9_last_name = pvproperty(name="esaf:user9:lastName", value="")
    proposal_beamline_name = pvproperty(name="proposal:beamline", value="99ID-C")
    proposal_end_date = pvproperty(name="proposal:endDate", value="")
    proposal_mail_in_flag = pvproperty(
        name="proposal:mailInFlag", value=1, dtype=PvpropertyInteger
    )
    proposal_number_users_in_pvs = pvproperty(name="proposal:users_in_pvs", value="")
    proposal_number_users_total = pvproperty(name="proposal:users_total", value="")
    proposal_id = pvproperty(name="proposal:id", value="25873", dtype=PvpropertyString)
    proposal_proprietary_flag = pvproperty(
        name="proposal:proprietaryFlag", value=0, dtype=PvpropertyInteger
    )
    proposal_raw = pvproperty(name="proposal:raw", value="")
    proposal_start_date = pvproperty(name="proposal:startDate", value="")
    proposal_submitted_date = pvproperty(name="proposal:submittedDate", value="")
    proposal_title = pvproperty(
        name="proposal:title", value="Making the world a more interesting place."
    )
    proposal_user_badges = pvproperty(
        name="proposal:userBadges", value="287341, 203884, 59208"
    )
    proposal_user_last_names = pvproperty(
        name="proposal:users", value="Franklin, Watson, Crick"
    )
    proposal_user1_badge_number = pvproperty(
        name="proposal:user1:badgeNumber", value=""
    )
    proposal_user1_email = pvproperty(name="proposal:user1:email", value="")
    proposal_user1_first_name = pvproperty(name="proposal:user1:firstName", value="")
    proposal_user1_institution = pvproperty(name="proposal:user1:institution", value="")
    proposal_user1_institution_id = pvproperty(name="proposal:user1:instId", value="")
    proposal_user1_last_name = pvproperty(name="proposal:user1:lastName", value="")
    proposal_user1_pi_flag = pvproperty(name="proposal:user1:piFlag", value="")
    proposal_user1_user_id = pvproperty(name="proposal:user1:userId", value="")
    proposal_user2_badge_number = pvproperty(
        name="proposal:user2:badgeNumber", value=""
    )
    proposal_user2_email = pvproperty(name="proposal:user2:email", value="")
    proposal_user2_first_name = pvproperty(name="proposal:user2:firstName", value="")
    proposal_user2_institution = pvproperty(name="proposal:user2:institution", value="")
    proposal_user2_institution_id = pvproperty(name="proposal:user2:instId", value="")
    proposal_user2_last_name = pvproperty(name="proposal:user2:lastName", value="")
    proposal_user2_pi_flag = pvproperty(name="proposal:user2:piFlag", value="")
    proposal_user2_user_id = pvproperty(name="proposal:user2:userId", value="")
    proposal_user3_badge_number = pvproperty(
        name="proposal:user3:badgeNumber", value=""
    )
    proposal_user3_email = pvproperty(name="proposal:user3:email", value="")
    proposal_user3_first_name = pvproperty(name="proposal:user3:firstName", value="")
    proposal_user3_institution = pvproperty(name="proposal:user3:institution", value="")
    proposal_user3_institution_id = pvproperty(name="proposal:user3:instId", value="")
    proposal_user3_last_name = pvproperty(name="proposal:user3:lastName", value="")
    proposal_user3_pi_flag = pvproperty(name="proposal:user3:piFlag", value="")
    proposal_user3_user_id = pvproperty(name="proposal:user3:userId", value="")
    proposal_user4_badge_number = pvproperty(
        name="proposal:user4:badgeNumber", value=""
    )
    proposal_user4_email = pvproperty(name="proposal:user4:email", value="")
    proposal_user4_first_name = pvproperty(name="proposal:user4:firstName", value="")
    proposal_user4_institution = pvproperty(name="proposal:user4:institution", value="")
    proposal_user4_institution_id = pvproperty(name="proposal:user4:instId", value="")
    proposal_user4_last_name = pvproperty(name="proposal:user4:lastName", value="")
    proposal_user4_pi_flag = pvproperty(name="proposal:user4:piFlag", value="")
    proposal_user4_user_id = pvproperty(name="proposal:user4:userId", value="")
    proposal_user5_badge_number = pvproperty(
        name="proposal:user5:badgeNumber", value=""
    )
    proposal_user5_email = pvproperty(name="proposal:user5:email", value="")
    proposal_user5_first_name = pvproperty(name="proposal:user5:firstName", value="")
    proposal_user5_institution = pvproperty(name="proposal:user5:institution", value="")
    proposal_user5_institution_id = pvproperty(name="proposal:user5:instId", value="")
    proposal_user5_last_name = pvproperty(name="proposal:user5:lastName", value="")
    proposal_user5_pi_flag = pvproperty(name="proposal:user5:piFlag", value="")
    proposal_user5_user_id = pvproperty(name="proposal:user5:userId", value="")
    proposal_user6_badge_number = pvproperty(
        name="proposal:user6:badgeNumber", value=""
    )
    proposal_user6_email = pvproperty(name="proposal:user6:email", value="")
    proposal_user6_first_name = pvproperty(name="proposal:user6:firstName", value="")
    proposal_user6_institution = pvproperty(name="proposal:user6:institution", value="")
    proposal_user6_institution_id = pvproperty(name="proposal:user6:instId", value="")
    proposal_user6_last_name = pvproperty(name="proposal:user6:lastName", value="")
    proposal_user6_pi_flag = pvproperty(name="proposal:user6:piFlag", value="")
    proposal_user6_user_id = pvproperty(name="proposal:user6:userId", value="")
    proposal_user7_badge_number = pvproperty(
        name="proposal:user7:badgeNumber", value=""
    )
    proposal_user7_email = pvproperty(name="proposal:user7:email", value="")
    proposal_user7_first_name = pvproperty(name="proposal:user7:firstName", value="")
    proposal_user7_institution = pvproperty(name="proposal:user7:institution", value="")
    proposal_user7_institution_id = pvproperty(name="proposal:user7:instId", value="")
    proposal_user7_last_name = pvproperty(name="proposal:user7:lastName", value="")
    proposal_user7_pi_flag = pvproperty(name="proposal:user7:piFlag", value="")
    proposal_user7_user_id = pvproperty(name="proposal:user7:userId", value="")
    proposal_user8_badge_number = pvproperty(
        name="proposal:user8:badgeNumber", value=""
    )
    proposal_user8_email = pvproperty(name="proposal:user8:email", value="")
    proposal_user8_first_name = pvproperty(name="proposal:user8:firstName", value="")
    proposal_user8_institution = pvproperty(name="proposal:user8:institution", value="")
    proposal_user8_institution_id = pvproperty(name="proposal:user8:instId", value="")
    proposal_user8_last_name = pvproperty(name="proposal:user8:lastName", value="")
    proposal_user8_pi_flag = pvproperty(name="proposal:user8:piFlag", value="")
    proposal_user8_user_id = pvproperty(name="proposal:user8:userId", value="")
    proposal_user9_badge_number = pvproperty(
        name="proposal:user9:badgeNumber", value=""
    )
    proposal_user9_email = pvproperty(name="proposal:user9:email", value="")
    proposal_user9_first_name = pvproperty(name="proposal:user9:firstName", value="")
    proposal_user9_institution = pvproperty(name="proposal:user9:institution", value="")
    proposal_user9_institution_id = pvproperty(name="proposal:user9:instId", value="")
    proposal_user9_last_name = pvproperty(name="proposal:user9:lastName", value="")
    proposal_user9_pi_flag = pvproperty(name="proposal:user9:piFlag", value="")
    proposal_user9_user_id = pvproperty(name="proposal:user9:userId", value="")
    ioc_host = pvproperty(name="ioc_host", value="")
    ioc_user = pvproperty(name="ioc_user", value="")
    status_msg = pvproperty(name="status", value="")

    default_prefix = "99id:bss:"


if __name__ == "__main__":
    ioc_options, run_options = ioc_arg_parser(
        default_prefix="255idc:bss:", desc="haven.tests.ioc_apsbss test IOC"
    )
    ioc = SimpleGroup(**ioc_options)
    run(ioc.pvdb, **run_options)


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
