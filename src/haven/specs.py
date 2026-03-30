from typing import Literal

import numpy as np
import numpy.typing as npt
from pydantic import Field
from pydantic.dataclasses import dataclass
from scanspec.core import Axis, Dimension, StrictConfig
from scanspec.specs import Line, Spec

from .energy_ranges import energy_to_wavenumber, wavenumber_to_energy


@dataclass(config=StrictConfig)
class EnergyRegion(Line[Axis]):
    """A region that is linear in energy, relative to a fixed offset *E0*."""

    E0: float = Field(
        default=0.0, description="Reference energy point for this region."
    )

    def _line_from_indexes(
        self, indexes: npt.NDArray[np.float64]
    ) -> dict[Axis, npt.NDArray[np.float64]]:
        line = super()._line_from_indexes(indexes)
        line = {ax: vals + self.E0 for ax, vals in line.items()}
        return line


@dataclass(config=StrictConfig)
class WavenumberRegion(Line[Axis]):
    """A region that is linear in wavenumber (A), but produces points in
    energy (eV).

    """

    E0: float = Field(
        default=0.0, description="Reference energy point for this region."
    )

    def _line_from_indexes(
        self, indexes: npt.NDArray[np.float64]
    ) -> dict[Axis, npt.NDArray[np.float64]]:
        line = super()._line_from_indexes(indexes)
        line = {ax: wavenumber_to_energy(vals) + self.E0 for ax, vals in line.items()}
        return line


@dataclass(config=StrictConfig)
class KWeighted(Spec[Axis]):
    """Apply a duration that scales with the wavenember.

    *base_duration* is applied to all points, and is scaled by
    `K**k_weight`.

    """

    base_duration: float = Field(description="Time when scan point == E0")
    E0: float = Field(
        default=0.0, description="Reference energy point for this region."
    )
    k_weight: float = Field(
        default=0.0,
        description="Weight to apply as a function of k to the base duration.",
    )
    spec: Spec[Axis] | None = Field(
        description="Spec contaning the path to be followed", default=None
    )

    def axes(self) -> list[Axis]:  # noqa: D102
        if self.spec:
            return self.spec.axes()
        else:
            return []

    def duration(self) -> float | None | Literal["VARIABLE_DURATION"]:  # noqa: D102
        if self.spec and self.spec.duration() is not None:
            raise ValueError(f"{self.spec} already defines a duration")
        elif self.k_weight == 0:
            return self.base_duration
        else:
            return "VARIABLE_DURATION"

    def calculate(  # noqa: D102
        self, bounds: bool = False, nested: bool = False
    ) -> list[Dimension[Axis]]:
        if self.spec:
            dimensions = self.spec.calculate(bounds=bounds)
            base_durations = np.full(
                len(dimensions[-1].gap),
                self.base_duration,
            )
            Es = next(iter(dimensions[-1].midpoints.values()))
            # Apply any k-dependence to the duration
            if self.k_weight == 0:
                dimensions[-1].duration = base_durations
            elif np.any(Es < self.E0):
                raise ValueError(
                    f"Cannot apply k-weight to energies below E0 {self.E0}."
                )
            else:
                ks = energy_to_wavenumber(Es - self.E0)
                dimensions[-1].duration = base_durations * ks**self.k_weight
            return dimensions
        else:
            # Had to do it like this otherwise it will complain about typing
            empty_dim: Dimension[Axis] = Dimension(
                {},
                {},
                {},
                None,
                duration=np.full(1, self.constant_duration),
            )
            return [empty_dim]
