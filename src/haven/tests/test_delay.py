"""
test the SRS DG-645 digital delay device support

Hardware is not available so test with best efforts
"""

from haven.devices import delay


async def test_dg645_device():
    dg645 = delay.DG645Delay("", name="delay")
    await dg645.connect(mock=True)
    read_names = []
    read_attrs = (await dg645.describe()).keys()
    assert sorted(read_attrs) == read_names

    cfg_names = [
        "delay-burst_config",
        "delay-burst_count",
        "delay-burst_delay",
        "delay-burst_mode",
        "delay-burst_period",
        "delay-channel_A-reference",
        "delay-channel_A-delay",
        "delay-channel_B-reference",
        "delay-channel_B-delay",
        "delay-channel_C-reference",
        "delay-channel_C-delay",
        "delay-channel_D-reference",
        "delay-channel_D-delay",
        "delay-channel_E-reference",
        "delay-channel_E-delay",
        "delay-channel_F-reference",
        "delay-channel_F-delay",
        "delay-channel_G-reference",
        "delay-channel_G-delay",
        "delay-channel_H-reference",
        "delay-channel_H-delay",
        "delay-device_id",
        "delay-label",
        "delay-output_AB-amplitude",
        "delay-output_AB-offset",
        "delay-output_AB-polarity",
        "delay-output_AB-trigger_phase",
        "delay-output_AB-trigger_prescale",
        "delay-output_CD-amplitude",
        "delay-output_CD-offset",
        "delay-output_CD-polarity",
        "delay-output_CD-trigger_phase",
        "delay-output_CD-trigger_prescale",
        "delay-output_EF-amplitude",
        "delay-output_EF-offset",
        "delay-output_EF-polarity",
        "delay-output_EF-trigger_phase",
        "delay-output_EF-trigger_prescale",
        "delay-output_GH-amplitude",
        "delay-output_GH-offset",
        "delay-output_GH-polarity",
        "delay-output_GH-trigger_phase",
        "delay-output_GH-trigger_prescale",
        "delay-output_T0-amplitude",
        "delay-output_T0-offset",
        "delay-output_T0-polarity",
        "delay-trigger_advanced_mode",
        "delay-trigger_holdoff",
        "delay-trigger_inhibit",
        "delay-trigger_level",
        "delay-trigger_prescale",
        "delay-trigger_rate",
        "delay-trigger_source",
    ]
    cfg_attrs = (await dg645.describe_configuration()).keys()
    assert sorted(cfg_attrs) == sorted(cfg_names)

    # List all the components
    cpt_names = [
        "delay-autoip_state",
        "delay-bare_socket_state",
        "delay-burst_config",
        "delay-burst_count",
        "delay-burst_delay",
        "delay-burst_mode",
        "delay-burst_period",
        "delay-channel_A",
        "delay-channel_B",
        "delay-channel_C",
        "delay-channel_D",
        "delay-channel_E",
        "delay-channel_F",
        "delay-channel_G",
        "delay-channel_H",
        "delay-clear_error",
        "delay-device_id",
        "delay-dhcp_state",
        "delay-gateway",
        "delay-goto_local",
        "delay-goto_remote",
        "delay-gpib_address",
        "delay-gpib_state",
        "delay-ip_address",
        "delay-label",
        "delay-lan_state",
        "delay-mac_address",
        "delay-network_mask",
        "delay-output_AB",
        "delay-output_CD",
        "delay-output_EF",
        "delay-output_GH",
        "delay-output_T0",
        "delay-reset",
        "delay-reset_gpib",
        "delay-reset_lan",
        "delay-reset_serial",
        "delay-serial_baud",
        "delay-serial_state",
        "delay-static_ip_state",
        "delay-status",
        "delay-status_checking",
        "delay-telnet_state",
        "delay-trigger_advanced_mode",
        "delay-trigger_holdoff",
        "delay-trigger_inhibit",
        "delay-trigger_level",
        "delay-trigger_prescale",
        "delay-trigger_rate",
        "delay-trigger_source",
        "delay-vxi11_state",
    ]
    child_names = [child.name for attr, child in dg645.children()]
    assert sorted(child_names) == sorted(cpt_names)
