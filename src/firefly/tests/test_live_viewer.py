import asyncio

import pytest

from firefly.live_viewer import LiveViewerDisplay


@pytest.fixture()
def display(affapp, catalog, event_loop):
    display = LiveViewerDisplay(root_node=catalog)
    display.clear_filters()
    # Flush pending async coroutines
    pending = asyncio.all_tasks(event_loop)
    event_loop.run_until_complete(asyncio.gather(*pending))
    assert all(task.done() for task in pending), "Init tasks not complete."
    # Yield displa to run the test
    try:
        yield display
    finally:
        pass
        # time.sleep(1)
        # # Cancel remaining tasks
        pending = asyncio.all_tasks(event_loop)
        event_loop.run_until_complete(asyncio.gather(*pending))
        assert all(task.done() for task in pending), "Shutdown tasks not complete."



def test_kafka_client(display):
    assert hasattr(display, "kafka_client")



consumed:  s25idc_queueserver-dev 0 4 b'kafka-unit-test-key' 1717042074437
(b'\x92\xa5start\xde\x00\x16\xa3uid\xd9$40b434c5-bec2-4eff-9cbe-c470b6435677'
 b'\xa4time\xcbA\xd9\x95\xfe\xe6\x9b\xf1H\xa8versions\x8b\xa8apstools\xb51.6.19'
 b'.dev52+ga165d24\xa7bluesky\xa81.13.0a3\xaadatabroker\xa51.2.5\xa8epics_'
 b'ca\xa53.5.2\xa5epics\xa53.5.2\xa5haven\xa723.10.0\xa4h5py\xa53.9.0\xaamatplo'
 b'tlib\xa53.8.4\xa5numpy\xa61.26.4\xa5ophyd\xa51.9.0\xa7pymongo\xa54.7.2\xa7sc'
 b'an_id\x02\xa9plan_type\xa9generator\xa9plan_name\xa5count\xafEPICS_HOST_AR'
 b'CH\xaclinux-x86_64\xabepics_libca\xd9O/home/beams0/S25STAFF/miniforge3/en'
 b'vs/haven-dev/epics/lib/linux-x86_64/libca.so\xb8EPICS_CA_MAX_ARRAY_BYTE'
 b'S\xa816777216\xabbeamline_id\xa725-ID-C\xabfacility_id\xb6Advanced Photon S'
 b'ource\xabxray_source\xb0insertion device\xa8login_id\xd9!s25staff@fedorov.xr'
 b'ay.aps.anl.gov\xa3pid\xce\x00\x10}y\xabsample_name\xa0\xaaparameters\xa0'
 b'\xa7purpose\xa0\xa9detectors\x91\xa2I0\xaanum_points\x01\xadnum_interval'
 b"s\x00\xa9plan_args\x83\xa9detectors\x91\xda\x03\xc9IonChamber(prefix='25idcV"
 b"ME:3820:', name='I0', read_attrs=['voltmeter', 'voltmeter.enable', 'voltmete"
 b"r.amps', 'voltmeter.volts', 'volts', 'counts', 'net_counts', 'exposure_time'"
 b"], configuration_attrs=['description', 'voltmeter', 'voltmeter.description',"
 b" 'voltmeter.scanning_rate', 'voltmeter.disable_value', 'voltmeter.scan_disab"
 b"le_input_link_value', 'voltmeter.scan_disable_value_input_link', 'voltmeter."
 b"forward_link', 'voltmeter.device_type', 'voltmeter.alarm_status', 'voltmeter"
 b".alarm_severity', 'voltmeter.new_alarm_status', 'voltmeter.new_alarm_severit"
 b"y', 'voltmeter.disable_alarm_severity', 'voltmeter.input_link', 'voltmeter.r"
 b"aw_value', 'voltmeter.differential', 'voltmeter.high', 'voltmeter.low', 'vol"
 b"tmeter.temperature_units', 'voltmeter.resolution', 'voltmeter.range', 'voltm"
 b"eter.mode', 'gate', 'preset_count', 'frequency', 'offset', 'record_dark_time"
 b"', 'channel_advance_source', 'num_channels_to_use', 'max_channels', 'channel"
 b"_one_source', 'count_on_start'])\xa3num\x01\xa5delay\xc0\xa5hints\x81\xaa"
 b'dimensions\x91\x92\x91\xa4time\xa7primary')
