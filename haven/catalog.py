import databroker


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
