from typing import Sequence, Union

from ophyd import Component, Device, Signal

Detector = Union[Device, Component, Signal, str]


DetectorList = Union[str, Sequence[Detector]]


Motor = Union[Device, Component, Signal, str]
