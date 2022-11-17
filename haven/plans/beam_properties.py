from collections import namedtuple

import matplotlib.pyplot as plt
import numpy as np
from lmfit.models import StepModel


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
