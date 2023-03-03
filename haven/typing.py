from typing import Union, Sequence

from ophyd import Device, Component, Signal


Detector = Union[Device, Component, Signal, str]


DetectorList = Union[str, Sequence[Detector]]


Motor = Union[Device, Component, Signal, str]
