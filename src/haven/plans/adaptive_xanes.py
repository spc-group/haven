from queue import Queue
from typing import Optional, Tuple, List, Literal
import logging
import random

import numpy as np
from numpy import ndarray
import pandas as pd
from scipy.interpolate import griddata
from bluesky import plans as bp
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
from ophyd_async.core import Device

from ..catalog import tiled_client

__all__ = ["XANESSamplingRecommender", "adaptive_xanes"]


def resample(xdata: np.ndarray, ydata: np.ndarray, new_xdata: np.ndarray) -> np.ndarray:
    """Re-sample the x and y data to match new xdata through interpolation."""
    new_ydata = griddata((xdata,), ydata, (new_xdata,))
    return new_ydata


class XANESSamplingRecommender:
    """A recommendation engine for XANES adaptive sampling.
    
    This agent is based on XANESExperimentGuide in autobl 
    (https://github.com/mdw771/auto_beamline_ops). Starting with
    n0 randomly positioned measurements of X-ray absorption coefficients
    for each spectrum, the guide builds a Gaussian process (GP) model, and
    suggests the next energy to measure based on the posterior uncertainty
    that the GP gives and features extracted from the current estimate
    of the spectrum.
    
    Parameters
    ----------
    energy_range
        The range of energies to be measured in eV.
    override_kernel_lengthscale
        If specified, override the kernel lengthscale with this value instead
        of fitting it from the initial data. 
    reference_spectra_x
        The reference spectrum energy values. The shape should be (n,).
    reference_spectra_y
        A stack of reference spectrum y values. The shape shuold be (n_spectra, n).
    phi_r
        Weight of the fitting residue term in the acquisition function.
    phi_g
        Weight of the first-order gradient term in the acquisition function.
    phi_g2
        Weight of the second-order gradient term in the acquisition function.
    beta
        Decay rate of the weights of add-on terms in the acquisition function.
    gamma
        Decay rate of the mixing coefficient between the acquisition reweighting 
        function and the original value.
    use_spline_interpolation_for_posterior_mean
        If true, use spline interpolation to estimate the spectrum instead of
        Gaussian process posterior mean.
    n_discrete_optimizer_points
        The number of discrete points to use in the acquisition function
        optimization.
    acqf_weight_func_post_edge_gain
        The gain for the reweighting function in the post-edge region.
    acqf_weight_func_post_edge_offset
        The offset for the reweighting function in the post-edge region.
        Specified in multiples of the edge width. 
    acqf_weight_func_post_edge_width
        The width for the post-edge gain of the reweighting function.
    stopping_criterion_uncertainty
        The max posterior uncertainty threshold for the stopping criterion.
    n_max_measurements
        The max number of measurements that can be made. Acquisition stops
        when this number is reached or the stopping criterion is triggered.
    cpu_only
        If true, use CPU only.
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
        # Collect all input arguments through locals(). A better way
        # is to create a dataclass with all the arguments if the interface
        # allows. 
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
            supplied_initial_points: Optional[ndarray] = None,
            random_seed: int = None,
    ):
        if random_seed is not None:
            torch.random.manual_seed(random_seed)
            np.random.seed(random_seed)
            random.seed(random_seed)
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

    def tell(self, energy: list[float], values: float) -> None:
        """Update model with a single data points.

        Parameters
        ----------
        energy
          The energy (eV) of the measurement.
        value
          Measured x-ray absorption coefficient at the energy.
        """
        self.check_guide()
        energy = to_tensor([[float(energy[0])]])
        value = to_tensor([[float(value)]])
        self.guide.update(energy, value)

    def tell_many(self, energies: list[float], values: list[float]) -> None:
        """Update model with multiple data points.

        :param xs: _description_
        :param ys: _description_
        """
        self.check_guide()
        tenergies = to_tensor(energies).reshape(-1, 1)
        # Convert the µ(E)
        I0 = values[:, 0]
        It = values[:, 1]
        µ = -np.log(It/I0)
        tvalues = to_tensor(µ).reshape(-1, 1)
        self.guide.update(tenergies, tvalues)

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
    I0: Device,
    It: Device,
    n_initial_measurements: int,
    energy_range: Tuple[float, float],
    energy_positioner: Device = "energy",
    override_kernel_lengthscale: Optional[float] = None,
    reference_spectra_uids: list[str] = [],
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
    ----------
    It
        The ophyd device for the transmitted signal intensity.
    I0
        The ophyd device for the reference signal intensity.
    n_initial_measurements
        The number of initial measurements.
    energy_range
        The range of energies to be measured in eV.
    override_kernel_lengthscale
        If specified, override the kernel lengthscale with this value instead
        of fitting it from the initial data. 
    reference_spectra_uids
        The scan UIDs for retrieving reference spectra from the Tiled database.
    phi_r
        Weight of the fitting residue term in the acquisition function.
    phi_g
        Weight of the first-order gradient term in the acquisition function.
    phi_g2
        Weight of the second-order gradient term in the acquisition function.
    beta
        Decay rate of the weights of add-on terms in the acquisition function.
    gamma
        Decay rate of the mixing coefficient between the acquisition reweighting 
        function and the original value.
    use_spline_interpolation_for_posterior_mean
        If true, use spline interpolation to estimate the spectrum instead of
        Gaussian process posterior mean.
    n_discrete_optimizer_points
        The number of discrete points to use in the acquisition function
        optimization.
    acqf_weight_func_post_edge_gain
        The gain for the reweighting function in the post-edge region.
    acqf_weight_func_post_edge_offset
        The offset for the reweighting function in the post-edge region.
        Specified in multiples of the edge width. 
    acqf_weight_func_post_edge_width
        The width for the post-edge gain of the reweighting function.
    stopping_criterion_uncertainty
        The max posterior uncertainty threshold for the stopping criterion.
    n_max_measurements
        The max number of measurements that can be made. Acquisition stops
        when this number is reached or the stopping criterion is triggered.
    cpu_only
        If true, use CPU only.
    """
    input_args = locals()

    # Retrieve reference spectra from the database
    ref_uids = input_args.pop("reference_spectra_uids")
    client = tiled_client()
    runs = [client[uid]['primary/data'].read() for uid in ref_uids]
    # Re-sample the reference spectra so they have the same energy basis
    x_datas = []
    for run in runs:
        x_datas.append(run[energy_positioner.name].compute().values)
    reference_y = []
    step = 0.5
    new_erange = (
        np.max(np.min(x_datas, axis=1)),
        np.min(np.max(x_datas, axis=1)),
    )
    new_x = np.arange(*new_erange, step)
    for run, x_data in zip(runs, x_datas):
        y_data = np.log(run[I0.scaler_channel.net_count.name] / run[It.scaler_channel.net_count.name]).compute().values
        new_y = resample(x_data, y_data, new_x)
        reference_y.append(new_y)
    
    recommender = XANESSamplingRecommender(reference_spectra_x = new_x,
                                           reference_spectra_y = reference_y,
                                           **input_args)

    detectors = [I0, It]
    ind_keys = [energy_positioner.name]
    dep_keys = [det.scaler_channel.net_count.name for det in detectors]
    rr, queue = recommender_factory(
        recommender,
        independent_keys=ind_keys,
        dependent_keys=dep_keys,
        max_count=np.inf,
    )
    # Prime the model with some initial data points
    yield from _prime_initial_points(It=It, I0=I0, energy_positioner=energy_positioner,
                                     recommender=recommender, n_initial_measurements=n_initial_measurements)
    # Execute the plan
    first_point = {
        energy_positioner: np.median(energy_range)
    }
    yield from adaptive_plan(
        dets=detectors,
        first_point=first_point,
        to_recommender=rr,
        from_recommender=queue,
    )

    
    # Get initial points to measure. In a dynamic experiment, one may save this initial
    # point set and reuse it for subsequent spectra by setting "method" to "supplied"
    # and "supplied_initial_points" to the saved point set.
    # x_init = recommender.get_initial_measurement_locations(n=n_initial_measurements, method='quasirandom')
    # y_init = dummy_measure(x_init)
    
    # recommender.initialize_guide(x_init, y_init)
    
    # while True:
    #     try:
    #         suggested_energy = recommender.ask(n=1)
    #         measured_value = dummy_measure(suggested_energy)
    #         recommender.tell(suggested_energy, measured_value)
    #     except NoRecommendation:
    #         break


def _prime_initial_points(It, I0, energy_positioner, recommender, n_initial_measurements):
    # Get some initial data points
    x_init = recommender.get_initial_measurement_locations(n=n_initial_measurements,
                                                           method='quasirandom')
    init_uid = yield from bp.list_scan([It, I0], energy_positioner, x_init)
    # Retrieve scan data from the database
    client = tiled_client()
    run = client[init_uid]
    It_data = run['primary/data'][It.scaler_channel.net_count.name].read()
    I0_data = run['primary/data'][I0.scaler_channel.net_count.name].read()
    signal = -np.log(It_data/I0_data)
    # Send the scan data to the recommender
    x_init = torch.tensor(x_init)
    signal = torch.tensor(signal.compute())[:, None]
    recommender.initialize_guide(x_init, signal)
    

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
