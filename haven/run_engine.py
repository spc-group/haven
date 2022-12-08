from bluesky import RunEngine as BlueskyRunEngine
import databroker

from ._iconfig import load_config


class RunEngine(BlueskyRunEngine):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Register the databroker catalog
        config = load_config()["database"]["databroker"]
        catalog = databroker.catalog[config["catalog"]]
        self.subscribe(catalog.v1.insert)
