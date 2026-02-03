import pytest

from haven import TiledWriter, tiled_writer


def test_load_tiled_writer(mocker):
    from_profile = mocker.MagicMock()
    mocker.patch("haven._tiled_writer.from_profile", new=from_profile)
    config = {
        "writer_profile": "spam",
        "writer_batch_size": 50,
        "writer_backup_directory": "/tmp/",
    }
    writer = tiled_writer(config)
    from_profile.assert_called_once_with("spam", structure_clients="numpy")
    assert writer._batch_size == 50
    assert writer.backup_directory == "/tmp/"


@pytest.mark.skip(reason="need a new way to put custom Spec into the writer")
def test_xas_spec(mocker):
    """Does the XASRun spec get added for valid XAS runs?"""
    client = mocker.MagicMock()
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


@pytest.mark.skip(reason="need a new way to put custom Spec into the writer")
def test_no_xas_spec(mocker):
    """Does the XASRun spec get skipped for invalid XAS runs?"""
    client = mocker.MagicMock()
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
