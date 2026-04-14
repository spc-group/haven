import logging
import random
from typing import Literal, Optional, Tuple

import numpy as np
from bluesky import plans as bp
from bluesky import preprocessors as bpp
from bluesky_adaptive.per_event import adaptive_plan, recommender_factory
from bluesky_adaptive.recommendations import NoRecommendation
from numpy import ndarray
from ophyd_async.core import Device
from scipy.interpolate import griddata
from tiled.client import from_profile
from tiled.profiles import get_default_profile_name

from haven.callbacks import Collector

__all__ = ["XANESSamplingRecommender", "adaptive_xanes"]

try:
    import botorch
    import gpytorch
    import torch
    from eaa_core.util import to_numpy, to_tensor
    from eaa_spectroscopy import (
        AdaptiveXANESBayesianOptimization,
        ComprehensiveAugmentedAcquisitionFunction,
    )
except ImportError:
    botorch = None
    gpytorch = None
    torch = None
    AdaptiveXANESBayesianOptimization = None
    ComprehensiveAugmentedAcquisitionFunction = None
    to_numpy = None
    to_tensor = None


def resample(xdata: np.ndarray, ydata: np.ndarray, new_xdata: np.ndarray) -> np.ndarray:
    """Re-sample the x and y data to match new xdata through interpolation."""
    new_ydata = griddata((xdata,), ydata, (new_xdata,))
    return new_ydata


