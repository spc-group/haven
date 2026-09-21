import logging
import re
from pathlib import Path
from uuid import uuid4

import httpx
import stamina
from bluesky_tiled_plugins import TiledWriter
from tiled.client import from_profile

from haven import exceptions
from haven.iconfig import TiledConfig

log = logging.getLogger()

xas_edge_regex = re.compile("^[A-Za-z]+[-_ ][K-Zk-z0-9]+$")


__all__ = ["tiled_writer", "TiledWriter"]


@stamina.retry(on=httpx.HTTPError, attempts=3)
def tiled_writer(config: TiledConfig) -> TiledWriter:
    """Load a tiled writer instance as specified in *config*."""
    profile = config.writer_profile
    try:
        client = from_profile(config.writer_profile, structure_clients="numpy")
    except httpx.ConnectError as exc:
        raise exceptions.TiledNotAvailable(profile) from exc
    client.include_data_sources()
    # Make sure the backup directory exists and is writable
    backup_directory = config.writer_backup_directory
    if backup_directory is not None:
        test_file = Path(backup_directory) / f"{uuid4()}.null"
        try:
            test_file.touch()
        finally:
            if test_file.exists():
                test_file.unlink()
    # Create the writer
    writer = TiledWriter(
        client,
        backup_directory=backup_directory,
        batch_size=config.writer_batch_size,
    )
    return writer
