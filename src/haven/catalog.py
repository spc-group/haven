import asyncio
import functools
import logging
import warnings
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path
from typing import Mapping
from urllib.parse import quote_plus

import httpx
import pandas as pd
import numpy as np
from tiled.client import from_profile
from tiled.client.base import BaseClient
from tiled.client.cache import Cache
from tiled.client.container import _queries_to_params
from tiled.queries import NoBool

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


def with_thread_lock(fn):
    """Makes sure the function isn't accessed concurrently."""

    def wrapper(obj, *args, **kwargs):
        obj._lock.acquire()
        try:
            fn(obj, *args, **kwargs)
        finally:
            obj._lock.release()

    return wrapper


class DEFAULT:
    pass


def tiled_client(
    catalog: str | type[DEFAULT] | None = DEFAULT,
    profile: str = "haven",
    cache_filepath: Path | type[DEFAULT] | None = DEFAULT,
    structure_clients: str = "numpy",
) -> BaseClient:
    """Load a Tiled client with some default options.

    Parameters
    ==========
    catalog
      If not None, load a specific catalog within the client. By
      default, the iconfig.toml file will be consulted for the value
      of ``tiled.default_catalog``.
    profile
      Use a specific Tiled profile. If not provided, the default Tiled
      profile will be used.
    cache_filepath
      The path on which to store a cache of downloaded data. If
      omitted, the iconfig.toml file will be consulted for the value
      of ``tiled.cache_filepath``.

    """
    # Get default values from the database
    tiled_config = load_config()["tiled"]
    if cache_filepath is DEFAULT:
        cache_filepath = tiled_config.get("cache_filepath")
    if catalog is DEFAULT:
        catalog = tiled_config.get("default_catalog")
    # Create the client
    kw = {}
    if cache_filepath is not None:
        kw["cache"] = Cache(cache_filepath)
    client = from_profile(profile, structure_clients=structure_clients, **kw)
    if catalog is not None:
        client = client[catalog]
    return client


async def _search(path: str, client: httpx.AsyncClient, params: dict = {}):
        """Find scans in the catalog matching the given criteria.

        This is a batched iterator that will fetch the next batch of
        scans once the first set have been exhausted.

        """
        # Build query parameters
        next_url = "/".join(["search", quote_plus(path)]).rstrip('/')
        # Get search results from API
        while next_url is not None:
            response = await client.get(
                next_url,
                params=params,
            )
            for run in response.json()['data']:
                yield run
            next_url = response.json()['links']['next']


