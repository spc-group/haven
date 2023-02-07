from typing import Sequence, Optional

from bluesky.callbacks.best_effort import BestEffortCallback
import pandas as pd
from lmfit.model import Model
from lmfit.models import QuadraticModel

from haven.typing import Motor
from ..instrument.instrument_registry import registry
from .set_energy import set_energy
from .align_motor import align_pitch2, align_motor


__all__ = ["mono_ID_calibration"]


def mono_ID_calibration(energies: Sequence, mono_motor: Motor="energy_mono_energy", id_motor: Motor = "energy_id_energy", fit_model: Optional[Model] = None):
    """A bluesky plan to measure the offset between monochromator and
    insertion device energies.

    This plan will print the results of the equation. The fit results
    will also be added to the *fit_model* object as
    `fit_model.result`.

    Pseudo-code:

    - for energy in *energies*
    
      - Move ID to *energy*
      - Align pitch motor
      - 1D scan over mono energy motor
      - Calculate mono energy motor position for maximum flux
    
    - Fit ID energy vs mono energy with function

    Parameters
    ==========
    energies
      The target energies, in eV, over which the calibration will be
      performed.
    mono_motor
      The motor to move for monochromator energy (will be scanned).
    id_motor
      The motor to move for the insertion device (will not be
      scanned).
    fit_model
      A lmfit model object that with determine the final fitting
      parameters for the calibration curve.

    """
    # Resolve device names
    mono_motor = registry.find(mono_motor)
    id_motor = registry.find(id_motor)
    results_df = pd.DataFrame(columns=["id_energy", "mono_energy"])
    # Do each energy point    
    for energy in energies:
        # Set the mono and ID to the target energy
        yield from set_energy(energy, positioners=[mono_motor, id_motor])
        # Align the pitch motor
        yield from align_pitch2()
        # Determine maximum mono energy
        bec = BestEffortCallback()
        bec.disable_plots()
        bec.disable_table()
        detector = registry.find("I0")
        yield from align_motor(motor=mono_motor, detector=detector)
        # Save the results to the dataframe for fitting later
        peak_center = bec.peaks["cen"]
        if detector.name in peak_center.keys():
            results_df.append({
                "id_energy": id_motor.readback.get(),
                "mono_energy": bec.peaks["cen"][detector.name],
            })
    # Fit the overall mono-ID calibration curve
    if fit_model is None:
        fit_model = QuadraticModel(nan_policy="omit")
    y = results_df.id_energy
    x = results_df.mono_energy
    params = fit_model.guess(y, x=x)
    fit = fit_model.fit(y, params, x=x)
    fit_model.fit_result = fit
    # Print the results of the fit
    print(fit)
