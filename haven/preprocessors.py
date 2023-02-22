"""Tools for modifying plans and data streams as they are generated."""


from typing import Union, Sequence, Callable
from collections import ChainMap
import pkg_resources

from bluesky.preprocessors import baseline_wrapper as bluesky_baseline_wrapper
from bluesky.utils import make_decorator
from bluesky.preprocessors import msg_mutator
import epics


from .instrument.instrument_registry import registry


def baseline_wrapper(plan, devices: Union[Sequence, str]=["motors", "power_supplies", "xray_sources", "APS"], name: str="baseline"):
    bluesky_baseline_wrapper.__doc__
    # Resolve devices
    devices = registry.findall(devices, allow_none=True)
    yield from bluesky_baseline_wrapper(plan=plan, devices=devices, name=name)


def get_version(pkg_name):
    return pkg_resources.get_distribution(pkg_name).version


VERSIONS = dict(
    apstools = get_version('apstools'),
    bluesky = get_version('bluesky'),
    databroker = get_version('databroker'),
    epics_ca = epics.__version__,
    epics = epics.__version__,
    haven = get_version('haven'),
    h5py = get_version('h5py'),
    matplotlib = get_version('matplotlib'),
    numpy = get_version('numpy'),
    ophyd = get_version('ophyd'),
    pymongo = get_version("pymongo"),
)


def inject_haven_md_wrapper(plan):
    """
    Inject additional metadata into a run.
    This takes precedences over the original metadata dict in the event of
    overlapping keys, but it does not mutate the original metadata dict.
    (It uses ChainMap.)

    Parameters
    ----------
    plan : iterable or iterator
        a generator, list, or similar containing `Msg` objects
    """
    def _inject_md(msg):
        md = {"versions": VERSIONS}
        if msg.command == 'open_run':
            msg = msg._replace(kwargs=ChainMap(md, msg.kwargs))
        return msg

    return (yield from msg_mutator(plan, _inject_md))  


baseline_decorator = make_decorator(baseline_wrapper)
