import logging
import warnings

from bluesky import RunEngine as BlueskyRunEngine
import databroker

from ._iconfig import load_config
from .preprocessors import inject_haven_md_wrapper

log = logging.getLogger(__name__)


class RunEngine(BlueskyRunEngine):
    def __init__(self, *args, connect_databroker=True, **kwargs):
        super().__init__(*args, **kwargs)
        if connect_databroker:
            # Load the databroker catalog and set up data saving
            catalog_name = load_config()["database"]["databroker"]["catalog"]
            try:
                catalog = databroker.catalog[catalog_name]
                self.subscribe(catalog.v1.insert)
            except Exception as e:
                msg = (
                    f"Data are not being saved! Could not load databroker catalog: {e}"
                )
                log.error(msg)
                warnings.warn(msg)
                raise RuntimeError(msg)
        # Add metadata pre-processor
        self.preprocessors.append(inject_haven_md_wrapper)
