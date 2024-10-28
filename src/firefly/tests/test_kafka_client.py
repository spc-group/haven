from unittest import mock

import pytest

from firefly.kafka_client import KafkaClient


@pytest.fixture()
def client():
    consumer = mock.AsyncMock()
    return KafkaClient(kafka_consumer=consumer)


async def test_start(client):
    await client.consumer_loop()


async def test_start_twice(client):
    client.start()
    with pytest.raises(Exception):
        client.start()


def check_uid(uid):
    return uid == "40b434c5-bec2-4eff-9cbe-c470b6435677"


def test_start_message(client, qtbot):
    with qtbot.waitSignal(client.run_started, check_params_cb=check_uid):
        client._process_document("start", start_doc)


def test_event_message(client, qtbot):
    with qtbot.waitSignal(client.run_updated, check_params_cb=check_uid):
        client._process_document("descriptor", descriptor_doc)
        client._process_document("event", event_doc)


def test_stop_message(client, qtbot):
    client._process_document("descriptor", descriptor_doc)
    assert len(client._descriptors) == 1
    with qtbot.waitSignal(client.run_stopped, check_params_cb=check_uid):

        client._process_document("stop", stop_doc)
    assert len(client._descriptors) == 0


start_doc = {
    "EPICS_CA_MAX_ARRAY_BYTES": "16777216",
    "EPICS_HOST_ARCH": "linux-x86_64",
    "beamline_id": "25-ID-C",
    "detectors": ["I0"],
    "epics_libca": "/home/beams0/S25STAFF/miniforge3/envs/haven-dev/epics/lib/linux-x86_64/libca.so",
    "facility_id": "Advanced Photon Source",
    "hints": {"dimensions": [[["time"], "primary"]]},
    "login_id": "s25staff@fedorov.xray.aps.anl.gov",
    "num_intervals": 0,
    "num_points": 1,
    "parameters": "",
    "pid": 1080697,
    "plan_args": {
        "delay": None,
        "detectors": [
            "IonChamber(prefix='25idcVME:3820:', name='I0', "
            "read_attrs=['voltmeter', 'voltmeter.enable', "
            "'voltmeter.amps', 'voltmeter.volts', 'volts', "
            "'counts', 'net_counts', 'exposure_time'], "
            "configuration_attrs=['description', "
            "'voltmeter', 'voltmeter.description', "
            "'voltmeter.scanning_rate', "
            "'voltmeter.disable_value', "
            "'voltmeter.scan_disable_input_link_value', "
            "'voltmeter.scan_disable_value_input_link', "
            "'voltmeter.forward_link', "
            "'voltmeter.device_type', "
            "'voltmeter.alarm_status', "
            "'voltmeter.alarm_severity', "
            "'voltmeter.new_alarm_status', "
            "'voltmeter.new_alarm_severity', "
            "'voltmeter.disable_alarm_severity', "
            "'voltmeter.input_link', 'voltmeter.raw_value', "
            "'voltmeter.differential', 'voltmeter.high', "
            "'voltmeter.low', 'voltmeter.temperature_units', "
            "'voltmeter.resolution', 'voltmeter.range', "
            "'voltmeter.mode', 'gate', 'preset_count', "
            "'frequency', 'offset', 'record_dark_time', "
            "'channel_advance_source', "
            "'num_channels_to_use', 'max_channels', "
            "'channel_one_source', 'count_on_start'])"
        ],
        "num": 1,
    },
    "plan_name": "count",
    "plan_type": "generator",
    "purpose": "",
    "sample_name": "",
    "scan_id": 2,
    "time": 1717042074.4366016,
    "uid": "40b434c5-bec2-4eff-9cbe-c470b6435677",
    "versions": {
        "apstools": "1.6.19.dev52+ga165d24",
        "bluesky": "1.13.0a3",
        "databroker": "1.2.5",
        "epics": "3.5.2",
        "epics_ca": "3.5.2",
        "h5py": "3.9.0",
        "haven": "23.10.0",
        "matplotlib": "3.8.4",
        "numpy": "1.26.4",
        "ophyd": "1.9.0",
        "pymongo": "4.7.2",
    },
    "xray_source": "insertion device",
}
descriptor_doc = {
    "configuration": {
        "I0": {
            "data": {
                "I0_channel_advance_source": 1,
                "I0_channel_one_source": 1,
                "I0_count_on_start": 1,
                "I0_description": "I0",
                "I0_frequency": 10000000.0,
                "I0_gate": 0,
                "I0_max_channels": 8000,
                "I0_num_channels_to_use": 8000,
                "I0_offset": 0.0,
                "I0_preset_count": 0.0,
                "I0_record_dark_time": 0.0,
                "I0_voltmeter_alarm_severity": 0,
                "I0_voltmeter_alarm_status": 0,
                "I0_voltmeter_description": "I0",
                "I0_voltmeter_device_type": 8,
                "I0_voltmeter_differential": 0,
                "I0_voltmeter_disable_alarm_severity": 0,
                "I0_voltmeter_disable_value": 1,
                "I0_voltmeter_forward_link": "",
                "I0_voltmeter_high": 0.0,
                "I0_voltmeter_input_link": "@asyn(LJT7V_0 " "2)ANALOG_IN_VALUE",
                "I0_voltmeter_low": 0.0,
                "I0_voltmeter_mode": 0,
                "I0_voltmeter_new_alarm_severity": 0,
                "I0_voltmeter_new_alarm_status": 0,
                "I0_voltmeter_range": 0,
                "I0_voltmeter_raw_value": 0,
                "I0_voltmeter_resolution": 0,
                "I0_voltmeter_scan_disable_input_link_value": 0,
                "I0_voltmeter_scan_disable_value_input_link": "",
                "I0_voltmeter_scanning_rate": 9,
                "I0_voltmeter_temperature_units": 0,
            },
            "data_keys": {
                "I0_channel_advance_source": {
                    "dtype": "integer",
                    "enum_strs": ["Internal", "External"],
                    "lower_ctrl_limit": None,
                    "shape": [],
                    "source": "PV:25idcVME:3820:ChannelAdvance",
                    "units": None,
                    "upper_ctrl_limit": None,
                },
                "I0_channel_one_source": {
                    "dtype": "integer",
                    "enum_strs": ["Int. " "clock", "External"],
                    "lower_ctrl_limit": None,
                    "shape": [],
                    "source": "PV:25idcVME:3820:Channel1Source",
                    "units": None,
                    "upper_ctrl_limit": None,
                },
                "I0_count_on_start": {
                    "dtype": "integer",
                    "enum_strs": ["No", "Yes"],
                    "lower_ctrl_limit": None,
                    "shape": [],
                    "source": "PV:25idcVME:3820:CountOnStart",
                    "units": None,
                    "upper_ctrl_limit": None,
                },
                "I0_description": {
                    "dtype": "string",
                    "lower_ctrl_limit": None,
                    "shape": [],
                    "source": "PV:25idcVME:3820:scaler1.NM4",
                    "units": None,
                    "upper_ctrl_limit": None,
                },
                "I0_frequency": {
                    "dtype": "number",
                    "lower_ctrl_limit": 0.0,
                    "precision": 3,
                    "shape": [],
                    "source": "PV:25idcVME:3820:scaler1.FREQ",
                    "units": "",
                    "upper_ctrl_limit": 0.0,
                },
                "I0_gate": {
                    "dtype": "integer",
                    "enum_strs": ["N", "Y"],
                    "lower_ctrl_limit": None,
                    "shape": [],
                    "source": "PV:25idcVME:3820:scaler1.G4",
                    "units": None,
                    "upper_ctrl_limit": None,
                },
                "I0_max_channels": {
                    "dtype": "integer",
                    "lower_ctrl_limit": 0,
                    "shape": [],
                    "source": "PV:25idcVME:3820:MaxChannels",
                    "units": "",
                    "upper_ctrl_limit": 0,
                },
                "I0_num_channels_to_use": {
                    "dtype": "integer",
                    "lower_ctrl_limit": 0,
                    "shape": [],
                    "source": "PV:25idcVME:3820:NuseAll",
                    "units": "",
                    "upper_ctrl_limit": 0,
                },
                "I0_offset": {
                    "dtype": "number",
                    "lower_ctrl_limit": 0.0,
                    "precision": 0,
                    "shape": [],
                    "source": "PV:25idcVME:3820:scaler1_offset0.D",
                    "units": "",
                    "upper_ctrl_limit": 0.0,
                },
                "I0_preset_count": {
                    "dtype": "number",
                    "lower_ctrl_limit": 0.0,
                    "precision": 0,
                    "shape": [],
                    "source": "PV:25idcVME:3820:scaler1.PR4",
                    "units": "",
                    "upper_ctrl_limit": 0.0,
                },
                "I0_record_dark_time": {
                    "dtype": "number",
                    "lower_ctrl_limit": 0.0,
                    "precision": 0,
                    "shape": [],
                    "source": "PV:25idcVME:3820:scaler1_offset_time.VAL",
                    "units": "",
                    "upper_ctrl_limit": 0.0,
                },
                "I0_voltmeter_alarm_severity": {
                    "dtype": "integer",
                    "enum_strs": [
                        "NO_ALARM",
                        "MINOR",
                        "MAJOR",
                        "INVALID",
                    ],
                    "lower_ctrl_limit": None,
                    "shape": [],
                    "source": "PV:25idc:LJT7Voltmeter_0:Ai2.SEVR",
                    "units": None,
                    "upper_ctrl_limit": None,
                },
                "I0_voltmeter_alarm_status": {
                    "dtype": "integer",
                    "enum_strs": [
                        "NO_ALARM",
                        "READ",
                        "WRITE",
                        "HIHI",
                        "HIGH",
                        "LOLO",
                        "LOW",
                        "STATE",
                        "COS",
                        "COMM",
                        "TIMEOUT",
                        "HWLIMIT",
                        "CALC",
                        "SCAN",
                        "LINK",
                        "SOFT",
                    ],
                    "lower_ctrl_limit": None,
                    "shape": [],
                    "source": "PV:25idc:LJT7Voltmeter_0:Ai2.STAT",
                    "units": None,
                    "upper_ctrl_limit": None,
                },
                "I0_voltmeter_description": {
                    "dtype": "string",
                    "lower_ctrl_limit": None,
                    "shape": [],
                    "source": "PV:25idc:LJT7Voltmeter_0:Ai2.DESC",
                    "units": None,
                    "upper_ctrl_limit": None,
                },
                "I0_voltmeter_device_type": {
                    "dtype": "integer",
                    "enum_strs": [
                        "Soft " "Channel",
                        "Raw " "Soft " "Channel",
                        "Async " "Soft " "Channel",
                        "Soft " "Timestamp",
                        "General " "Time",
                        "asynInt32",
                        "asynInt32Average",
                        "asynFloat64",
                        "asynFloat64Average",
                        "asynInt64",
                        "IOC " "stats",
                        "IOC " "stats " "clusts",
                        "GPIB " "init/report",
                        "Sec " "Past " "Epoch",
                        "asyn " "ai " "stringParm",
                        "asyn " "ai " "HeidND261",
                    ],
                    "lower_ctrl_limit": None,
                    "shape": [],
                    "source": "PV:25idc:LJT7Voltmeter_0:Ai2.DTYP",
                    "units": None,
                    "upper_ctrl_limit": None,
                },
                "I0_voltmeter_differential": {
                    "dtype": "integer",
                    "enum_strs": ["Single-Ended", "Differential"],
                    "lower_ctrl_limit": None,
                    "shape": [],
                    "source": "PV:25idc:LJT7Voltmeter_0:AiDiff2",
                    "units": None,
                    "upper_ctrl_limit": None,
                },
                "I0_voltmeter_disable_alarm_severity": {
                    "dtype": "integer",
                    "enum_strs": [
                        "NO_ALARM",
                        "MINOR",
                        "MAJOR",
                        "INVALID",
                    ],
                    "lower_ctrl_limit": None,
                    "shape": [],
                    "source": "PV:25idc:LJT7Voltmeter_0:Ai2.DISS",
                    "units": None,
                    "upper_ctrl_limit": None,
                },
                "I0_voltmeter_disable_value": {
                    "dtype": "integer",
                    "lower_ctrl_limit": -32768,
                    "shape": [],
                    "source": "PV:25idc:LJT7Voltmeter_0:Ai2.DISV",
                    "units": "",
                    "upper_ctrl_limit": 32767,
                },
                "I0_voltmeter_forward_link": {
                    "dtype": "string",
                    "lower_ctrl_limit": None,
                    "shape": [],
                    "source": "PV:25idc:LJT7Voltmeter_0:Ai2.FLNK",
                    "units": None,
                    "upper_ctrl_limit": None,
                },
                "I0_voltmeter_high": {
                    "dtype": "number",
                    "lower_ctrl_limit": 0.0,
                    "precision": 4,
                    "shape": [],
                    "source": "PV:25idc:LJT7Voltmeter_0:AiHOPR2",
                    "units": "",
                    "upper_ctrl_limit": 0.0,
                },
                "I0_voltmeter_input_link": {
                    "dtype": "string",
                    "lower_ctrl_limit": None,
                    "shape": [],
                    "source": "PV:25idc:LJT7Voltmeter_0:Ai2.INP",
                    "units": None,
                    "upper_ctrl_limit": None,
                },
                "I0_voltmeter_low": {
                    "dtype": "number",
                    "lower_ctrl_limit": 0.0,
                    "precision": 4,
                    "shape": [],
                    "source": "PV:25idc:LJT7Voltmeter_0:AiLOPR2",
                    "units": "",
                    "upper_ctrl_limit": 0.0,
                },
                "I0_voltmeter_mode": {
                    "dtype": "integer",
                    "enum_strs": [
                        "Volts",
                        "Type " "B " "TC",
                        "Type " "C " "TC",
                        "Type " "E " "TC",
                        "Type " "J " "TC",
                        "Type " "K " "TC",
                        "Type " "N " "TC",
                        "Type " "R " "TC",
                        "Type " "S " "TC",
                        "Type " "T " "TC",
                    ],
                    "lower_ctrl_limit": None,
                    "shape": [],
                    "source": "PV:25idc:LJT7Voltmeter_0:AiMode2",
                    "units": None,
                    "upper_ctrl_limit": None,
                },
                "I0_voltmeter_new_alarm_severity": {
                    "dtype": "integer",
                    "enum_strs": [
                        "NO_ALARM",
                        "MINOR",
                        "MAJOR",
                        "INVALID",
                    ],
                    "lower_ctrl_limit": None,
                    "shape": [],
                    "source": "PV:25idc:LJT7Voltmeter_0:Ai2.NSEV",
                    "units": None,
                    "upper_ctrl_limit": None,
                },
                "I0_voltmeter_new_alarm_status": {
                    "dtype": "integer",
                    "enum_strs": [
                        "NO_ALARM",
                        "READ",
                        "WRITE",
                        "HIHI",
                        "HIGH",
                        "LOLO",
                        "LOW",
                        "STATE",
                        "COS",
                        "COMM",
                        "TIMEOUT",
                        "HWLIMIT",
                        "CALC",
                        "SCAN",
                        "LINK",
                        "SOFT",
                    ],
                    "lower_ctrl_limit": None,
                    "shape": [],
                    "source": "PV:25idc:LJT7Voltmeter_0:Ai2.NSTA",
                    "units": None,
                    "upper_ctrl_limit": None,
                },
                "I0_voltmeter_range": {
                    "dtype": "integer",
                    "enum_strs": [
                        "+= " "10V",
                        "+= " "1V",
                        "+= " "0.1V",
                        "+= " "0.01V",
                    ],
                    "lower_ctrl_limit": None,
                    "shape": [],
                    "source": "PV:25idc:LJT7Voltmeter_0:AiRange2",
                    "units": None,
                    "upper_ctrl_limit": None,
                },
                "I0_voltmeter_raw_value": {
                    "dtype": "integer",
                    "lower_ctrl_limit": -2147483648,
                    "shape": [],
                    "source": "PV:25idc:LJT7Voltmeter_0:Ai2.RVAL",
                    "units": "",
                    "upper_ctrl_limit": 2147483647,
                },
                "I0_voltmeter_resolution": {
                    "dtype": "integer",
                    "enum_strs": [
                        "Default",
                        "1",
                        "2",
                        "3",
                        "4",
                        "5",
                        "6",
                        "7",
                        "8",
                    ],
                    "lower_ctrl_limit": None,
                    "shape": [],
                    "source": "PV:25idc:LJT7Voltmeter_0:AiResolution2",
                    "units": None,
                    "upper_ctrl_limit": None,
                },
                "I0_voltmeter_scan_disable_input_link_value": {
                    "dtype": "integer",
                    "lower_ctrl_limit": -32768,
                    "shape": [],
                    "source": "PV:25idc:LJT7Voltmeter_0:Ai2.DISA",
                    "units": "",
                    "upper_ctrl_limit": 32767,
                },
                "I0_voltmeter_scan_disable_value_input_link": {
                    "dtype": "string",
                    "lower_ctrl_limit": None,
                    "shape": [],
                    "source": "PV:25idc:LJT7Voltmeter_0:Ai2.SDIS",
                    "units": None,
                    "upper_ctrl_limit": None,
                },
                "I0_voltmeter_scanning_rate": {
                    "dtype": "integer",
                    "enum_strs": [
                        "Passive",
                        "Event",
                        "I/O " "Intr",
                        "10 " "second",
                        "5 " "second",
                        "2 " "second",
                        "1 " "second",
                        ".5 " "second",
                        ".2 " "second",
                        ".1 " "second",
                    ],
                    "lower_ctrl_limit": None,
                    "shape": [],
                    "source": "PV:25idc:LJT7Voltmeter_0:Ai2.SCAN",
                    "units": None,
                    "upper_ctrl_limit": None,
                },
                "I0_voltmeter_temperature_units": {
                    "dtype": "integer",
                    "enum_strs": ["K", "C", "F"],
                    "lower_ctrl_limit": None,
                    "shape": [],
                    "source": "PV:25idc:LJT7Voltmeter_0:AiTempUnits2",
                    "units": None,
                    "upper_ctrl_limit": None,
                },
            },
            "timestamps": {
                "I0_channel_advance_source": 1706288136.019154,
                "I0_channel_one_source": 1715890566.204044,
                "I0_count_on_start": 1716408876.514808,
                "I0_description": 1716500670.770429,
                "I0_frequency": 1716500670.770429,
                "I0_gate": 1716500670.770429,
                "I0_max_channels": 1706288136.002487,
                "I0_num_channels_to_use": 1706288136.002487,
                "I0_offset": 631152000.0,
                "I0_preset_count": 1716500670.770429,
                "I0_record_dark_time": 631152000.0,
                "I0_voltmeter_alarm_severity": 1717042054.125238,
                "I0_voltmeter_alarm_status": 1717042054.125238,
                "I0_voltmeter_description": 1717041575.425234,
                "I0_voltmeter_device_type": 1717041573.025238,
                "I0_voltmeter_differential": 1715889930.536937,
                "I0_voltmeter_disable_alarm_severity": 1717041573.025238,
                "I0_voltmeter_disable_value": 1717041573.025238,
                "I0_voltmeter_forward_link": 1717041575.425234,
                "I0_voltmeter_high": 631152000.0,
                "I0_voltmeter_input_link": 1717041575.425234,
                "I0_voltmeter_low": 631152000.0,
                "I0_voltmeter_mode": 1715889930.536705,
                "I0_voltmeter_new_alarm_severity": 1717041573.025238,
                "I0_voltmeter_new_alarm_status": 1717041573.025238,
                "I0_voltmeter_range": 1715889930.537142,
                "I0_voltmeter_raw_value": 1717041573.025238,
                "I0_voltmeter_resolution": 1715889930.537357,
                "I0_voltmeter_scan_disable_input_link_value": 1717041573.025238,
                "I0_voltmeter_scan_disable_value_input_link": 1717041575.425234,
                "I0_voltmeter_scanning_rate": 1717041573.025238,
                "I0_voltmeter_temperature_units": 1715889930.536706,
            },
        }
    },
    "data_keys": {
        "I0_counts": {
            "dtype": "number",
            "lower_ctrl_limit": 0.0,
            "object_name": "I0",
            "precision": 0,
            "shape": [],
            "source": "PV:25idcVME:3820:scaler1.S4",
            "units": "",
            "upper_ctrl_limit": 0.0,
        },
        "I0_exposure_time": {
            "dtype": "number",
            "lower_ctrl_limit": 0.0,
            "object_name": "I0",
            "precision": 3,
            "shape": [],
            "source": "PV:25idcVME:3820:scaler1.TP",
            "units": "",
            "upper_ctrl_limit": 0.0,
        },
        "I0_net_counts": {
            "dtype": "number",
            "lower_ctrl_limit": 0.0,
            "object_name": "I0",
            "precision": 0,
            "shape": [],
            "source": "PV:25idcVME:3820:scaler1_netA.D",
            "units": "",
            "upper_ctrl_limit": 0.0,
        },
        "I0_voltmeter_amps": {
            "derived_from": "I0_voltmeter_volts",
            "dtype": "number",
            "lower_ctrl_limit": 0.0,
            "object_name": "I0",
            "precision": 4,
            "shape": [],
            "source": "SIM:I0_voltmeter_amps",
            "units": "",
            "upper_ctrl_limit": 0.0,
        },
        "I0_voltmeter_enable": {
            "dtype": "integer",
            "enum_strs": ["Disable", "Enable"],
            "lower_ctrl_limit": None,
            "object_name": "I0",
            "shape": [],
            "source": "PV:25idc:LJT7Voltmeter_0:AiEnable2",
            "units": None,
            "upper_ctrl_limit": None,
        },
        "I0_voltmeter_volts": {
            "dtype": "number",
            "lower_ctrl_limit": 0.0,
            "object_name": "I0",
            "precision": 4,
            "shape": [],
            "source": "PV:25idc:LJT7Voltmeter_0:Ai2.VAL",
            "units": "",
            "upper_ctrl_limit": 0.0,
        },
        "I0_volts": {
            "derived_from": "I0_counts",
            "dtype": "number",
            "lower_ctrl_limit": 0.0,
            "object_name": "I0",
            "precision": 0,
            "shape": [],
            "source": "SIM:I0_volts",
            "units": "",
            "upper_ctrl_limit": 0.0,
        },
    },
    "hints": {"I0": {"fields": ["I0_net_counts"]}},
    "name": "primary",
    "object_keys": {
        "I0": [
            "I0_voltmeter_enable",
            "I0_voltmeter_amps",
            "I0_voltmeter_volts",
            "I0_volts",
            "I0_counts",
            "I0_net_counts",
            "I0_exposure_time",
        ]
    },
    "run_start": "40b434c5-bec2-4eff-9cbe-c470b6435677",
    "time": 1717042074.559484,
    "uid": "bb592c67-1d8f-41f1-99fa-d4db6886ae03",
}


