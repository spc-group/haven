import asyncio
import logging
import os
import sqlite3
import threading
import warnings
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Sequence

import databroker
import numpy as np
from tiled.client import from_uri
from tiled.client.cache import Cache

from ._iconfig import load_config

log = logging.getLogger(__name__)


def unsnake(arr: np.ndarray, snaking: list) -> np.ndarray:
    """Unsnake a nump array.

    For each axis in *arr*, there should be a corresponding True/False
    in *snaking* whether that axis should have alternating rows. The
    first entry is ignored as it doesn't make sense to snake the first
    axis.

    Returns
    =======
    unsnaked
      A copy of *arr* with the odd-numbered axes flipped (if indicated
      by *snaking*).

    """
    # arr = np.copy(arr)
    # Create some slice object for easier manipulation
    full_axis = slice(None)
    alternating = slice(None, None, 2)
    flipped = slice(None, None, -1)
    # Flip each axis if necessary (skipping the first axis)
    for axis, is_snaked in enumerate(snaking[1:]):
        if not is_snaked:
            continue
        slices = (full_axis,) * axis
        slices += (alternating,)
        arr[slices] = arr[slices + (flipped,)]
    return arr


def load_catalog(name: str = "bluesky"):
    """Load a databroker catalog for retrieving data.

    To retrieve individual scans, consider the ``load_result`` and
    ``load_data`` methods.

    Parameters
    ==========
    name
      The name of the catalog as defined in the Intake file
      (e.g. ~/.local/share/intake/catalogs.yml)

    Returns
    =======
    catalog
      The databroker catalog.
    """
    return databroker.catalog[name]


def load_result(uid: str, catalog_name: str = "bluesky", stream: str = "primary"):
    """Load a past experiment from the database.

    The result contains metadata and scan parameters. The data
    themselves are accessible from the result's *read()* method.

    Parameters
    ==========
    uid
      The universal identifier for this scan, as return by a bluesky
      RunEngine.
    catalog_name
      The name of the catalog as defined in the Intake file
      (e.g. ~/.local/share/intake/catalogs.yml)
    stream
      The data stream defined by the bluesky RunEngine.

    Returns
    =======
    result
      The experiment result, with data available via the *read()*
      method.

    """
    cat = load_catalog(name=catalog_name)
    result = cat[uid][stream]
    return result


def load_data(uid, catalog_name="bluesky", stream="primary"):
    """Load a past experiment's data from the database.

    The result is an xarray with the data collected.

    Parameters
    ==========
    uid
      The universal identifier for this scan, as return by a bluesky
      RunEngine.
    catalog_name
      The name of the catalog as defined in the Intake file
      (e.g. ~/.local/share/intake/catalogs.yml)
    stream
      The data stream defined by the bluesky RunEngine.

    Returns
    =======
    data
      The experimental data, as an xarray.

    """

    res = load_result(uid=uid, catalog_name=catalog_name, stream=stream)
    data = res.read()
    return data


def with_thread_lock(fn):
    """Makes sure the function isn't accessed concurrently."""

    def wrapper(obj, *args, **kwargs):
        obj._lock.acquire()
        try:
            fn(obj, *args, **kwargs)
        finally:
            obj._lock.release()

    return wrapper


class ThreadSafeCache(Cache):
    """Equivalent to the regular cache, but thread-safe.

    Ensures that sqlite3 is built with concurrency features, and
    ensures that no two write operations happen concurrently.

    """

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._lock = threading.Lock()

    def write_safe(self):
        """
        Check that it is safe to write.

        SQLite is not threadsafe for concurrent _writes_.
        """
        is_main_thread = threading.current_thread().ident == self._owner_thread
        sqlite_is_safe = sqlite3.threadsafety == 1
        return is_main_thread or sqlite_is_safe

    # Wrap the accessor methods so they wait for the lock
    clear = with_thread_lock(Cache.clear)
    set = with_thread_lock(Cache.set)
    get = with_thread_lock(Cache.get)
    delete = with_thread_lock(Cache.delete)


def tiled_client(
    entry_node=None, uri=None, cache_filepath=None, structure_clients="numpy"
):
    config = load_config()
    tiled_config = config["database"].get("tiled", {})
    # Create a cache for saving local copies
    if cache_filepath is None:
        cache_filepath = tiled_config.get("cache_filepath", "")
    if os.access(cache_filepath, os.W_OK):
        cache = ThreadSafeCache(filepath=cache_filepath)
    else:
        warnings.warn(f"Cache file is not writable: {cache_filepath}")
        cache = None
    # Create the client
    if uri is None:
        uri = tiled_config["uri"]
    api_key = tiled_config.get("api_key")
    client_ = from_uri(uri, structure_clients, api_key=api_key)
    if entry_node is None:
        entry_node = tiled_config["entry_node"]
    client_ = client_[entry_node]
    return client_


