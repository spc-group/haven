from pathlib import Path

import numpy as np
import pytest
from bluesky_adaptive.recommendations import NoRecommendation

pytest.importorskip("eaa_spectroscopy")
from eaa_spectroscopy import SimulatedSpectrumMeasurementTool

from haven.plans.adaptive_xanes import XANESSamplingRecommender


DATA_PATH = Path(__file__).parent / "data" / "test_adaptive_xanes"


def read_xmu(path: Path) -> dict[str, np.ndarray]:
    data = np.loadtxt(path, comments="#")
    return {
        "e": data[:, 0],
        "xmu": data[:, 1],
    }


def load_data():
    data_raw = read_xmu(DATA_PATH / "10Feb_PtL3_025_042C.xmu")
    _, unique_inds = np.unique(data_raw["e"], return_index=True)
    unique_inds = np.sort(unique_inds)

    energies = data_raw["e"][unique_inds]
    data = data_raw["xmu"][unique_inds]
    ref1 = read_xmu(DATA_PATH / "10Feb_PtL3_024_026C.xmu")["xmu"][unique_inds]
    ref2 = read_xmu(DATA_PATH / "10Feb_PtL3_045_497C.xmu")["xmu"][unique_inds]

    mask = (energies >= 11400) & (energies <= 11700)
    return energies[mask], data[mask], ref1[mask], ref2[mask]


def test_adaptive_xanes(debug: bool = False):
    np.random.seed(124)
    energies, data, ref_spectra_0, ref_spectra_1 = load_data()

    instrument = SimulatedSpectrumMeasurementTool(data=(energies, data))

    params = {
        "energy_range": [energies[0], energies[-1]],
        "override_kernel_lengthscale": 7,
        "reference_spectra_x": energies,
        "reference_spectra_y": np.stack([ref_spectra_0, ref_spectra_1]),
        "phi_r": 1e2,
        "phi_g": 2e-3,
        "phi_g2": 2e-3,
        "stopping_criterion_uncertainty": 0.03,
        "n_max_measurements": 30,
        "cpu_only": True,
    }
    recommender = XANESSamplingRecommender(**params)

    x_init = recommender.get_initial_measurement_locations(
        n=10,
        method="quasirandom",
        random_seed=124,
    )
    y_init = instrument.measure(np.asarray(x_init).reshape(-1, 1), add_noise=False)
    recommender.initialize_guide(x_init, y_init)

    n_measurements = len(x_init)
    while True:
        try:
            suggested_energy = recommender.ask(n=1)
            measured_value = instrument.measure(
                np.asarray(suggested_energy).reshape(-1, 1),
                add_noise=False,
            )
            recommender.tell(
                suggested_energy,
                float(measured_value.squeeze().detach().cpu().numpy()),
            )
            n_measurements += 1
        except NoRecommendation:
            break

    if debug:
        import matplotlib.pyplot as plt
        figure = recommender.guide.visualize_status()
        plt.show()

    assert n_measurements <= params["n_max_measurements"]
    assert n_measurements > 20
    assert recommender.guide.should_stop()


if __name__ == "__main__":
    test_adaptive_xanes(debug=True)
