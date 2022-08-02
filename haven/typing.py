from typing import Union, Sequence

from ophyd import Device, Component, Signal


Detector = Union[Device, Component, Signal]


DetectorList = Union[str, Sequence[Detector]]
