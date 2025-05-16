"""Test module apsbss_ophyd."""

import datetime

import pytest

from haven.devices import BeamlineSchedulingSystem

@pytest.fixture()
async def bss():
    bss = BeamlineSchedulingSystem(prefix="255idz:bss:", name="bss")
    await bss.connect(mock=True)
    return bss


async def test_signals(bss):
    child_names = [name for name, child in bss.children()]
    for cpt in "esaf proposal ioc_host ioc_user status_msg".split():
        assert cpt in child_names

    await bss.status_msg.set("")
    assert (await bss.status_msg.get_value()) == ""

    await bss.status_msg.set("this is a test")
    assert (await bss.status_msg.get_value()) == "this is a test"

    await bss.clear()
    assert (await bss.status_msg.get_value()) == "Cleared"


async def test_reading(bss):
    reading = await bss.read()
    expected_keys = {
        "bss-esaf-aps_run",
        "bss-esaf-description",
        "bss-esaf-end_date",
        "bss-esaf-end_date_timestamp",
        "bss-esaf-esaf_id",
        "bss-esaf-esaf_status",
        "bss-esaf-number_users_in_pvs",
        "bss-esaf-number_users_total",
        "bss-esaf-sector",
        "bss-esaf-start_date",
        "bss-esaf-start_date_timestamp",
        "bss-esaf-title",
        "bss-esaf-user_badges",
        "bss-esaf-user_last_names",
        *[key for idx in range(9) for key in [
            f"bss-esaf-users-{idx}-badge_number",
            f"bss-esaf-users-{idx}-email",
            f"bss-esaf-users-{idx}-first_name",
            f"bss-esaf-users-{idx}-last_name",
        ]],
        "bss-proposal-beamline_name",
        "bss-proposal-end_date",
        "bss-proposal-end_date_timestamp",
        "bss-proposal-mail_in_flag",
        "bss-proposal-number_users_in_pvs",
        "bss-proposal-number_users_total",
        "bss-proposal-proposal_id",
        "bss-proposal-proprietary_flag",
        "bss-proposal-start_date",
        "bss-proposal-start_date_timestamp",
        "bss-proposal-submitted_date",
        "bss-proposal-submitted_date_timestamp",
        "bss-proposal-title",
        "bss-proposal-user_badges",
        "bss-proposal-user_last_names",
        *[key for idx in range(9) for key in [
            f"bss-proposal-users-{idx}-badge_number",
            f"bss-proposal-users-{idx}-email",
            f"bss-proposal-users-{idx}-first_name",
            f"bss-proposal-users-{idx}-last_name",
            f"bss-proposal-users-{idx}-institution_id",
            f"bss-proposal-users-{idx}-institution",
            f"bss-proposal-users-{idx}-pi_flag",
            f"bss-proposal-users-{idx}-user_id",
            
        ]],

    }
    assert set(reading.keys()) == expected_keys
