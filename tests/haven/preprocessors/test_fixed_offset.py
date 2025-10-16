from pathlib import Path
from unittest import mock

import pandas as pd
import pytest
from bluesky import Msg
from bluesky.utils import ensure_generator

from haven.devices import AxilonMonochromator, ChannelCutMonochromator
from haven.preprocessors import fixed_offset_wrapper
from haven.preprocessors.fixed_offset import beam_offset
from haven.units import ureg

# Load calculated data from Aleks
df_parameters = pd.read_excel(
    "tests/haven/preprocessors/fixed_offset_calculations.xlsx",
    nrows=8,
    usecols=[2, 3, 4],
    index_col=0,
    skiprows=1,
)
df_parameters = df_parameters.T
df = pd.read_excel(
    Path(__file__).parent / "fixed_offset_calculations.xlsx", skiprows=12
)
df = df.rename(
    columns={
        "Energy eV": "energy",
        "Energy nm": "wavelength",
        "Bragg Angle rad": "primary_bragg_angle",
        "Offset (um)": "primary_beam_offset",
        "Bragg Angle rad.1": "secondary_bragg_angle",
        "Offset (um).1": "secondary_beam_offset",
    }
)


@pytest.fixture()
async def primary_mono():
    mono = AxilonMonochromator(prefix="", name="primary_mono")
    await mono.connect(mock=True)
    return mono


@pytest.fixture()
async def secondary_mono():
    mono = ChannelCutMonochromator(
        prefix="", name="secondary_mono", vertical_motor="255idzVME:m1"
    )
    await mono.connect(mock=True)
    return mono


def units_tasks(description):
    task = mock.MagicMock()
    task.exception.return_value = None
    task.result.return_value = description
    return [task]


def test_beam_offset():
    # Taken from a working configuration at 25-ID-C
    bragg = 67407.927958 * ureg.arcseconds - 2159.15 * ureg.arcseconds
    gap = 4000 * ureg.microns
    offset = 7603.055409 * ureg.microns
    assert beam_offset(bragg, gap=gap).magnitude == pytest.approx(offset.magnitude)


@pytest.mark.parametrize("idx, row", df.iloc[1::10].iterrows())
def test_bragg_tracking(primary_mono, secondary_mono, idx, row):
    row0 = df.iloc[0]
    bragg = row["secondary_bragg_angle"]
    input_plan = ensure_generator(
        [
            Msg("set", secondary_mono.bragg, bragg, group="set-43367a", run=None),
            Msg("wait", group="set-43367a", run=None),
        ]
    )
    wrapped = fixed_offset_wrapper(input_plan, primary_mono, secondary_mono)
    msg = next(wrapped)  # Prime the generative coroutine
    primary_beam_offset = row0["primary_beam_offset"]
    secondary_beam_offset = row0["secondary_beam_offset"]
    d_spacing = df_parameters["Si(220) D Spacing:"].iloc[0]
    gap = df_parameters["Si(220) Gap"].iloc[0]
    bragg_offset = df_parameters["Si(220) Bragg Offset:"].iloc[0]
    wrapped.send(units_tasks({"secondary_mono-bragg": {"units": "radian"}}))
    wrapped.send(units_tasks({"secondary_mono-energy": {"units": "eV"}}))
    wrapped.send({"readback": primary_beam_offset})
    wrapped.send(units_tasks({"primary_mono-beam_offset": {"units": "microns"}}))
    wrapped.send({secondary_mono.beam_offset.name: {"value": secondary_beam_offset}})
    wrapped.send(units_tasks({"secondary_mono-beam_offset": {"units": "microns"}}))
    wrapped.send({"readback": bragg_offset})
    wrapped.send(units_tasks({"secondary_mono-bragg_offset": {"units": "arcsec"}}))
    wrapped.send({"readback": gap})
    wrapped.send(units_tasks({"secondary_mono-gap": {"units": "mm"}}))
    wrapped.send({"readback": d_spacing})
    new_msg = wrapped.send(units_tasks({"secondary_mono-d_spacing": {"units": "nm"}}))
    assert new_msg.args[0] == pytest.approx(row["primary_beam_offset"])
    other_msgs = list(wrapped)
    assert len(other_msgs) == 2


@pytest.mark.parametrize("idx, row", df.iloc[1::10].iterrows())
def test_energy_tracking(primary_mono, secondary_mono, idx, row):
    # E = hc/2/d/sin(θ)
    #
    # F = 12398.42
    # B = 1.92
    #
    # F/2/B/sin((A+D)/R2S)
    row0 = df.iloc[0]
    energy = row["energy"]
    input_plan = ensure_generator(
        [
            Msg("set", secondary_mono.energy, energy, group="set-43367a", run=None),
            Msg("wait", group="set-43367a", run=None),
        ]
    )
    wrapped = fixed_offset_wrapper(input_plan, primary_mono, secondary_mono)
    msg = next(wrapped)  # Prime the generative coroutine
    primary_beam_offset = row0["primary_beam_offset"]
    secondary_beam_offset = row0["secondary_beam_offset"]
    d_spacing = df_parameters["Si(220) D Spacing:"].iloc[0]
    gap = df_parameters["Si(220) Gap"].iloc[0]
    bragg_offset = df_parameters["Si(220) Bragg Offset:"].iloc[0]
    wrapped.send(units_tasks({"secondary_mono-bragg": {"units": "radian"}}))
    wrapped.send(units_tasks({"secondary_mono-energy": {"units": "eV"}}))
    wrapped.send({"readback": primary_beam_offset})
    wrapped.send(units_tasks({"primary_mono-beam_offset": {"units": "microns"}}))
    wrapped.send({secondary_mono.beam_offset.name: {"value": secondary_beam_offset}})
    wrapped.send(units_tasks({"secondary_mono-beam_offset": {"units": "microns"}}))
    wrapped.send({"readback": bragg_offset})
    wrapped.send(units_tasks({"secondary_mono-bragg_offset": {"units": "arcsec"}}))
    wrapped.send({"readback": gap})
    wrapped.send(units_tasks({"secondary_mono-gap": {"units": "mm"}}))
    wrapped.send({"readback": d_spacing})
    new_msg = wrapped.send(units_tasks({"secondary_mono-d_spacing": {"units": "nm"}}))
    assert new_msg.args[0] == pytest.approx(row["primary_beam_offset"])
    other_msgs = list(wrapped)
    assert len(other_msgs) == 2