class CatalogScan:
    """A single scan from the tiled API with some convenience methods.

    Parameters
    ==========
    path
      The catalog path in the API from which to fetch data.
    metadata
      Pre-fetched mapping of metadata. If `None` (default), new data
      will be fetched when needed.
    client
      An http client object to use for accessing the API. If `None`
      (default), a new client will be created.

    """

    def __init__(
        self,
        path: str,
        metadata: Mapping | None = None,
        client: httpx.AsyncClient | None = None,
    ):
        self.path = path
        self._client = client
        self._metadata = metadata

    @property
    def client(self):
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_uri)
        return self._client

    async def stream_names(self):
        streams = _search(path=self.path, client=self.client)
        names = [stream['id'] async for stream in streams]
        return names

    async def _read_data(self, signals: Sequence[str] | None, dataset: str):
        params = {}
        path = "/".join([self.path, dataset]).rstrip("/")
        url = f"table/full/{quote_plus(path)}"
        response = await self.client.get(url, params=params)
        df = pd.DataFrame(response.json())
        return df

    @property
    async def uid(self):
        return (await self.metadata)['start']['uid']

    async def export(self, filename: str, format: str):
        target = partial(self.container.export, filename, format=format)
        await self.loop.run_in_executor(None, target)

    def formats(self):
        return self.container.formats

    async def data(self, *, signals=None, stream: str = "primary"):
        return await self._read_data(signals, f"{stream}/internal/events/")

    async def external_dataset(self, name: str, stream: str = "primary") -> np.ndarray:
        """Load an external N-dimensional dataset from the database.

        Parameters
        ==========
        The key of the external dataset.

        Returns
        =======
        arr
          The loaded dataset.

        """
        return await self._read_data(None, f"{stream}/external/{name}")

    @property
    def loop(self):
        return asyncio.get_running_loop()

    async def data_keys(self, stream: str = "primary"):
        print(self.path, stream)
        metadata = await self._read_metadata(stream)
        data_keys = metadata.get("data_keys")
        return data_keys or {}

    async def hints(self, stream: str = "primary"):
        """Retrieve the data hints for this scan.

        Parameters
        ==========
        stream
          The name of the Tiled data stream to look up hints for.

        Returns
        =======
        independent
          The hints for the independent scanning axis.
        dependent
          The hints for the dependent scanning axis.

        """
        run_md, stream_md = await asyncio.gather(
            self._read_metadata(),
            self._read_metadata(path=stream),
        )
        # Get hints for the independent (X)
        try:
            dimensions = run_md["start"]["hints"]["dimensions"]
            independent = [
                sig for signals, strm in dimensions if strm == stream for sig in signals
            ]
        except (KeyError, IndexError):
            warnings.warn("Could not get independent hints")
            independent = []
        # Get hints for the dependent (Y) axes
        dependent = []
        hints = stream_md.get("hints", {})
        for device, dev_hints in hints.items():
            dependent.extend(dev_hints["fields"])
        return independent, dependent

    async def _read_metadata(self, path: str = ""):
        new_path = "/".join([self.path, path]).rstrip('/')
        response = await self.client.get(
            f"metadata/{quote_plus(new_path)}",
        )
        return response.json()["data"]["attributes"]["metadata"]

    @property
    async def metadata(self):
        return await self._read_metadata()

    async def __getitem__(self, signal, stream: str = "primary"):
        """Retrieve a signal from the dataset, with reshaping etc."""
        arr = await self._read_data(
            [f"{stream}/{signal}"], dataset=f"{stream}/internal/events"
        )
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
    """Asynchronously access Bluesky data in Tiled.

    This class has a more intelligent understanding of how *our* data
    are structured, so can make some assumptions and takes care of
    boiler-plate code (e.g. reshaping maps, etc).

    Parameters
    ==========
    path
      Where the data live in the Tiled server.
    host
      The address and port of the service hosting the Tiled
      API. Ignored if *client* is provided.
    client
      An asynchronous HTTP client used for API calls. This client
      should have *base_url* set. If omitted, a new client will be
      created.

    """

    _client: httpx.AsyncClient | None
    base_uri: str

    def __init__(self, path: str, host: str = "http://localhost:8000",client: httpx.AsyncClient | None = None):
        self.base_uri = f"{host.strip('/')}/api/v1/"
        self.path = path
        self._client = client

    @property
    def client(self):
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_uri)
        return self._client

    def __getitem__(self, uid) -> CatalogScan:
        # Check that the child exists in this container
        new_path = f"{self.path}/{uid}"
        # Create the child scan object
        scan = CatalogScan(path=new_path, client=self.client)
        return scan

    async def keys(self):
        async for run in self.runs():
            yield run['id']

    async def items(self):
        client = await self.client
        for key, value in await run_in_executor(client.items)():
            yield key, CatalogScan(container=value, executor=self.executor)

    async def values(self):
        client = await self.client
        containers = await run_in_executor(client.values)()
        for container in containers:
            yield CatalogScan(container, executor=self.executor)

    async def __len__(self):
        client = await self.client
        length = await run_in_executor(client.__len__)()
        return length

    def _search_params(self, queries: Sequence[NoBool] = (), sort: Sequence[str] = ()) -> dict:
        query_params = _queries_to_params(*queries)
        params = {
            **query_params
        }
        if len(sort) > 0:
            params['sort'] = sort
        return params

    async def runs(
        self,
        queries: Sequence[NoBool] = (),
        sort: Sequence[str] = (),
        batch_size: int = 100,
    ):
        """All the scans in the catalog matching the given criteria.

        This is a batched iterator that will fetch the next batch of
        scans once the first set have been exhausted.

        """
        # Build query parameters
        params = self._search_params(queries=queries, sort=sort)        
        # Get search results from API
        async for run in _search(path=self.path, params=params, client=self.client):
            md = run.get('attributes', {}).get('metadata')
            yield CatalogScan(path=f"{self.path}/{run['id']}", metadata=md, client=self.client)

    async def distinct(
            self, *metadata_keys, queries: Sequence[NoBool] = (), sort: Sequence[str] = ()
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
        params = self._search_params(queries=queries)
        response = await self.client.get(
            f"distinct/{self.path}",
            params=params,
        )
        return response.json()['metadata']


def from_profile(catalog: str = "scans", profile: str = "haven") -> Catalog:
    pass

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