consumed:  s25idc_queueserver-dev 0 5 b'kafka-unit-test-key' 1717042074568
(b'\x92\xaadescriptor\x88\xadconfiguration\x81\xa2I0\x83\xa4data\xde\x00 '
 b'\xaeI0_description\xa2I0\xb8I0_voltmeter_description\xa2I0\xbaI0_voltmeter_'
 b'scanning_rate\t\xbaI0_voltmeter_disable_value\x01\xd9*I0_voltmeter_scan_di'
 b'sable_input_link_value\x00\xd9*I0_voltmeter_scan_disable_value_input_l'
 b'ink\xa0\xb9I0_voltmeter_forward_link\xa0\xb8I0_voltmeter_device_type'
 b'\x08\xb9I0_voltmeter_alarm_status\x00\xbbI0_voltmeter_alarm_severity'
 b'\x00\xbdI0_voltmeter_new_alarm_status\x00\xbfI0_voltmeter_new_alarm_severity'
 b'\x00\xd9#I0_voltmeter_disable_alarm_severity\x00\xb7I0_voltmeter_input_l'
 b'ink\xbf@asyn(LJT7V_0 2)ANALOG_IN_VALUE\xb6I0_voltmeter_raw_value\x00\xb9I0_v'
 b'oltmeter_differential\x00\xb1I0_voltmeter_high\xcb\x00\x00\x00'
 b'\x00\x00\x00\x00\x00\xb0I0_voltmeter_low\xcb\x00\x00\x00\x00\x00'
 b'\x00\x00\x00\xbeI0_voltmeter_temperature_units\x00\xb7I0_voltmeter_resolut'
 b'ion\x00\xb2I0_voltmeter_range\x00\xb1I0_voltmeter_mode\x00\xa7I0_gate\x00'
 b'\xafI0_preset_count\xcb\x00\x00\x00\x00\x00\x00\x00\x00\xacI0_frequency\xcbA'
 b'c\x12\xd0\x00\x00\x00\x00\xa9I0_offset\xcb\x00\x00\x00\x00\x00\x00'
 b'\x00\x00\xb3I0_record_dark_time\xcb\x00\x00\x00\x00\x00\x00\x00\x00\xb9I0_c'
 b'hannel_advance_source\x01\xb6I0_num_channels_to_use\xcd\x1f@\xafI0_max_chan'
 b'nels\xcd\x1f@\xb5I0_channel_one_source\x01\xb1I0_count_on_start\x01\xaati'
 b'mestamps\xde\x00 \xaeI0_description\xcbA\xd9\x93\xee/\xb1N\xb5\xb8I0_voltm'
 b'eter_description\xcbA\xd9\x95\xfei\xdb7\t\xbaI0_voltmeter_scanning_rate'
 b'\xcbA\xd9\x95\xfeiA\x9d\x80\xbaI0_voltmeter_disable_value\xcbA\xd9\x95'
 b'\xfeiA\x9d\x80\xd9*I0_voltmeter_scan_disable_input_link_value\xcbA\xd9'
 b'\x95\xfeiA\x9d\x80\xd9*I0_voltmeter_scan_disable_value_input_link\xcbA'
 b'\xd9\x95\xfei\xdb7\t\xb9I0_voltmeter_forward_link\xcbA\xd9\x95\xfei\xdb'
 b'7\t\xb8I0_voltmeter_device_type\xcbA\xd9\x95\xfeiA\x9d\x80\xb9I0_voltmete'
 b'r_alarm_status\xcbA\xd9\x95\xfe\xe1\x88\x03\xe6\xbbI0_voltmeter_alarm_sever'
 b'ity\xcbA\xd9\x95\xfe\xe1\x88\x03\xe6\xbdI0_voltmeter_new_alarm_status\xcbA'
 b'\xd9\x95\xfeiA\x9d\x80\xbfI0_voltmeter_new_alarm_severity\xcbA\xd9\x95\xfe'
 b'iA\x9d\x80\xd9#I0_voltmeter_disable_alarm_severity\xcbA\xd9\x95\xfeiA'
 b'\x9d\x80\xb7I0_voltmeter_input_link\xcbA\xd9\x95\xfei\xdb7\t\xb6I0_voltmeter'
 b'_raw_value\xcbA\xd9\x95\xfeiA\x9d\x80\xb9I0_voltmeter_differential\xcbA\xd9'
 b'\x91\x99\xc2\xa2]-\xb1I0_voltmeter_high\xcbA\xc2\xcfN\xc0\x00\x00\x00\xb0I0'
 b'_voltmeter_low\xcbA\xc2\xcfN\xc0\x00\x00\x00\xbeI0_voltmeter_temperature_uni'
 b'ts\xcbA\xd9\x91\x99\xc2\xa2Yd\xb7I0_voltmeter_resolution\xcbA\xd9\x91\x99'
 b'\xc2\xa2d\x0f\xb2I0_voltmeter_range\xcbA\xd9\x91\x99\xc2\xa2`\x89\xb1I0_volt'
 b'meter_mode\xcbA\xd9\x91\x99\xc2\xa2Y`\xa7I0_gate\xcbA\xd9\x93\xee/\xb1N\xb5'
 b'\xafI0_preset_count\xcbA\xd9\x93\xee/\xb1N\xb5\xacI0_frequency\xcbA'
 b'\xd9\x93\xee/\xb1N\xb5\xa9I0_offset\xcbA\xc2\xcfN\xc0\x00\x00\x00\xb3I0_re'
 b'cord_dark_time\xcbA\xc2\xcfN\xc0\x00\x00\x00\xb9I0_channel_advance_sourc'
 b'e\xcbA\xd9l\xf9\x02\x019\xd2\xb6I0_num_channels_to_use\xcbA\xd9l\xf9\x02\x00'
 b'(\xbf\xafI0_max_channels\xcbA\xd9l\xf9\x02\x00(\xbf\xb5I0_channel_one_sourc'
 b'e\xcbA\xd9\x91\x9aa\x8d\x0f\x0f\xb1I0_count_on_start\xcbA\xd9\x93'
 b'\x94\x8b \xf2\x9d\xa9data_keys\xde\x00 \xaeI0_description\x86\xa6sourc'
 b'e\xbcPV:25idcVME:3820:scaler1.NM4\xa5dtype\xa6string\xa5shape\x90\xa5units'
 b'\xc0\xb0lower_ctrl_limit\xc0\xb0upper_ctrl_limit\xc0\xb8I0_voltmeter_descr'
 b'iption\x86\xa6source\xd9!PV:25idc:LJT7Voltmeter_0:Ai2.DESC\xa5dtype\xa6stri'
 b'ng\xa5shape\x90\xa5units\xc0\xb0lower_ctrl_limit\xc0\xb0upper_ctrl_limit\xc0'
 b'\xbaI0_voltmeter_scanning_rate\x87\xa6source\xd9!PV:25idc:LJT7Voltmeter_0:Ai'
 b'2.SCAN\xa5dtype\xa7integer\xa5shape\x90\xa5units\xc0\xb0lower_ctrl_limit\xc0'
 b'\xb0upper_ctrl_limit\xc0\xa9enum_strs\x9a\xa7Passive\xa5Event\xa8I/O Intr'
 b'\xa910 second\xa85 second\xa82 second\xa81 second\xa9.5 second\xa9.2 secon'
 b'd\xa9.1 second\xbaI0_voltmeter_disable_value\x86\xa6source\xd9!PV:25idc:LJT'
 b'7Voltmeter_0:Ai2.DISV\xa5dtype\xa7integer\xa5shape\x90\xa5units\xa0\xb0lo'
 b'wer_ctrl_limit\xd1\x80\x00\xb0upper_ctrl_limit\xcd\x7f\xff\xd9*I0_voltmeter_'
 b'scan_disable_input_link_value\x86\xa6source\xd9!PV:25idc:LJT7Voltmeter_0:'
 b'Ai2.DISA\xa5dtype\xa7integer\xa5shape\x90\xa5units\xa0\xb0lower_ctrl_limi'
 b't\xd1\x80\x00\xb0upper_ctrl_limit\xcd\x7f\xff\xd9*I0_voltmeter_scan_disable_'
 b'value_input_link\x86\xa6source\xd9!PV:25idc:LJT7Voltmeter_0:Ai2.SDIS\xa5dtyp'
 b'e\xa6string\xa5shape\x90\xa5units\xc0\xb0lower_ctrl_limit\xc0\xb0upper_ctrl_'
 b'limit\xc0\xb9I0_voltmeter_forward_link\x86\xa6source\xd9!PV:25idc:LJT7Voltm'
 b'eter_0:Ai2.FLNK\xa5dtype\xa6string\xa5shape\x90\xa5units\xc0\xb0lower_ctr'
 b'l_limit\xc0\xb0upper_ctrl_limit\xc0\xb8I0_voltmeter_device_type\x87\xa6sou'
 b'rce\xd9!PV:25idc:LJT7Voltmeter_0:Ai2.DTYP\xa5dtype\xa7integer\xa5sha'
 b'pe\x90\xa5units\xc0\xb0lower_ctrl_limit\xc0\xb0upper_ctrl_limit\xc0\xa9enum_'
 b'strs\xdc\x00\x10\xacSoft Channel\xb0Raw Soft Channel\xb2Async Soft Channel'
 b'\xaeSoft Timestamp\xacGeneral Time\xa9asynInt32\xb0asynInt32Average\xabasyn'
 b'Float64\xb2asynFloat64Average\xa9asynInt64\xa9IOC stats\xb0IOC stats clu'
 b'sts\xb0GPIB init/report\xaeSec Past Epoch\xb2asyn ai stringParm\xb1asyn ai H'
 b'eidND261\xb9I0_voltmeter_alarm_status\x87\xa6source\xd9!PV:25idc:LJT7Voltmet'
 b'er_0:Ai2.STAT\xa5dtype\xa7integer\xa5shape\x90\xa5units\xc0\xb0lower_ctrl'
 b'_limit\xc0\xb0upper_ctrl_limit\xc0\xa9enum_strs\xdc\x00\x10\xa8NO_ALARM\xa4'
 b'READ\xa5WRITE\xa4HIHI\xa4HIGH\xa4LOLO\xa3LOW\xa5STATE\xa3COS\xa4COMM\xa7TIM'
 b'EOUT\xa7HWLIMIT\xa4CALC\xa4SCAN\xa4LINK\xa4SOFT\xbbI0_voltmeter_alarm_seve'
 b'rity\x87\xa6source\xd9!PV:25idc:LJT7Voltmeter_0:Ai2.SEVR\xa5dtype\xa7intege'
 b'r\xa5shape\x90\xa5units\xc0\xb0lower_ctrl_limit\xc0\xb0upper_ctrl_lim'
 b'it\xc0\xa9enum_strs\x94\xa8NO_ALARM\xa5MINOR\xa5MAJOR\xa7INVALID\xbdI0_voltm'
 b'eter_new_alarm_status\x87\xa6source\xd9!PV:25idc:LJT7Voltmeter_0:Ai2.NSTA'
 b'\xa5dtype\xa7integer\xa5shape\x90\xa5units\xc0\xb0lower_ctrl_limit\xc0\xb0u'
 b'pper_ctrl_limit\xc0\xa9enum_strs\xdc\x00\x10\xa8NO_ALARM\xa4READ\xa5WRIT'
 b'E\xa4HIHI\xa4HIGH\xa4LOLO\xa3LOW\xa5STATE\xa3COS\xa4COMM\xa7TIMEOUT\xa7HWLI'
 b'MIT\xa4CALC\xa4SCAN\xa4LINK\xa4SOFT\xbfI0_voltmeter_new_alarm_severity\x87'
 b'\xa6source\xd9!PV:25idc:LJT7Voltmeter_0:Ai2.NSEV\xa5dtype\xa7integer\xa5sha'
 b'pe\x90\xa5units\xc0\xb0lower_ctrl_limit\xc0\xb0upper_ctrl_limit\xc0\xa9enum_'
 b'strs\x94\xa8NO_ALARM\xa5MINOR\xa5MAJOR\xa7INVALID\xd9#I0_voltmeter_disable'
 b'_alarm_severity\x87\xa6source\xd9!PV:25idc:LJT7Voltmeter_0:Ai2.DISS\xa5dtype'
 b'\xa7integer\xa5shape\x90\xa5units\xc0\xb0lower_ctrl_limit\xc0\xb0upper_ctrl_'
 b'limit\xc0\xa9enum_strs\x94\xa8NO_ALARM\xa5MINOR\xa5MAJOR\xa7INVALID\xb7I0_vo'
 b'ltmeter_input_link\x86\xa6source\xd9 PV:25idc:LJT7Voltmeter_0:Ai2.INP\xa5dty'
 b'pe\xa6string\xa5shape\x90\xa5units\xc0\xb0lower_ctrl_limit\xc0\xb0upper_ctrl'
 b'_limit\xc0\xb6I0_voltmeter_raw_value\x86\xa6source\xd9!PV:25idc:LJT7Voltmet'
 b'er_0:Ai2.RVAL\xa5dtype\xa7integer\xa5shape\x90\xa5units\xa0\xb0lower_ctrl'
 b'_limit\xd2\x80\x00\x00\x00\xb0upper_ctrl_limit\xce\x7f\xff\xff\xff\xb9I0_vol'
 b'tmeter_differential\x87\xa6source\xd9 PV:25idc:LJT7Voltmeter_0:AiDiff2\xa5dt'
 b'ype\xa7integer\xa5shape\x90\xa5units\xc0\xb0lower_ctrl_limit\xc0\xb0upper_ct'
 b'rl_limit\xc0\xa9enum_strs\x92\xacSingle-Ended\xacDifferential\xb1I0_voltme'
 b'ter_high\x87\xa6source\xd9 PV:25idc:LJT7Voltmeter_0:AiHOPR2\xa5dtype\xa6num'
 b'ber\xa5shape\x90\xa5units\xa0\xb0lower_ctrl_limit\xcb\x00\x00\x00\x00\x00'
 b'\x00\x00\x00\xb0upper_ctrl_limit\xcb\x00\x00\x00\x00\x00\x00\x00\x00\xa9pr'
 b'ecision\x04\xb0I0_voltmeter_low\x87\xa6source\xd9 PV:25idc:LJT7Voltmeter_0:'
 b'AiLOPR2\xa5dtype\xa6number\xa5shape\x90\xa5units\xa0\xb0lower_ctrl_limit\xcb'
 b'\x00\x00\x00\x00\x00\x00\x00\x00\xb0upper_ctrl_limit\xcb\x00\x00'
 b'\x00\x00\x00\x00\x00\x00\xa9precision\x04\xbeI0_voltmeter_temperature_units'
 b'\x87\xa6source\xd9%PV:25idc:LJT7Voltmeter_0:AiTempUnits2\xa5dtype\xa7intege'
 b'r\xa5shape\x90\xa5units\xc0\xb0lower_ctrl_limit\xc0\xb0upper_ctrl_lim'
 b'it\xc0\xa9enum_strs\x93\xa1K\xa1C\xa1F\xb7I0_voltmeter_resolution\x87\xa6so'
 b'urce\xd9&PV:25idc:LJT7Voltmeter_0:AiResolution2\xa5dtype\xa7integer\xa5shape'
 b'\x90\xa5units\xc0\xb0lower_ctrl_limit\xc0\xb0upper_ctrl_limit\xc0\xa9enum_st'
 b'rs\x99\xa7Default\xa11\xa12\xa13\xa14\xa15\xa16\xa17\xa18\xb2I0_voltmeter'
 b'_range\x87\xa6source\xd9!PV:25idc:LJT7Voltmeter_0:AiRange2\xa5dtype\xa7inte'
 b'ger\xa5shape\x90\xa5units\xc0\xb0lower_ctrl_limit\xc0\xb0upper_ctrl_limit'
 b'\xc0\xa9enum_strs\x94\xa6+= 10V\xa5+= 1V\xa7+= 0.1V\xa8+= 0.01V\xb1I0_voltme'
 b'ter_mode\x87\xa6source\xd9 PV:25idc:LJT7Voltmeter_0:AiMode2\xa5dtype\xa7int'
 b'eger\xa5shape\x90\xa5units\xc0\xb0lower_ctrl_limit\xc0\xb0upper_ctrl_limi'
 b't\xc0\xa9enum_strs\x9a\xa5Volts\xa9Type B TC\xa9Type C TC\xa9Type E TC\xa9Ty'
 b'pe J TC\xa9Type K TC\xa9Type N TC\xa9Type R TC\xa9Type S TC\xa9Type T T'
 b'C\xa7I0_gate\x87\xa6source\xbbPV:25idcVME:3820:scaler1.G4\xa5dtype\xa7inte'
 b'ger\xa5shape\x90\xa5units\xc0\xb0lower_ctrl_limit\xc0\xb0upper_ctrl_limit'
 b'\xc0\xa9enum_strs\x92\xa1N\xa1Y\xafI0_preset_count\x87\xa6source\xbcPV:25id'
 b'cVME:3820:scaler1.PR4\xa5dtype\xa6number\xa5shape\x90\xa5units\xa0\xb0low'
 b'er_ctrl_limit\xcb\x00\x00\x00\x00\x00\x00\x00\x00\xb0upper_ctrl_limit\xcb'
 b'\x00\x00\x00\x00\x00\x00\x00\x00\xa9precision\x00\xacI0_frequency\x87\xa6so'
 b'urce\xbdPV:25idcVME:3820:scaler1.FREQ\xa5dtype\xa6number\xa5shape\x90\xa5u'
 b'nits\xa0\xb0lower_ctrl_limit\xcb\x00\x00\x00\x00\x00\x00\x00\x00\xb0upper_ct'
 b'rl_limit\xcb\x00\x00\x00\x00\x00\x00\x00\x00\xa9precision\x03\xa9I0_offs'
 b'et\x87\xa6source\xd9"PV:25idcVME:3820:scaler1_offset0.D\xa5dtype\xa6num'
 b'ber\xa5shape\x90\xa5units\xa0\xb0lower_ctrl_limit\xcb\x00\x00\x00\x00\x00'
 b'\x00\x00\x00\xb0upper_ctrl_limit\xcb\x00\x00\x00\x00\x00\x00\x00\x00\xa9pr'
 b'ecision\x00\xb3I0_record_dark_time\x87\xa6source\xd9(PV:25idcVME:3820:scale'
 b'r1_offset_time.VAL\xa5dtype\xa6number\xa5shape\x90\xa5units\xa0\xb0lower_'
 b'ctrl_limit\xcb\x00\x00\x00\x00\x00\x00\x00\x00\xb0upper_ctrl_limit'
 b'\xcb\x00\x00\x00\x00\x00\x00\x00\x00\xa9precision\x00\xb9I0_channel_advance_'
 b'source\x87\xa6source\xbfPV:25idcVME:3820:ChannelAdvance\xa5dtype\xa7integer'
 b'\xa5shape\x90\xa5units\xc0\xb0lower_ctrl_limit\xc0\xb0upper_ctrl_limi'
 b't\xc0\xa9enum_strs\x92\xa8Internal\xa8External\xb6I0_num_channels_to_u'
 b'se\x86\xa6source\xb8PV:25idcVME:3820:NuseAll\xa5dtype\xa7integer\xa5sh'
 b'ape\x90\xa5units\xa0\xb0lower_ctrl_limit\x00\xb0upper_ctrl_limit\x00\xafI0_m'
 b'ax_channels\x86\xa6source\xbcPV:25idcVME:3820:MaxChannels\xa5dtype\xa7integ'
 b'er\xa5shape\x90\xa5units\xa0\xb0lower_ctrl_limit\x00\xb0upper_ctrl_limit\x00'
 b'\xb5I0_channel_one_source\x87\xa6source\xbfPV:25idcVME:3820:Channel1Sour'
 b'ce\xa5dtype\xa7integer\xa5shape\x90\xa5units\xc0\xb0lower_ctrl_limit\xc0'
 b'\xb0upper_ctrl_limit\xc0\xa9enum_strs\x92\xaaInt. clock\xa8External\xb1I0'
 b'_count_on_start\x87\xa6source\xbdPV:25idcVME:3820:CountOnStart\xa5dtype\xa7'
 b'integer\xa5shape\x90\xa5units\xc0\xb0lower_ctrl_limit\xc0\xb0upper_ctrl_l'
 b'imit\xc0\xa9enum_strs\x92\xa2No\xa3Yes\xa9data_keys\x87\xb3I0_voltmeter_enab'
 b'le\x88\xa6source\xd9"PV:25idc:LJT7Voltmeter_0:AiEnable2\xa5dtype\xa7integer'
 b'\xa5shape\x90\xa5units\xc0\xb0lower_ctrl_limit\xc0\xb0upper_ctrl_limi'
 b't\xc0\xa9enum_strs\x92\xa7Disable\xa6Enable\xabobject_name\xa2I0\xb1I0_voltm'
 b'eter_amps\x89\xa6source\xb5SIM:I0_voltmeter_amps\xa5dtype\xa6number\xa5sha'
 b'pe\x90\xa5units\xa0\xb0lower_ctrl_limit\xcb\x00\x00\x00\x00\x00\x00\x00\x00'
 b'\xb0upper_ctrl_limit\xcb\x00\x00\x00\x00\x00\x00\x00\x00\xa9precision'
 b'\x04\xacderived_from\xb2I0_voltmeter_volts\xabobject_name\xa2I0\xb2I0_volt'
 b'meter_volts\x88\xa6source\xd9 PV:25idc:LJT7Voltmeter_0:Ai2.VAL\xa5dtype\xa6'
 b'number\xa5shape\x90\xa5units\xa0\xb0lower_ctrl_limit\xcb\x00\x00'
 b'\x00\x00\x00\x00\x00\x00\xb0upper_ctrl_limit\xcb\x00\x00\x00\x00'
 b'\x00\x00\x00\x00\xa9precision\x04\xabobject_name\xa2I0\xa8I0_volts\x89'
 b'\xa6source\xacSIM:I0_volts\xa5dtype\xa6number\xa5shape\x90\xa5units\xa0\xb0'
 b'lower_ctrl_limit\xcb\x00\x00\x00\x00\x00\x00\x00\x00\xb0upper_ctrl_lim'
 b'it\xcb\x00\x00\x00\x00\x00\x00\x00\x00\xa9precision\x00\xacderived_from\xa9'
 b'I0_counts\xabobject_name\xa2I0\xa9I0_counts\x88\xa6source\xbbPV:25idcVME:3'
 b'820:scaler1.S4\xa5dtype\xa6number\xa5shape\x90\xa5units\xa0\xb0lower_ctrl'
 b'_limit\xcb\x00\x00\x00\x00\x00\x00\x00\x00\xb0upper_ctrl_limit'
 b'\xcb\x00\x00\x00\x00\x00\x00\x00\x00\xa9precision\x00\xabobject_name'
 b'\xa2I0\xadI0_net_counts\x88\xa6source\xbfPV:25idcVME:3820:scaler1_netA.'
 b'D\xa5dtype\xa6number\xa5shape\x90\xa5units\xa0\xb0lower_ctrl_limi'
 b't\xcb\x00\x00\x00\x00\x00\x00\x00\x00\xb0upper_ctrl_limit\xcb'
 b'\x00\x00\x00\x00\x00\x00\x00\x00\xa9precision\x00\xabobject_name\xa2I0\xb0I'
 b'0_exposure_time\x88\xa6source\xbbPV:25idcVME:3820:scaler1.TP\xa5dtype\xa6nu'
 b'mber\xa5shape\x90\xa5units\xa0\xb0lower_ctrl_limit\xcb\x00\x00\x00\x00'
 b'\x00\x00\x00\x00\xb0upper_ctrl_limit\xcb\x00\x00\x00\x00\x00\x00'
 b'\x00\x00\xa9precision\x03\xabobject_name\xa2I0\xa4name\xa7primary\xabobject'
 b'_keys\x81\xa2I0\x97\xb3I0_voltmeter_enable\xb1I0_voltmeter_amps\xb2I0_volt'
 b'meter_volts\xa8I0_volts\xa9I0_counts\xadI0_net_counts\xb0I0_exposure_tim'
 b'e\xa9run_start\xd9$40b434c5-bec2-4eff-9cbe-c470b6435677\xa4time\xcbA'
 b'\xd9\x95\xfe\xe6\xa3\xce\x96\xa3uid\xd9$bb592c67-1d8f-41f1-99fa-d4db6886ae0'
 b'3\xa5hints\x81\xa2I0\x81\xa6fields\x91\xadI0_net_counts')
