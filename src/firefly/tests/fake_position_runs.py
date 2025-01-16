import pandas as pd
from tiled.adapters.mapping import MapAdapter
from tiled.adapters.xarray import DatasetAdapter
from tiled.adapters.table import TableAdapter

position_runs = {
    "a9b3e0fa-eba1-43e0-a38c-c7ac76278000": MapAdapter(
        {
            "primary": MapAdapter(
                {
                    "internal": MapAdapter(
                        {
                            "events": TableAdapter.from_pandas(
                                pd.DataFrame(
                                    {
                                        "motor_A": [12.0],
                                        "motor_B": [-113.25],
                                    }
                                )
                            ),
                        }
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
    # A second saved motor position
    "1b7f2ef5-6a3c-496e-9f6f-f1a4805c0065": MapAdapter(
        {
            "primary": MapAdapter(
                {
                    "internal": MapAdapter(
                        {
                            "events": TableAdapter.from_pandas(
                                pd.DataFrame(
                                    {
                                        "motorC": [11250.0],
                                    }
                                )
                            ),
                        }
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
            "position_name": "A good position B",
            "time": 1725897193,
            "uid": "1b7f2ef5-6a3c-496e-9f6f-f1a4805c0065",
            "start": {
                "plan_name": "save_motor_position",
                "position_name": "A good position B",
                "time": 1725897193,
                "uid": "1b7f2ef5-6a3c-496e-9f6f-f1a4805c0065",
            },
        },
    ),
    
    # A third saved motor position
    "1b7f2ef5-6a3c-496e-9f6f-f1a4805c0067": MapAdapter(
        {
            "primary": MapAdapter(
                {
                    "internal": MapAdapter(
                        {
                            "events": TableAdapter.from_pandas(
                                pd.DataFrame(
                                    {
                                        "motorD": [1.8932107438],
                                    }
                                )
                            ),
                        }
                    ),
                },
                metadata={
                    "descriptors": [
                        {
                            "data_keys": {
                                "motorD": {"object_name": "motorD"},
                            },
                        }
                    ],
                },
            ),
        },
        metadata={
            "plan_name": "save_motor_position",
            "position_name": "A good position B",
            "time": 1725897193,
            "uid": "1b7f2ef5-6a3c-496e-9f6f-f1a4805c0067",
            "start": {
                "plan_name": "save_motor_position",
                "position_name": "A good position B",
                "time": 1725897193,
                "uid": "1b7f2ef5-6a3c-496e-9f6f-f1a4805c0067",
            },
        },
    ),
    # A saved motor position, but older style
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
            "position_name": "Good position C",
            "time": 1725897033,
            "uid": "5dd9a185-d5c4-4c8b-a719-9d7beb9007dc",
            "start": {
                "plan_name": "save_motor_position",
                "position_name": "Good position C",
                "time": 1725897033,
                "uid": "5dd9a185-d5c4-4c8b-a719-9d7beb9007dc",
            },
        },
    ),
    # A saved motor position, but older
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
                "time": 17258972333,
                "uid": "42b8c45d-e98d-4f59-9ce8-8f14134c90bd",
            },
        },
    ),
    # A scan that's not a saved motor position
    "9bcd07e9-3188-49d3-a1ce-e3b51ebe48b5": MapAdapter(
        {},
        metadata={
            "plan_name": "xafs_scan",
            "time": 1725897133,
        },
    ),
}
