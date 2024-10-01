from tiled.adapters.mapping import MapAdapter
from tiled.adapters.xarray import DatasetAdapter
import pandas as pd

position_runs = {
    # Existing entries
    "a9b3e0fa-eba1-43e0-a38c-c7ac76278000": MapAdapter(
        {
            "primary": MapAdapter(
                {
                    "data": DatasetAdapter.from_dataset(
                        pd.DataFrame(
                            {
                                "motor_A": [12.0],
                                "motor_B": [-113.25],
                            }
                        ).to_xarray()
                    ),
                },
                metadata={
                    "descriptors": [
                        {
                            "data_keys": {
                                "motor_A": {"object_name": "motor_A"},
                                "motor_B": {"object_name": "motor_B"},
                            },
                        }
                    ],
                },
            ),
        },
        metadata={
            "plan_name": "save_motor_position",
            "position_name": "Good position A",
            "time": 1725897133,
            "uid": "a9b3e0fa-eba1-43e0-a38c-c7ac76278000",
            "start": {
                "plan_name": "save_motor_position",
                "position_name": "Good position A",
                "time": 1725897133,
                "uid": "a9b3e0fa-eba1-43e0-a38c-c7ac76278000",
            },
        },
    ),
    "1b7f2ef5-6a3c-496e-9f6f-f1a4805c0065": MapAdapter(
        {
            "primary": MapAdapter(
                {
                    "data": DatasetAdapter.from_dataset(
                        pd.DataFrame(
                            {
                                "motorC": [11250.0],
                            }
                        ).to_xarray()
                    ),
                },
                metadata={
                    "descriptors": [
                        {
                            "data_keys": {
                                "motorC": {"object_name": "motorC"},
                            },
                        }
                    ],
                },
            ),
        },
        metadata={
            "plan_name": "save_motor_position",
            "position_name": "Another good position",
            "time": 1725897193,
            "uid": "1b7f2ef5-6a3c-496e-9f6f-f1a4805c0065",
            "start": {
                "plan_name": "save_motor_position",
                "position_name": "Another good position",
                "time": 1725897193,
                "uid": "1b7f2ef5-6a3c-496e-9f6f-f1a4805c0065",
            },
        },
    ),
    "5dd9a185-d5c4-4c8b-a719-9d7beb9007dc": MapAdapter(
        {
            "primary": MapAdapter(
                {
                    "data": DatasetAdapter.from_dataset(
                        pd.DataFrame(
                            {
                                "motorC": [11250.0],
                            }
                        ).to_xarray()
                    ),
                },
                metadata={
                    "descriptors": [
                        {
                            "data_keys": {
                                "motorC": {"object_name": "motorC"},
                            },
                        }
                    ],
                },
            ),
        },
        metadata={
            "plan_name": "save_motor_position",
            "position_name": "Another good position",
            "time": 1725897033,
            "uid": "5dd9a185-d5c4-4c8b-a719-9d7beb9007dc",
            "start": {
                "plan_name": "save_motor_position",
                "position_name": "Another good position",
                "time": 1725897033,
                "uid": "5dd9a185-d5c4-4c8b-a719-9d7beb9007dc",
            },
        },
    ),
    "42b8c45d-e98d-4f59-9ce8-8f14134c90bd": MapAdapter(
        {
            "primary": MapAdapter(
                {
                    "data": DatasetAdapter.from_dataset(
                        pd.DataFrame(
                            {
                                "motorC": [11250.0],
                            }
                        ).to_xarray()
                    ),
                },
                metadata={
                    "descriptors": [
                        {
                            "data_keys": {
                                "motorC": {"object_name": "motorC"},
                            },
                        }
                    ],
                },
            ),
        },
        metadata={
            "plan_name": "save_motor_position",
            "position_name": "Another good position",
            "time": 1725897233,
            "uid": "42b8c45d-e98d-4f59-9ce8-8f14134c90bd",
            "start": {
                "plan_name": "save_motor_position",
                "position_name": "Another good position",
                "time": 1725897233,
                "uid": "42b8c45d-e98d-4f59-9ce8-8f14134c90bd",
            },
        },
    ),
    "9bcd07e9-3188-49d3-a1ce-e3b51ebe48b5": MapAdapter(
        {},
        metadata={
            "plan_name": "xafs_scan",
            "time": 1725897133,
        },
    ),
    # New entries added from fake data
    "e1f2d3c4-5b6a-7d8e-9f0a-1b2c3d4e5f60": MapAdapter(
        {
            "primary": MapAdapter(
                {
                    "data": DatasetAdapter.from_dataset(
                        pd.DataFrame(
                            {
                                "SLT V Upper": [510.5],
                                "SLT V Upper_offset": [0.0],
                                "SLT V Lower": [-211.93],
                            }
                        ).to_xarray()
                    ),
                },
                metadata={
                    "descriptors": [
                        {
                            "data_keys": {
                                "SLT V Upper": {"object_name": "SLT V Upper"},
                                "SLT V Upper_offset": {"object_name": "SLT V Upper_offset"},
                                "SLT V Lower": {"object_name": "SLT V Lower"},
                            },
                        }
                    ],
                },
            ),
        },
        metadata={
            "plan_name": "save_motor_position",
            "position_name": "Good position A",
            "time": 1660907451.0,
            "uid": "e1f2d3c4-5b6a-7d8e-9f0a-1b2c3d4e5f60",
            "start": {
                "plan_name": "save_motor_position",
                "position_name": "Good position A",
                "time": 1660907451.0,
                "uid": "e1f2d3c4-5b6a-7d8e-9f0a-1b2c3d4e5f60",
            },
        },
    ),
    "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c60": MapAdapter(
        {
            "primary": MapAdapter(
                {
                    "data": DatasetAdapter.from_dataset(
                        pd.DataFrame(
                            {
                                "sam_H": [10.1],
                                "sam_H_offset": [0.1],
                                "sam_V": [-20.95],
                                "sam_V_offset": [-0.05],
                            }
                        ).to_xarray()
                    ),
                },
                metadata={
                    "descriptors": [
                        {
                            "data_keys": {
                                "sam_H": {"object_name": "sam_H"},
                                "sam_H_offset": {"object_name": "sam_H_offset"},
                                "sam_V": {"object_name": "sam_V"},
                                "sam_V_offset": {"object_name": "sam_V_offset"},
                            },
                        }
                    ],
                },
            ),
        },
        metadata={
            "plan_name": "save_motor_position",
            "position_name": "Good Sample position",
            "time": 1723236837.230731,
            "uid": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c60",
            "start": {
                "plan_name": "save_motor_position",
                "position_name": "Good Sample position",
                "time": 1723236837.230731,
                "uid": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c60",
            },
        },
    ),
    "f0e9d8c7-b6a5-4d3c-2b1a-9f8e7d6c5b4a": MapAdapter(
        {
            "primary": MapAdapter(
                {
                    "data": DatasetAdapter.from_dataset(
                        pd.DataFrame(
                            {
                                "vortex_in": [6.1],
                            }
                        ).to_xarray()
                    ),
                },
                metadata={
                    "descriptors": [
                        {
                            "data_keys": {
                                "vortex_in": {"object_name": "vortex_in"},
                            },
                        }
                    ],
                },
            ),
        },
        metadata={
            "plan_name": "save_motor_position",
            "position_name": "Vortex_pos1",
            "time": 1723236915.988184,
            "uid": "f0e9d8c7-b6a5-4d3c-2b1a-9f8e7d6c5b4a",
            "start": {
                "plan_name": "save_motor_position",
                "position_name": "Vortex_pos1",
                "time": 1723236915.988184,
                "uid": "f0e9d8c7-b6a5-4d3c-2b1a-9f8e7d6c5b4a",
            },
        },
    ),
    "0a1b2c3d-4e5f-6a7b-8c9d-0e1f2a3b4c5d": MapAdapter(
        {
            "primary": MapAdapter(
                {
                    "data": DatasetAdapter.from_dataset(
                        pd.DataFrame(
                            {
                                "fakePitch": [832678.1],
                                "fakePitch_offset": [3525.1],
                                "fakeBragg": [789231.97321],
                                "fakeBragg_offset": [45612.543],
                                "fakeHoriz": [78239087149.231],
                                "fakeHoriz_offset": [5280.3452],
                                "fakeVert": [65843296.4321],
                                "fakeVert_offset": [5143.314],
                                "fakeGap": [80214.25],
                                "fakeGap_offset": [5890.213],
                            }
                        ).to_xarray()
                    ),
                },
                metadata={
                    "descriptors": [
                        {
                            "data_keys": {
                                "fakePitch": {"object_name": "fakePitch"},
                                "fakePitch_offset": {"object_name": "fakePitch_offset"},
                                "fakeBragg": {"object_name": "fakeBragg"},
                                "fakeBragg_offset": {"object_name": "fakeBragg_offset"},
                                "fakeHoriz": {"object_name": "fakeHoriz"},
                                "fakeHoriz_offset": {"object_name": "fakeHoriz_offset"},
                                "fakeVert": {"object_name": "fakeVert"},
                                "fakeVert_offset": {"object_name": "fakeVert_offset"},
                                "fakeGap": {"object_name": "fakeGap"},
                                "fakeGap_offset": {"object_name": "fakeGap_offset"},
                            },
                        }
                    ],
                },
            ),
        },
        metadata={
            "plan_name": "save_motor_position",
            "position_name": "Fake_mono_position",
            "time": 1660907851.5,
            "uid": "0a1b2c3d-4e5f-6a7b-8c9d-0e1f2a3b4c5d",
            "start": {
                "plan_name": "save_motor_position",
                "position_name": "Fake_mono_position",
                "time": 1660907851.5,
                "uid": "0a1b2c3d-4e5f-6a7b-8c9d-0e1f2a3b4c5d",
            },
        },
    ),
}
