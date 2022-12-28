from typing import Union, Sequence, Callable

from bluesky.preprocessors import baseline_wrapper as bluesky_baseline_wrapper
from bluesky.utils import make_decorator

from .instrument.instrument_registry import registry


def baseline_wrapper(plan, devices: Union[Sequence, str], name: str="baseline"):
    bluesky_baseline_wrapper.__doc__
    # Resolve devices
    devices = registry.findall(devices)
    print(devices)
    yield from bluesky_baseline_wrapper(plan=plan, devices=devices, name=name)


baseline_decorator = make_decorator(baseline_wrapper)
