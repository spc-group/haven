import logging

import databroker
from bluesky import RunEngine as BlueskyRunEngine
from bluesky import suspenders
from bluesky.callbacks.best_effort import BestEffortCallback

from .exceptions import ComponentNotFound
from .instrument.instrument_registry import registry
from .preprocessors import inject_haven_md_wrapper

log = logging.getLogger(__name__)


catalog = None


def save_data(name, doc):
    # This is a hack around a problem with garbage collection
    # Has been fixed in main, maybe released in databroker v2?
    # Create the databroker callback if necessary
    global catalog
    if catalog is None:
        catalog = databroker.catalog["bluesky"]
    # Save the document
    catalog.v1.insert(name, doc)


def run_engine(connect_databroker=True, use_bec=True) -> BlueskyRunEngine:
    RE = BlueskyRunEngine()
    # Add the best-effort callback
    if use_bec:
        RE.subscribe(BestEffortCallback())
    # Install suspenders
    try:
        aps = registry.find("APS")
    except ComponentNotFound:
        log.warning("APS device not found, suspenders not installed.")
    else:
        # Suspend when shutter permit is disabled
        RE.install_suspender(
            suspenders.SuspendWhenChanged(
                signal=aps.shutter_permit,
                expected_value="PERMIT",
                allow_resume=True,
                sleep=3,
                tripped_message="Shutter permit revoked.",
            )
        )
    # Install databroker connection
    if connect_databroker:
        RE.subscribe(save_data)
    # Add preprocessors
    RE.preprocessors.append(inject_haven_md_wrapper)
    return RE
