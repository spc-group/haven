import logging
import re
from typing import Sequence

from bluesky.callbacks.tiled_writer import TiledWriter as BlueskyTiledWriter
from bluesky.callbacks.tiled_writer import _RunWriter as BlueskyRunWriter
from bluesky.utils import truncate_json_overflow
from event_model.documents import RunStart
from tiled.structures.core import Spec

log = logging.getLogger()

xas_edge_regex = re.compile("^[A-Za-z]+[-_ ][K-Zk-z0-9]+$")


__all__ = ["TiledWriter"]


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
        print(self.client)
        self.root_node = self.client.create_container(
            key=doc["uid"],
            metadata={"start": truncate_json_overflow(dict(doc))},
            specs=md_to_specs(doc),
        )
        self._streams_node = self.root_node.create_container(key="streams")
