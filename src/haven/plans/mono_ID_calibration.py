from typing import Sequence, Optional
import warnings
import logging

from bluesky.callbacks.best_effort import BestEffortCallback
from bluesky import plan_stubs as bps
import pandas as pd
from lmfit.model import Model
from lmfit.models import QuadraticModel

from haven.typing import Motor
from ..instrument.instrument_registry import registry
from .set_energy import set_energy
from .align_motor import align_pitch2, align_motor


__all__ = ["mono_ID_calibration"]


log = logging.getLogger(__name__)


def mono_ID_calibration(
    energies: Sequence,
    mono_motor: Motor = "energy_mono_energy",
    id_motor: Motor = "energy_id_energy",
    energy_motor: Motor = "energy",
    detector="I0",
    fit_model: Optional[Model] = None,
):
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
    energy_motor
      The motor to move when initially setting the energy for each
      point.
    detector
      The detector to measure.
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
        # Set the mono and ID to the target energy to get started
        yield from set_energy(energy, positioners=[energy_motor])
        # Align the pitch motor
        yield from align_pitch2(detector=detector)
        # Determine maximum mono energy
        bec = BestEffortCallback()
        bec.disable_plots()
        bec.disable_table()
        detector_ = registry.find(detector)
        yield from align_motor(
            motor=id_motor, detector=detector_, distance=0.4, bec=bec
        )
        # Save the results to the dataframe for fitting later
        peak_center = bec.peaks["cen"]
        signal_name = getattr(detector_, "raw_counts", detector_).name
        try:
            mono_energy = mono_motor.user_readback.get()
        except AttributeError:
            mono_energy = mono_motor.readback.get()
        if signal_name in peak_center.keys():
            # results_df = results_df.append(
            new_row = {
                "id_energy": bec.peaks["cen"][signal_name],
                "mono_energy": mono_energy,
            }
            results_df = pd.concat(
                [results_df, pd.DataFrame([new_row])], ignore_index=True
            )
        print(results_df)
    # Fit the overall mono-ID calibration curve
    if fit_model is None:
        fit_model = QuadraticModel(nan_policy="omit")
    y = results_df.id_energy
    x = results_df.mono_energy
    params = fit_model.guess(y, x=x)
    try:
        fit = fit_model.fit(y, params, x=x)
    except Exception as e:
        log.warning(str(e))
        warnings.warn(str(e))
        print(fit_model, results_df)
    else:
        fit_model.fit_result = fit
        print(fit_model, fit, results_df)
    fit_model.results_df = results_df
