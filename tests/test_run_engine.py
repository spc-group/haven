import gc

import databroker
from bluesky import RunEngine

from haven.instrument.aps import load_aps
from haven import run_engine


def test_subscribers_garbage_collection(monkeypatch):
    """Tests for regression of a bug in databroker.

    Since databroker uses a weak reference to the insert function, it
    can be subject to garbage collection and no longer able to save
    data.

    """
    monkeypatch.setattr(databroker, "catalog", {"bluesky": databroker.temp()})
    load_aps()
    RE = run_engine()
    assert len(RE.dispatcher.cb_registry.callbacks) == 12
    gc.collect()
    assert len(RE.dispatcher.cb_registry.callbacks) == 12


def test_run_engine_preprocessors():
    load_aps()
    RE = run_engine()
    assert len(RE.preprocessors) > 0


def test_run_engine_created():
    load_aps()
    RE = run_engine()
    assert isinstance(RE, RunEngine)