consumed:  s25idc_queueserver-dev 0 6 b'kafka-unit-test-key' 1717042074568
(b'\x92\xa5event\x87\xa3uid\xd9$3577aa5f-0605-4609-af60-e5f9a9bc462e\xa4t'
 b'ime\xcbA\xd9\x95\xfe\xe6\xa4fP\xa4data\x87\xb3I0_voltmeter_enable\x01\xb1'
 b'I0_voltmeter_amps\xcb\xbe\x03\xa1\xe0\x8f\xf80\x80\xb2I0_voltmeter_volt'
 b"s\xcb?\xef\xd11`\x00\x00\x00\xa8I0_volts\xcb@#\xc9|\xc72\x8f'\xa9I0_coun"
 b'ts\xcbA.1T\x00\x00\x00\x00\xadI0_net_counts\xcbA.1T\x00\x00\x00\x00\xb0I0_ex'
 b'posure_time\xcb?\xb9\x99\x99\x99\x99\x99\x9a\xaatimestamps\x87\xb3I0_volt'
 b'meter_enable\xcbA\xd9\x91\x99\xc2\xa2\x11\n\xb1I0_voltmeter_amps\xcb'
 b'A\xd9\x95\xfe\xe6\xa1\x9d\xb2\xb2I0_voltmeter_volts\xcbA\xd9\x95\xfe'
 b'\xe6\xa1\x9d\xb2\xa8I0_volts\xcbA\xd9\x95\xfe\xe6\x9a\x89P\xa9I0_counts'
 b'\xcbA\xd9\x95\xfe\xe6\x9a\x89P\xadI0_net_counts\xcbA\xc2\xcfN'
 b'\xc0\x00\x00\x00\xb0I0_exposure_time\xcbA\xd9\x93\xee/\xb1N\xb5\xa7seq_n'
 b'um\x01\xa6filled\x80\xaadescriptor\xd9$bb592c67-1d8f-41f1-99fa-d4db6886ae03')
consumed:  s25idc_queueserver-dev 0 7 b'kafka-unit-test-key' 1717042074569
(b'\x92\xa4stop\x86\xa3uid\xd9$e9a17152-2e39-4f1b-acab-71aeb11e7222\xa4ti'
 b'me\xcbA\xd9\x95\xfe\xe6\xa4i\x1b\xa9run_start\xd9$40b434c5-bec2-4eff-9cbe-c'
 b'470b6435677\xabexit_status\xa7success\xa6reason\xa0\xaanum_events\x81\xa7'
 b'primary\x01')
    