class CatalogScan:
    """A single scan from the tiled API with some convenience methods.

    Parameters
    ==========
      A tiled container on which to operate.
    """

    def __init__(self, container, executor=None):
        self.container = container
        self.executor = executor

    def _read_data(
        self, signals: Sequence | None, dataset: str = "primary/internal/events"
    ):
        data = self.container[dataset]
        if signals is None:
            return data.read()
        # Remove duplicates and missing signals
        signals = set(signals)
        available_signals = set(data.columns)
        signals = signals & available_signals
        return data.read()

    def _read_metadata(self, keys=None):
        container = self.container
        if keys is not None:
            container = container[keys]
        return container.metadata

    @property
    def uid(self):
        return self.container._item["id"]

    async def run(self, to_call, *args):
        """Run the given syncronous callable in an asynchronous context."""
        return await self.loop.run_in_executor(self.executor, to_call, *args)

    async def export(self, filename: str, format: str):
        target = partial(self.container.export, filename, format=format)
        await self.loop.run_in_executor(None, target)

    def formats(self):
        return self.container.formats

    async def data(self, signals=None, stream="primary"):
        return await self.loop.run_in_executor(
            None, self._read_data, signals, f"{stream}/internal/events/"
        )

    @property
    def loop(self):
        return asyncio.get_running_loop()

    def _data_keys(self, stream):
        return self.container[stream]["internal/events"].columns

    async def data_keys(self, stream="primary"):
        return await self.run(self._data_keys, ("primary",))

    async def hints(self):
        """Retrieve the data hints for this scan.

        Returns
        =======
        independent
          The hints for the independent scanning axis.
        dependent
          The hints for the dependent scanning axis.
        """
        metadata = await self.metadata
        # Get hints for the independent (X)
        try:
            independent = metadata["start"]["hints"]["dimensions"][0][0]
        except (KeyError, IndexError):
            warnings.warn("Could not get independent hints")
        # Get hints for the dependent (X)
        dependent = []
        primary_metadata = await self.run(self._read_metadata, "primary")
        hints = primary_metadata["hints"]
        for device, dev_hints in hints.items():
            dependent.extend(dev_hints["fields"])
        return independent, dependent

    @property
    async def metadata(self):
        metadata = await self.run(self._read_metadata)
        return metadata

    async def __getitem__(self, signal):
        """Retrieve a signal from the dataset, with reshaping etc."""
        arr = await self.run(self._read_data, tuple([signal]))
        arr = np.asarray(arr[signal])
        # Re-shape to match the scan dimensions
        metadata = await self.metadata
        try:
            shape = metadata["start"]["shape"]
        except KeyError:
            log.warning(f"No shape found for {repr(signal)}.")
        else:
            arr = np.reshape(arr, shape)
        # Flip alternating rows if snaking is enabled
        if "snaking" in metadata["start"]:
            arr = unsnake(arr, metadata["start"]["snaking"])
        return arr


class Catalog:
    """An asynchronous wrapper around the tiled client.

    This class has a more intelligent understanding of how *our* data
    are structured, so can make some assumptions and takes care of
    boiler-plate code (e.g. reshaping maps, etc).

    """

    _client = None

    def __init__(self, client=None):
        self._client = client
        self.executor = ThreadPoolExecutor()

    def __del__(self):
        self.executor.shutdown(wait=True, cancel_futures=True)

    async def run(self, to_call, *args):
        """Run the given syncronous callable in an asynchronous context."""
        return await self.loop.run_in_executor(self.executor, to_call, *args)

    @property
    def loop(self):
        return asyncio.get_running_loop()

    @property
    async def client(self):
        if self._client is None:
            self._client = await self.run(tiled_client)
        return self._client

    async def __getitem__(self, uid) -> CatalogScan:
        client = await self.client
        container = await self.run(client.__getitem__, uid)
        scan = CatalogScan(container=container, executor=self.executor)
        return scan

    async def items(self):
        client = await self.client
        for key, value in await self.run(client.items):
            yield key, CatalogScan(container=value, executor=self.executor)

    async def values(self):
        client = await self.client
        containers = await self.run(client.values)
        for container in containers:
            yield CatalogScan(container, executor=self.executor)

    async def __len__(self):
        client = await self.client
        length = await self.run(client.__len__)
        return length

    async def search(self, query):
        """
        Make a Node with a subset of this Node's entries, filtered by query.

        Examples
        --------

        >>> from tiled.queries import FullText
        >>> await tree.search(FullText("hello"))
        """
        loop = asyncio.get_running_loop()
        client = await self.client
        return Catalog(await loop.run_in_executor(self.executor, client.search, query))

    async def distinct(
        self, *metadata_keys, structure_families=False, specs=False, counts=False
    ):
        """Get the unique values and optionally counts of metadata_keys,
        structure_families, and specs in this Node's entries

        Examples
        --------

        Query all the distinct values of a key.

        >>> await catalog.distinct("foo", counts=True)

        Query for multiple keys at once.

        >>> await catalog.distinct("foo", "bar", counts=True)

        """
        loop = asyncio.get_running_loop()
        client = await self.client
        query = partial(
            client.distinct,
            *metadata_keys,
            structure_families=structure_families,
            specs=specs,
            counts=counts,
        )
        return await loop.run_in_executor(self.executor, query)


# Create a default catalog for basic usage
catalog = Catalog()


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2023, UChicago Argonne, LLC
#
# Distributed under the terms of the 3-Clause BSD License
#
# The full license is in the file LICENSE, distributed with this software.
#
# DISCLAIMER
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# -----------------------------------------------------------------------------
