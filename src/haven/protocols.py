"""Protocols for the various kinds of monos at our beamlines."""

from typing import Protocol

from bluesky.protocols import Movable, Readable


class EnergyDevice(Protocol):
    energy: Movable


class Monochromator(EnergyDevice):
    bragg: Movable
    beam_offset: Readable


class FixedOffsetMonochromator(Monochromator):
    beam_offset: Movable
