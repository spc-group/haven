import threading

import databroker
import sqlite3
from tiled.client import from_uri
from tiled.client.cache import Cache

from ._iconfig import load_config


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
    def __init__(self, *args, **kwargs, ):
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
    

    


def tiled_client(entry_node=None, uri=None):
    config = load_config()
    if uri is None:
        uri = config["database"]["tiled"]["uri"]
    client_ = from_uri(uri, "dask", cache=ThreadSafeCache())
    if entry_node is None:
        entry_node = config["database"]["tiled"]["entry_node"]
    client_ = client_[entry_node]
    return client_


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