event_doc = {
    "data": {
        "I0_counts": 989354.0,
        "I0_exposure_time": 0.1,
        "I0_net_counts": 989354.0,
        "I0_voltmeter_amps": -5.713760852813812e-10,
        "I0_voltmeter_enable": 1,
        "I0_voltmeter_volts": 0.9942862391471863,
        "I0_volts": 9.893530106469894,
    },
    "descriptor": "bb592c67-1d8f-41f1-99fa-d4db6886ae03",
    "filled": {},
    "seq_num": 1,
    "time": 1717042074.5687447,
    "timestamps": {
        "I0_counts": 1717042074.414631,
        "I0_exposure_time": 1716500670.770429,
        "I0_net_counts": 631152000.0,
        "I0_voltmeter_amps": 1717042074.52525,
        "I0_voltmeter_enable": 1715889930.53229,
        "I0_voltmeter_volts": 1717042074.52525,
        "I0_volts": 1717042074.414631,
    },
    "uid": "3577aa5f-0605-4609-af60-e5f9a9bc462e",
}


stop_doc = {
    "exit_status": "success",
    "num_events": {"primary": 1},
    "reason": "",
    "run_start": "40b434c5-bec2-4eff-9cbe-c470b6435677",
    "time": 1717042074.5689151,
    "uid": "e9a17152-2e39-4f1b-acab-71aeb11e7222",
}
