import copy
import logging
import re
from typing import NotRequired, Sequence, TypedDict

import httpx
import stamina
from bluesky.callbacks.tiled_writer import TiledWriter as BlueskyTiledWriter
from bluesky.callbacks.tiled_writer import _RunWriter as BlueskyRunWriter
from bluesky.utils import truncate_json_overflow
from event_model.documents import RunStart
from tiled.client import from_profile
from tiled.structures.core import Spec

from haven import exceptions

log = logging.getLogger()

xas_edge_regex = re.compile("^[A-Za-z]+[-_ ][K-Zk-z0-9]+$")


__all__ = ["tiled_writer", "TiledWriter"]


class TiledConfig(TypedDict):
    writer_profile: str
    writer_backup_directory: NotRequired[str]
    writer_batch_size: NotRequired[int]


@stamina.retry(on=httpx.HTTPError, attempts=3)
def tiled_writer(config: TiledConfig):
    """Load a tiled writer instance as specified in *config*.

    Looks for keys:
    -"""
    profile = config["writer_profile"]
    try:
        client = from_profile(config["writer_profile"], structure_clients="numpy")
    except httpx.ConnectError as exc:
        raise exceptions.TiledNotAvailable(profile) from exc
    client.include_data_sources()
    writer = TiledWriter(
        client,
        backup_directory=config.get("writer_backup_directory"),
        batch_size=config.get("writer_batch_size", 100),
    )
    return writer


def md_to_specs(start_doc: dict) -> Sequence[Spec]:
    """Determine which specs apply based on *start_doc*."""
    specs = [Spec("BlueskyRun", version="3.0")]
    # Check for XAS runs
    has_d_spacing = "d_spacing" in start_doc.keys()
    has_edge = xas_edge_regex.match(start_doc.get("edge", ""))
    if has_d_spacing and has_edge:
        specs.insert(0, Spec("XASRun", version="1.0"))
    else:
        log.info(f"Not adding XASRun spec: {has_d_spacing=}, {has_edge=}")
    return specs


class TiledWriter(BlueskyTiledWriter):
    def _factory(self, name, doc):
        return [_RunWriter(self.client)], []


class _RunWriter(BlueskyRunWriter):
    def start(self, doc: RunStart):
        doc = copy.copy(doc)
        self.access_tags = doc.pop("tiled_access_tags", None)  # type: ignore
        self.root_node = self.client.create_container(
            key=doc["uid"],
            metadata={"start": truncate_json_overflow(dict(doc))},
            specs=md_to_specs(doc),
            access_tags=self.access_tags,
        )
        self._streams_node = self.root_node.create_container(
            key="streams", access_tags=self.access_tags
        )
