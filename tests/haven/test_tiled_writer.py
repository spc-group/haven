import pytest

from haven import tiled_writer
from haven.iconfig import TiledConfig


def test_load_tiled_writer(mocker, tmp_path):
    from_profile = mocker.MagicMock()
    mocker.patch("haven._tiled_writer.from_profile", new=from_profile)
    config = TiledConfig(
        writer_profile="spam",
        writer_batch_size=50,
        writer_backup_directory=str(tmp_path),
    )
    writer = tiled_writer(config)
    from_profile.assert_called_once_with("spam", structure_clients="numpy")
    assert writer._batch_size == 50
    assert writer.backup_directory == str(tmp_path)


def test_missing_backup_directory(mocker, tmp_path):
    from_profile = mocker.MagicMock()
    mocker.patch("haven._tiled_writer.from_profile", new=from_profile)
    config = TiledConfig(
        writer_profile="spam",
        writer_batch_size=50,
        writer_backup_directory=str(tmp_path / "missing"),
    )
    with pytest.raises(FileNotFoundError):
        writer = tiled_writer(config)
