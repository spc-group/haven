from queue import Queue
from typing import Optional, Tuple, List, Literal
import logging

import numpy as np
from numpy import ndarray
import pandas as pd
from bluesky_adaptive.per_event import adaptive_plan, recommender_factory
from bluesky_adaptive.recommendations import NoRecommendation
import autobl.steering
from autobl.steering.configs import XANESExperimentGuideConfig, StoppingCriterionConfig
from autobl.steering.guide import XANESExperimentGuide
from autobl.steering.acquisition import ComprehensiveAugmentedAcquisitionFunction
from autobl.steering.optimization import DiscreteOptimizer
from autobl.util import to_numpy, to_tensor
import torch
import botorch
import gpytorch

from ..instrument.instrument_registry import registry

__all__ = ["XANESSamplingRecommender", "adaptive_xanes"]


class XANESSamplingRecommender:
    """A recommendation engine for XANES adaptive sampling.
    
    This agent is based on XANESExperimentGuide in autobl 
    (https://github.com/mdw771/auto_beamline_ops). Starting with
    n0 randomly positioned measurements of X-ray absorption coefficients
    for each spectrum, the guide builds a Gaussian process (GP) model, and
    suggests the next energy to measure based on the posterior uncertainty
    that the GP gives and features extracted from the current estimate
    of the spectrum.
    """

    def __init__(
        self,
        energy_range: Tuple[float, float],
        override_kernel_lengthscale: Optional[float] = None,
        reference_spectra_x: Optional[ndarray] = None,
        reference_spectra_y: Optional[ndarray] = None,
        phi_r: Optional[float] = None,
        phi_g: Optional[float] = None,
        phi_g2: Optional[float] = None,
        beta: float = 0.999,
        gamma: float = 0.95,
        use_spline_interpolation_for_posterior_mean: bool = True,
        n_discrete_optimizer_points: int = 1000,
        acqf_weight_func_post_edge_gain: float = 3.0,
        acqf_weight_func_post_edge_offset: float = 2.0,
        acqf_weight_func_post_edge_width: float = 1.0,
        stopping_criterion_uncertainty: float = 0.03,
        n_max_measurements: int = 50,
        cpu_only: bool = True,
        *args, **kwargs
    ):
        # Collect all input arguments through locals()
        self.input_args = locals()
        self.energy_range = energy_range
        
        self.configs = None
        self.guide = None
        self.cpu_only = cpu_only
        
        self.build()

    def build(self):
        self.build_configs()
        self.build_device()
        
    def build_configs(self):
        ref_spectra_x = None
        if self.input_args['reference_spectra_x'] is not None:
            ref_spectra_x = to_tensor(self.input_args['reference_spectra_x'])
        ref_spectra_y = None
        if self.input_args['reference_spectra_y'] is not None:
            ref_spectra_y = to_tensor(self.input_args['reference_spectra_y'])
        
        self.configs = XANESExperimentGuideConfig(
            dim_measurement_space=1,
            num_candidates=1,
            model_class=botorch.models.SingleTaskGP,
            model_params={'covar_module': gpytorch.kernels.MaternKernel(2.5)},
            noise_variance=1e-6,
            override_kernel_lengthscale=self.input_args['override_kernel_lengthscale'],
            lower_bounds=torch.tensor([self.input_args['energy_range'][0]]),
            upper_bounds=torch.tensor([self.input_args['energy_range'][1]]),
            acquisition_function_class=ComprehensiveAugmentedAcquisitionFunction,
            acquisition_function_params={'gradient_order': 2,
                                        'differentiation_method': 'numerical',
                                        'reference_spectra_x': ref_spectra_x,
                                        'reference_spectra_y': ref_spectra_y,
                                        'phi_r': self.input_args['phi_r'],
                                        'phi_g': self.input_args['phi_g'],
                                        'phi_g2': self.input_args['phi_g2'],
                                        'beta': self.input_args['beta'],
                                        'gamma': self.input_args['gamma'],
                                        'addon_term_lower_bound': 3e-2,
                                        'estimate_posterior_mean_by_interpolation': True,
                                        'subtract_background_gradient': True,
                                        'debug': False,
                                        },

            optimizer_class=DiscreteOptimizer,
            optimizer_params={'optim_func': botorch.optim.optimize.optimize_acqf_discrete,
                                'optim_func_params': {
                                    'choices': torch.linspace(0, 1, self.input_args['n_discrete_optimizer_points'])[:, None]
                                }
                            },

            n_updates_create_acqf_weight_func=5,
            acqf_weight_func_floor_value=0.01,
            acqf_weight_func_post_edge_gain=self.input_args['acqf_weight_func_post_edge_gain'],
            acqf_weight_func_post_edge_offset=self.input_args['acqf_weight_func_post_edge_offset'],
            acqf_weight_func_post_edge_width=self.input_args['acqf_weight_func_post_edge_width'],
            stopping_criterion_configs=StoppingCriterionConfig(
                method='max_uncertainty',
                params={'threshold': self.input_args['stopping_criterion_uncertainty']},
                n_max_measurements=self.input_args['n_max_measurements']
            ),
            use_spline_interpolation_for_posterior_mean=self.input_args['use_spline_interpolation_for_posterior_mean'],
        )
        
    def build_device(self):
        if self.cpu_only:
            torch.set_default_device('cpu')
        else:
            if torch.cuda.is_available():
                torch.set_default_device('cuda')
            else:
                torch.set_default_device('cpu')
                
    def check_guide(self):
        if self.guide is None:
            raise ValueError("Guide is not initialized yet.")
                
    def initialize_guide(self, energies: list[float], values: list[float]) -> None:
        energies = to_tensor(energies).reshape(-1, 1)
        values = to_tensor(values).reshape(-1, 1)
        self.guide = XANESExperimentGuide(self.configs)
        self.guide.build(energies, values)
        
    def get_initial_measurement_locations(
            self, n: int, 
            method: Literal['uniform', 'random', 'quasirandom', 'supplied'] = 'uniform', 
            supplied_initial_points: Optional[ndarray] = None):
        lb, ub = self.energy_range
        if method == 'uniform':
            x_init = np.linspace(lb, ub, n).double().reshape(-1, 1)
        elif method == 'random':
            assert n > 2
            x_init = np.random.rand(n - 2) * (ub - lb) + lb
            x_init = np.concatenate([x_init, np.array([lb, ub])])
            x_init = np.sort(x_init)
        elif method == 'quasirandom':
            assert n > 2
            x_init = np.linspace(lb, ub, n)
            dx = (np.random.rand(n - 2) - 0.5) * (ub - lb) / (n - 1)
            x_init[1:-1] = x_init[1:-1] + dx
            x_init = np.sort(x_init)
        elif method == 'supplied':
            x_init = supplied_initial_points
        else:
            raise ValueError('{} is not a valid method to generate initial locations.'.format(method))
        return x_init

    def tell(self, energy: float, value: float) -> None:
        """Update model with a single data points.

        Parameters
        ----------
        energy
          The energy (eV) of the measurement..
        value
          Measured x-ray absorption coefficient at the energy.
        """
        self.check_guide()
        energy = to_tensor([[float(energy)]])
        value = to_tensor([[float(value)]])
        self.guide.update(energy, value)

    def tell_many(self, energies: list[float], values: list[float]) -> None:
        """Update model with multiple data points.

        :param xs: _description_
        :param ys: _description_
        """
        self.check_guide()
        energies = to_tensor(energies).reshape(-1, 1)
        values = to_tensor(values).reshape(-1, 1)
        self.guide.update(energies, values)

    def ask(self, n=1, *args, **kwargs) -> list[float]:
        """Figure out the next point based on the past ones we've measured.
        
        Returns
        -------
        list[float]. The next point to measure. Since the algorithm suggests
            one point at a time, this is a list of length 1.
        """
        if n != 1:
            raise NotImplementedError('Only one point at a time is supported.')
        candidates = self.guide.suggest().double()
        candidates = list(np.atleast_1d(np.squeeze(to_numpy(candidates))))
        
        if self.guide.stopping_criterion.check():
            logging.info("Stopping criterion reached. Reason: {} ({} measured)".format(
                self.guide.stopping_criterion.reason, len(self.guide.data_x)))
            raise NoRecommendation
        
        return candidates


