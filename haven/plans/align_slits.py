"""A bluesky plan to scan the X-ray beam slits and then move the slits
to that position.

"""

import numpy as np
import lmfit
from bluesky import plans as bp, plan_stubs as bps
from bluesky.preprocessors import subs_decorator
from bluesky.callbacks import LiveFit


__all__ = ["align_slits"]


def align_slit_scan(slit_motor, ion_chamber):
    yield from bp.rel_scan([ion_chamber], slit_motor, -1, 1, 50)


def align_slits(slit_motors=[], ion_chamber=None):
    """Scan a range of values for the slit motor, and position the motor in the center."""
    for motor in slit_motors:
        # Set up the live fit object to process the results
        def gaussian(x, A, sigma, x0):
            return A * np.exp(-((x - x0) ** 2) / (2 * sigma**2))

        model = lmfit.Model(gaussian)
        init_guess = {"A": 2, "sigma": lmfit.Parameter("sigma", 3, min=0), "x0": -0.2}
        fit = LiveFit(model, ion_chamber.name, {"x": motor.name}, init_guess)
        scan = subs_decorator(fit)(align_slit_scan)
        # Execute the scan
        yield from scan(ion_chamber=ion_chamber, slit_motor=motor)
        # Move the slit motor to the center of the Gaussian peak
        new_center = fit.result.values["x0"]
        yield from bps.mv(motor, new_center)
