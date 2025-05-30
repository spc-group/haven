from unittest.mock import MagicMock

from haven import TiledWriter


def test_xas_spec():
    """Does the XASRun spec get added for valid XAS runs?"""
    client = MagicMock()
    client.include_data_sources.return_value = client
    writer = TiledWriter(client=client)
    start_doc = {
        "uid": "0",
        "d_spacing": 3.1415926,
        "edge": "Ni-K",
    }
    writer("start", start_doc)
    assert writer.client is client
    assert writer.client.create_container.called
    specs = client.create_container.call_args[1]["specs"]
    assert len(specs) == 2
    assert specs[0].name == "XASRun"
    assert specs[1].name == "BlueskyRun"


def test_no_xas_spec():
    """Does the XASRun spec get skipped for invalid XAS runs?"""
    client = MagicMock()
    client.include_data_sources.return_value = client
    writer = TiledWriter(client=client)
    start_doc = {
        "uid": "0",
    }
    writer("start", start_doc)
    assert client.create_container.called
    specs = client.create_container.call_args[1]["specs"]
    assert len(specs) == 1
    assert specs[0].name == "BlueskyRun"
