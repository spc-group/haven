import pytest
pytest.importorskip("autobl")

import matplotlib.pyplot as plt
import torch
import numpy as np

from autobl.steering.measurement import SimulatedMeasurement
from autobl.steering.io_util import *
from autobl.steering.configs import ExperimentAnalyzerConfig
from autobl.steering.analysis import ScanningExperimentAnalyzer
from autobl.util import *
from bluesky_adaptive.recommendations import NoRecommendation

from haven.plans.adaptive_xanes import XANESSamplingRecommender


def load_data():
    data_raw = read_nor('data/test_adaptive_xanes/10Feb_PtL3_025_042C.xmu')
    _, unique_inds = np.unique(data_raw['e'], return_index=True)
    unique_inds = np.sort(unique_inds)
    data_raw = data_raw.iloc[unique_inds]
    ref1 = read_nor('data/test_adaptive_xanes/10Feb_PtL3_024_026C.xmu').iloc[unique_inds]
    ref2 = read_nor('data/test_adaptive_xanes/10Feb_PtL3_045_497C.xmu').iloc[unique_inds]
    
    data = data_raw['xmu'].to_numpy()
    ref_spectra_0 = ref1['xmu'].to_numpy()
    ref_spectra_1 = ref2['xmu'].to_numpy()
    energies = data_raw['e'].to_numpy()
    
    # Only keep 11400 - 11700 eV
    mask = (energies >= 11400) & (energies <= 11700)
    data = data[mask]
    ref_spectra_0 = ref_spectra_0[mask]
    ref_spectra_1 = ref_spectra_1[mask]
    energies = energies[mask]
    
    return energies, data, ref_spectra_0, ref_spectra_1


def test_adaptive_xanes():
    set_random_seed(124)
    energies, data, ref_spectra_0, ref_spectra_1 = load_data()
    
    instrument = SimulatedMeasurement(data=(energies[None, :], data))
    
    params = {
        'energy_range': [energies[0], energies[-1]],
        'override_kernel_lengthscale': 7,
        'reference_spectra_x': energies,
        'reference_spectra_y': np.stack([ref_spectra_0, ref_spectra_1]),
        'phi_r': 1e2,
        'phi_g': 2e-3,
        'phi_g2': 2e-3,
        'stopping_criterion_uncertainty': 0.03,
        'n_max_measurements': 50,
        'cpu_only': True,
    }
    recommender = XANESSamplingRecommender(**params)
    
    # Get initial points to measure. In a dynamic experiment, one may save this initial
    # point set and reuse it for subsequent spectra by setting "method" to "supplied"
    # and "supplied_initial_points" to the saved point set.
    x_init = recommender.get_initial_measurement_locations(n=20, method='quasirandom')
    y_init = instrument.measure(x_init)
    
    recommender.initialize_guide(x_init, y_init)
    
    # The analyzer is just used for tracking data and generating plots for debugging. It is not needed
    # for the recommender to run.
    analyzer = ScanningExperimentAnalyzer(
        ExperimentAnalyzerConfig(
            name='Pt',
            output_dir='tmp',
            n_plot_interval=5
        ), 
        recommender.guide,
        energies, 
        data,
        n_target_measurements=params['n_max_measurements'],
        n_init_measurements=20
    )
    analyzer.increment_n_points_measured(20)
    analyzer.update_analysis()
    
    while True:
        try:
            suggested_energy = recommender.ask(n=1)
            measured_value = instrument.measure(suggested_energy)
            recommender.tell(np.squeeze(suggested_energy), np.squeeze(measured_value))
            analyzer.increment_n_points_measured(1)
            analyzer.update_analysis()
        except NoRecommendation:
            break
    analyzer.save_analysis()
    

if __name__ == '__main__':
    test_adaptive_xanes()
