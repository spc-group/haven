from collections import namedtuple
from typing import Mapping

import matplotlib.pyplot as plt
import numpy as np
from lmfit.models import StepModel
from bluesky.preprocessors import subs_decorator
from bluesky import plans as bp

from ..instrument.instrument_registry import registry


def knife_scan(knife_motor, start: float, end: float, num: int,
               I0="I0", It="It", relative: bool = False, md: Mapping = {}):
    """Plan to scan over a knife placed in the beam to measure its height.

    Parameters
    ==========
    knife_motor
      An ophyd device or name of a registered device that has a well
      defined edge attached to it.
    start
      Motor position at which to start scanning.
    end
      Motor position at which to finish scanning.
    num
      How many points to measure between *start* and *end*.
    I0
      Device or name of a registered ion chamber upstream from the
      knife.
    It
      Device or name of a registered ion chamber downstream from the
      knife.
    relative
      If true, *start* and *end* will be interpreted as relative to
      the current motor position.
    md
      Extra metadata to pass into the run engine.
    
    """
    md_ = dict(plan_name="knife_scan", **md)
    I0 = registry.find(I0)
    It = registry.find(It)
    knife_motor = registry.find(knife_motor)
    # Check for relative or absolute scan
    if relative:
        plan_func = bp.rel_scan
    else:
        plan_func = bp.scan
    # Compute the plan
    yield from plan_func([I0, It], knife_motor, start, end, num=num, md=md_)


def fit_step(x, y, plot=False):
    """Extract beam properties from a step scan over the beam profile.

    Parameters
    ==========
    x
      Array of motor positions.
    y
      Array of measured values at each motor position
      (e.g. transmitted intensity).
    plot
      If true, plot the fitting results.

    Returns
    =======
    properties
      A named tuple with the *size* and *position* of the beam, in
      units of *x*.

    """
    # Normalize data to start at zero
    y -= y[0]
    # Set up initial fitting parameters
    model = StepModel(form="erf")
    params = model.guess(y, x)
    half_max = (np.min(y) + np.max(y)) / 2
    center_idx = np.argmin(np.abs(y-half_max))
    center_guess = x[center_idx]
    params['center'].set(center_guess)
    # Invert the amplitude if we started with full transmission
    is_inverted = np.mean(y) < 0
    if is_inverted:
        params['amplitude'].set(-params['amplitude'].value)
    # Fit the model to the data
    result = model.fit(y, params=params, x=x)
    beam_position = result.values['center']
    # Plot results
    if plot:
        plt.figure()
        result.plot(show_init=True, datafmt="x", xlabel="Knife position /µm", ylabel="Relative transmission")
        plt.axvline(beam_position, color="C4", ls=":", label="Beam position")
        plt.axhline(half_max, color="C4", ls=":")
        plt.text(beam_position, half_max, s=f"{beam_position:.2f}", color="C4")
        plt.legend()
    # Prepare results object
    Properties = namedtuple("Properties", ["position"])
    properties = Properties(position=beam_position)
    return properties