def dummy_measure(*args, **kwargs):
    return None


def adaptive_xanes(
    n_initial_measurements: int,
    energy_range: Tuple[float, float],
    override_kernel_lengthscale: Optional[float] = None,
    reference_spectra_x: Optional[ndarray] = None,
    reference_spectra_y: Optional[ndarray] = None,
    phi_r: Optional[float] = None,
    phi_g: Optional[float] = None,
    phi_g2: Optional[float] = None,
    beta: float = 0.999,
    gamma: float = 0.95,
    use_spline_interpolation_for_posterior_mean: bool = True,
    n_discrete_optimizer_points: int = 1000,
    acqf_weight_func_post_edge_gain: float = 3.0,
    acqf_weight_func_post_edge_offset: float = 2.0,
    acqf_weight_func_post_edge_width: float = 1.0,
    stopping_criterion_uncertainty: float = 0.03,
    n_max_measurements: int = 50,
    cpu_only: bool = True
):
    """An adaptive Bluesky plan for adaptive XANES sampling.

    Parameters
    ==========
    """
    input_args = locals()
    
    recommender = XANESSamplingRecommender(**input_args)
    
    # Get initial points to measure. In a dynamic experiment, one may save this initial
    # point set and reuse it for subsequent spectra by setting "method" to "supplied"
    # and "supplied_initial_points" to the saved point set.
    x_init = recommender.get_initial_measurement_locations(n=n_initial_measurements, method='quasirandom')
    y_init = dummy_measure(x_init)
    
    recommender.initialize_guide(x_init, y_init)
    
    while True:
        try:
            suggested_energy = recommender.ask(n=1)
            measured_value = dummy_measure(suggested_energy)
            recommender.tell(suggested_energy, measured_value)
        except NoRecommendation:
            break
    

# -----------------------------------------------------------------------------
# :author:    Mark Wolfman, Ming Du
# :email:     wolfman@anl.gov, mingdu@anl.gov
# :copyright: Copyright © 2024, UChicago Argonne, LLC
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
