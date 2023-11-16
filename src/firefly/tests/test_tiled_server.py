"""Tests to check that the simulated tiled client works properly."""

import numpy
import pytest
from tiled.adapters.array import ArrayAdapter
from tiled.adapters.mapping import MapAdapter
from tiled.client import Context, from_context
from tiled.server.app import build_app

simple_tree = MapAdapter(
    {
        "a": ArrayAdapter.from_array(
            numpy.arange(10), metadata={"apple": "red", "animal": "dog"}
        ),
        "b": ArrayAdapter.from_array(
            numpy.arange(10), metadata={"banana": "yellow", "animal": "dog"}
        ),
        "c": ArrayAdapter.from_array(
            numpy.arange(10), metadata={"cantalope": "orange", "animal": "cat"}
        ),
    }
)


@pytest.fixture(scope="module")
def client():
    app = build_app(simple_tree)
    with Context.from_app(app) as context:
        client = from_context(context)
        yield client


def test_client_fixture(client):
    """Does the client fixture load without stalling the test runner?"""