class XANESSamplingRecommender:
    """A recommendation engine for XANES adaptive sampling.

    This agent uses EAA's ``AdaptiveXANESBayesianOptimization`` tool as the
    underlying recommendation engine. Starting with
    n0 randomly positioned measurements of X-ray absorption coefficients
    for each spectrum, the optimizer builds a Gaussian process (GP) model, and
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

    guide: AdaptiveXANESBayesianOptimization | None = None

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
        *args,
        **kwargs,
    ):
        # Collect all input arguments through locals(). A better way
        # is to create a dataclass with all the arguments if the interface
        # allows.
        self.input_args = locals()
        self.energy_range = energy_range

        self.cpu_only = cpu_only

        self.build()

    def build(self):
        self._ensure_eaa()
        self.build_device()

    def _ensure_eaa(self) -> None:
        if AdaptiveXANESBayesianOptimization is None:
            raise ImportError(
                "Adaptive XANES sampling requires optional EAA dependencies. "
                "Install `eaa-core` and `eaa-spectroscopy` to use this plan."
            )

    def _build_acquisition_kwargs(self) -> dict:
        self._ensure_eaa()
        ref_spectra_x = self.input_args["reference_spectra_x"]
        ref_spectra_y = self.input_args["reference_spectra_y"]
        return {
            "gradient_order": 2,
            "differentiation_method": "numerical",
            "reference_spectra_x": (
                to_tensor(ref_spectra_x) if ref_spectra_x is not None else None
            ),
            "reference_spectra_y": (
                to_tensor(ref_spectra_y) if ref_spectra_y is not None else None
            ),
            "phi_r": self.input_args["phi_r"],
            "phi_g": self.input_args["phi_g"],
            "phi_g2": self.input_args["phi_g2"],
            "beta": self.input_args["beta"],
            "gamma": self.input_args["gamma"],
            "addon_term_lower_bound": 3e-2,
            "estimate_posterior_mean_by_interpolation": (
                self.input_args["use_spline_interpolation_for_posterior_mean"]
            ),
            "subtract_background_gradient": True,
            "acqf_weight_func_floor_value": 0.01,
            "acqf_weight_func_post_edge_gain": self.input_args[
                "acqf_weight_func_post_edge_gain"
            ],
            "acqf_weight_func_post_edge_offset": self.input_args[
                "acqf_weight_func_post_edge_offset"
            ],
            "acqf_weight_func_post_edge_width": self.input_args[
                "acqf_weight_func_post_edge_width"
            ],
        }

    def build_device(self):
        if self.cpu_only:
            torch.set_default_device("cpu")
        else:
            if torch.cuda.is_available():
                torch.set_default_device("cuda")
            else:
                torch.set_default_device("cpu")

    def check_guide(self):
        if self.guide is None:
            raise ValueError("Guide is not initialized yet.")
        else:
            return self.guide

    def initialize_guide(self, energies: list[float], values: list[float]) -> None:
        self._ensure_eaa()
        energies = to_tensor(energies).reshape(-1, 1)
        values_ = to_tensor(values)
        if values_.ndim == 1:
            values_ = values_.reshape(-1, 1)

        kernel_lengthscale = self.input_args["override_kernel_lengthscale"]
        if kernel_lengthscale is not None:
            kernel_lengthscale = torch.tensor([kernel_lengthscale], dtype=torch.float32)

        guide = AdaptiveXANESBayesianOptimization(
            bounds=(
                [float(self.input_args["energy_range"][0])],
                [float(self.input_args["energy_range"][1])],
            ),
            acquisition_function_class=ComprehensiveAugmentedAcquisitionFunction,
            acquisition_function_kwargs=self._build_acquisition_kwargs(),
            model_class=botorch.models.SingleTaskGP,
            model_kwargs={"covar_module": gpytorch.kernels.MaternKernel(2.5)},
            n_observations=1,
            kernel_lengthscales=kernel_lengthscale,
            noise_std=np.sqrt(1e-6),
            n_updates_create_acqf_weight_func=5,
            n_discrete_choices=self.input_args["n_discrete_optimizer_points"],
            stopping_uncertainty_threshold=self.input_args[
                "stopping_criterion_uncertainty"
            ],
            stopping_n_updates_to_begin=10,
            stopping_check_interval=5,
            n_max_measurements=self.input_args["n_max_measurements"],
        )
        self.guide = guide
        guide.update(energies, values_)
        guide.build()

    def get_initial_measurement_locations(
        self,
        n: int,
        method: Literal["uniform", "random", "quasirandom", "supplied"] = "uniform",
        supplied_initial_points: Optional[ndarray] = None,
        random_seed: int | None = None,
    ):
        if random_seed is not None:
            torch.random.manual_seed(random_seed)
            np.random.seed(random_seed)
            random.seed(random_seed)
        lb, ub = self.energy_range
        if method == "uniform":
            x_init = np.linspace(lb, ub, n, dtype=float)
        elif method == "random":
            assert n > 2
            x_init = np.random.rand(n - 2) * (ub - lb) + lb
            x_init = np.concatenate([x_init, np.array([lb, ub])])
            x_init = np.sort(x_init)
        elif method == "quasirandom":
            assert n > 2
            x_init = np.linspace(lb, ub, n)
            dx = (np.random.rand(n - 2) - 0.5) * (ub - lb) / (n - 1)
            x_init[1:-1] = x_init[1:-1] + dx
            x_init = np.sort(x_init)
        elif method == "supplied":
            x_init = np.asarray(supplied_initial_points, dtype=float)
        else:
            raise ValueError(
                f"{method} is not a valid method to generate initial locations."
            )
        return x_init

    def tell(self, energy: list[float], value: float) -> None:
        """Update model with a single data points.

        Parameters
        ----------
        energy
          The energy (eV) of the measurement. This may be a scalar-like value
          or a length-1 sequence. Internally it is converted to a tensor with
          shape ``(1, 1)`` before updating the optimizer.
        value
          Measured x-ray absorption coefficient at the energy. Internally it is
          converted to a tensor with shape ``(1, 1)``.
        """
        guide = self.check_guide()
        energy = to_tensor([[float(np.atleast_1d(energy)[0])]])
        value = to_tensor([[float(value)]])
        guide.update(energy, value)

    def tell_many(self, energies: list[float], values: list[float]) -> None:
        r"""Update model with multiple data points.

        Parameters
        ----------
        energies
          Measured energies. The input is reshaped internally to a tensor with
          shape ``(n_samples, 1)``.
        values
          Measured values associated with ``energies``. Accepted input layouts
          are:

          - ``(n_samples,)``: direct :math:`\mu(E)` values
          - ``(n_samples, 1)``: direct :math:`\mu(E)` values
          - ``(n_samples, 2)``: intensity pairs ``[I0, It]``, which are
            converted internally to :math:`\mu(E) = -\log(It / I0)` before
            updating the optimizer

          The final values are always converted to a tensor with shape
          ``(n_samples, 1)``.
        """
        guide = self.check_guide()
        tenergies = to_tensor(energies).reshape(-1, 1)
        values_ = np.asarray(values)
        if values_.ndim == 1:
            µ = values_
        elif values_.shape[1] == 1:
            µ = values_[:, 0]
        else:
            # Convert the measured intensities to µ(E).
            I0 = values_[:, 0]
            It = values_[:, 1]
            µ = -np.log(It / I0)
        tvalues_ = to_tensor(µ).reshape(-1, 1)
        guide.update(tenergies, tvalues_)

    def ask(self, n=1, *args, **kwargs) -> list[float]:
        """Figure out the next point based on the past ones we've measured.

        Parameters
        ----------
        n
          Number of requested suggestions. Only ``n=1`` is currently
          supported.

        Returns
        -------
        list[float]
          The next point to measure. Since the algorithm suggests one point at
          a time, this is a list of length 1. Internally, the underlying EAA
          optimizer returns a tensor with shape ``(1, 1)``, which is converted
          to a Python list.
        """
        guide = self.check_guide()
        if n != 1:
            raise NotImplementedError("Only one point at a time is supported.")
        if guide.should_stop():
            logging.info(
                "Stopping criterion reached. Reason: %s (%s measured)",
                guide.stop_reason,
                len(guide.xs_untransformed),
            )
            raise NoRecommendation
        candidates = guide.suggest(n_suggestions=1)
        candidates = list(np.atleast_1d(np.squeeze(to_numpy(candidates))))

        return candidates


def dummy_measure(*args, **kwargs):
    return None


def _get_tiled_client(profile: str):
    profile_ = profile or get_default_profile_name()
    if not profile_:
        raise ValueError(
            "Adaptive XANES plans require a Tiled profile, "
            "either profile one with the *tiled_profile* "
            "argument or set a default Tiled profile."
        )
    return from_profile(profile_)


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
    cpu_only: bool = True,
    tiled_profile: str = "",
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
    client = _get_tiled_client(profile=tiled_profile)
    runs = [client[uid]["primary/data"].read() for uid in ref_uids]
    # Re-sample the reference spectra so they have the same energy basis
    x_datas = []
    for run in runs:
        x_datas.append(run[energy_positioner.name].compute().values)
    reference_y = []
    step = 0.5
    new_erange: tuple[int | float, int | float] = (
        np.max(np.min(x_datas, axis=1)),
        np.min(np.max(x_datas, axis=1)),
    )
    new_x = np.arange(*new_erange, step)
    for run, x_data in zip(runs, x_datas):
        y_data = (
            np.log(
                run[I0.scaler_channel.net_count.name]
                / run[It.scaler_channel.net_count.name]
            )
            .compute()
            .values
        )
        new_y = resample(x_data, y_data, new_x)
        reference_y.append(new_y)

    recommender = XANESSamplingRecommender(
        reference_spectra_x=new_x,
        reference_spectra_y=np.asarray(reference_y),
        **input_args,
    )

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
    yield from _prime_initial_points(
        It=It,
        I0=I0,
        energy_positioner=energy_positioner,
        recommender=recommender,
        n_initial_measurements=n_initial_measurements,
    )
    # Execute the plan
    first_point = {energy_positioner: np.median(energy_range)}
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


def _prime_initial_points(
    It, I0, energy_positioner, recommender, n_initial_measurements
):
    # Get some initial data points
    x_init = recommender.get_initial_measurement_locations(
        n=n_initial_measurements, method="quasirandom"
    )
    plan = bp.list_scan([It, I0], energy_positioner, x_init)
    collector = Collector()
    plan = bpp.subs_wrapper(plan, collector)
    yield from plan
    # Retrieve scan data from the database
    It_data = collector[It.scaler_channel.net_count.name]
    I0_data = collector[I0.scaler_channel.net_count.name]
    signal = -np.log(It_data / I0_data)
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
