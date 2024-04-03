import datetime as dt
import logging
from pathlib import Path

from bluesky import plan_stubs as bps
from bluesky.callbacks import LiveFit, best_effort, fitting, mpl_plotting
from bluesky.preprocessors import subs_decorator
from lmfit.models import StepModel
from matplotlib import pyplot as plt

from .._iconfig import load_config
from ..instrument.instrument_registry import registry
from .align_motor import align_pitch2
from .auto_gain import auto_gain
from .beam_properties import knife_scan
from .set_energy import set_energy

log = logging.getLogger(__name__)


def calibrate_mono_gap(
    gap_list,
    mono_energies,
    id_energies,
    knife_motor,
    knife_points,
    beamline,
    md={},
    folder="",
):
    """All energies in eV."""
    config = load_config()
    md = dict(beamline=config["beamline"]["name"], **md)
    now = dt.datetime.now()
    now_str = now.strftime("%Y-%m-%d_%H-%M")
    # Find registered ophyd devices
    monochromator = registry.find(name="monochromator")
    It = registry.find(name="It")
    registry.find(name="I0")
    knife_motor = registry.find(any=knife_motor)
    # Gap scans at each gap
    for new_gap in gap_list:
        # Determine the new file name based on gap
        folder = Path(folder).expanduser()
        fname = folder / f"knife_edge_scans_{now_str}_{beamline}_{new_gap}gap.txt"
        fp = fname.resolve()
        fp.parent.mkdir(parents=True, exist_ok=True)
        log.info(f"Saving calibration results to {fp}")
        # Go to the new gap value
        md["gap"] = new_gap
        yield from bps.mv(monochromator.gap, new_gap)
        # Open the file the write
        with open(fp, mode="x") as fd:
            fd.write(
                "mono_energy\tid_energy\tbragg_arcsec\t"
                "pitch2\t\tknife_cen\tknife_dcen\tknife_com\tknife_dcom\n"
            )
        for mono_energy, id_energy in zip(mono_energies, id_energies):
            # Move to the new energy
            yield from set_energy(mono_energy=mono_energy, id_energy=id_energy)
            # Prepare metadata for the scans
            for key in ["pitch2"]:
                if key in md.keys():
                    del md[key]
            md.update(
                {
                    "target_energy": mono_energy,
                    "actual_energy": monochromator.energy.get().user_readback,
                    "bragg_angle": monochromator.bragg.get().user_readback,
                    "undulator_sp": id_energy,
                }
            )
            # Align the mono pitch motor
            bec = best_effort.BestEffortCallback()
            bec.disable_table()
            if mono_energy < 6500:
                pitch_distance = 50
            else:
                pitch_distance = 150
            # Do the cycle twice: align pitch motor, adjust gain, ...
            for idx in [0, 1]:
                yield from subs_decorator(bec)(align_pitch2)(
                    bec=bec, distance=pitch_distance, md=md
                )
                new_pitch2 = bec.peaks["cen"].get("I0_raw_counts", None)
                md["pitch2"] = new_pitch2
                plt.show()
                # Set the pitch2 to the new value (from below accounting for hysteresis)
                yield from bps.mvr(monochromator.pitch2, -200)
                yield from bps.mv(monochromator.pitch2, new_pitch2)
                # Set the ion chamber gain
                yield from auto_gain()
            # Prepare callback for peak states
            knife_scan_ = knife_scan
            peaks = fitting.PeakStats(
                "knife", "It_raw_counts", calc_derivative_and_stats=True
            )
            knife_scan_ = subs_decorator(peaks)(knife_scan_)
            # Callback for fitting with a step function (erf)
            model = StepModel(form="erf")
            fit_cb = LiveFit(
                model,
                It.raw_counts.name,
                {"x": knife_motor.name},
            )
            knife_scan_ = subs_decorator(fit_cb)(knife_scan_)
            # Do the actual knife scan and fitting
            yield from knife_scan_(
                knife_motor=knife_motor, knife_points=knife_points, md=md
            )
            results = peaks
            # Save the energy and center of mass to disk
            getattr(results["stats"], "cen", None)
            getattr(results["derivative_stats"], "cen", None)
            getattr(results["stats"], "com", None)
            getattr(results["derivative_stats"], "com", None)
            log.info(f"Knife center: {results['stats']}")
            with open(fp, mode="a") as fd:
                fd.write(
                    f"{mono_energy}\t{id_energy}\t{md['bragg_angle']}\t"
                    "{new_pitch2}\t{cen}\t{dcen}\t{com}\t{dcom}\n"
                )
            # Plot results
            if hasattr(results, "x_data"):
                plt.figure()
                ax = plt.gca()
                ax.set_title(f"{mono_energy:.1f} eV / {new_gap} µm gap")
                mpl_plotting.plot_peak_stats(results, ax=ax)
                ax.axvline(results["derivative_stats"].com, label="f' center of mass")
                plt.show()


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2023, UChicago Argonne, LLC
#
# Distributed under the terms of the 3-Clause BSD License
#
# The full license is in the file LICENSE, distributed with this software.
#
# DISCLAIMER
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# -----------------------------------------------------------------------------
