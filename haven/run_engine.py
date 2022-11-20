from bluesky import RunEngine as BlueskyRunEngine
import databroker


class RunEngine(BlueskyRunEngine):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Register the databroker catalog
        catalog = databroker.catalog["bluesky"]
        self.subscribe(catalog.v1.insert)
