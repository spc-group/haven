# larch imports
import copy
import os

# General imports
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from larch.io import read_ascii
from larch.plot.plotly_xafsplots import *
from larch.xafs import autobk, estimate_noise, pre_edge, sort_xafs, xftf

# Set the default font for the entire plot
mpl.rcParams["font.family"] = "Arial"


# Constant
# for epsilon_r method
r_window_size = 30  # this can be changed depending on the data points.
noise_factor = 0.2  # not sure now
# for random noise method
average_num = 5  # smoothing data using average of 5 data points
random_noise_window_size = 10  # this can be changed depending on the data points.


def find_closest_index(array, target_value):
    """
    Finds the index of the element in a NumPy array that is closest to the target_value.

    Parameters:
    - array (numpy.ndarray): The NumPy array of numbers to search.
    - target_value (float): The value to find the closest match for.

    Returns:
    - int: The index of the element closest to the target_value.
    """
    closest_index = np.abs(array - target_value).argmin()
    return closest_index


def find_smoothest_range(data, window_size):
    """
    Finds the smoothest range in an oscillation curve based on variance.
    Parameters:
    - data: 1D array or list representing the oscillation curve.
    - window_size: Size of the window for calculating variance.

    Returns:
    - Start and end indices of the smoothest range.
    """
    window_size = int(window_size)  # Ensure window_size is an integer
    variances = np.zeros(len(data) - window_size + 1)
    for i in range(len(variances)):
        variances[i] = np.var(data[i : i + window_size])
    smoothest_index = np.argmin(variances)
    start_index = smoothest_index
    end_index = smoothest_index + window_size - 1
    return start_index, end_index


def load_data(data_path):
    """
    From this step, the data including all the Larch processes, eg. data.r and data.chi_r will automatically created in the data group after xftf process
    """
    data = read_ascii(data_path, labels="col1, col2")
    data.is_frozen = False
    data.datatype = "xas"
    data.xdat = data.data[0, :]
    data.ydat = data.data[1, :] / 1.0
    data.yerr = 1.0
    data.energy = data.xdat
    data.mu = data.ydat
    sort_xafs(data, overwrite=True, fix_repeats=True)
    data.filename = data_path.split(os.sep)[-1]
    return data


def data_nor_bg(data, figure=True):
    # Normalization
    pre_edge(data, pre1=-100, pre2=-20.00, nvict=0, nnorm=2, norm1=50.00, norm2=1000)
    # Background function
    autobk(
        data,
        rbkg=1.0,
        ek0=data.e0,
        kmin=0.000,
        kmax=30,
        kweight=2.0,
        clamp_lo=0,
        clamp_hi=0,
    )

    if figure:
        fig1 = plot_mu(
            data,
            show_norm=False,
            show_deriv=False,
            show_pre=True,
            show_post=True,
            show_e0=True,
            with_deriv=False,
            emin=None,
            emax=None,
            label=f"mu_nor_bg",
            offset=0,
            title=None,
            fig=None,
            show=True,
        )
        fig1.set_style(width=800, height=350)
        indice = np.where(data.energy > data.ek0)[0][0]
        fig1.add_plot(
            [data.energy[indice]],
            [data.mu[indice]],
            label="ek0",
            color="red",
            linewidth=0,
            marker=dict(size=5),
        )
        fig1.show()
        plot_bkg(data, label=f"bkg_nor_bg")
    return data


def scan_num_epsilon_r(folder, data_list, figure=True):
    """
    Finds the scan number while the noise is smaller than noise_factor*(the 1st scan data noise)
    Here the noise_factor is 0.2, which is not sure now.
    Parameters:
    - folder: the folder saving all the data.
    - data_list: a data list of data with one scan, two scan merged, three scan merged...
    - figure: whether plots are shown in the noise estimate process

    Returns:
    - scan number that is good for measurement
    """

    epsilon_r_list = []

    data_path = folder + data_list[0][0]
    data = load_data(data_path)
    datacopy = copy.deepcopy(data)
    data_nor_bg(datacopy, figure=False)
    xftf(
        datacopy,
        kmin=3,
        kmax=12,
        dk=1.000,
        kweight=3.000,
        window="Hanning",
        rmax_out=30.000,
    )  # k weight should be 3 to magnifize the noise part.
    start_index, end_index = find_smoothest_range(datacopy.chir_re, r_window_size)
    r_start_noise = datacopy.r[start_index]
    r_end_noise = datacopy.r[end_index]

    for n in range(len(data_list)):
        data_path = folder + data_list[n][0]
        print(data_path)
        data = load_data(data_path)
        datacopy = copy.deepcopy(data)
        data_nor_bg(datacopy, figure=False)

        xftf(
            datacopy,
            kmin=3,
            kmax=12,
            dk=1.000,
            kweight=3.000,
            window="Hanning",
            rmax_out=30.000,
        )

        estimate_noise(
            datacopy.k,
            datacopy.chi,
            group=datacopy,
            rmin=r_start_noise,
            rmax=r_end_noise,
            kweight=3,
            kmin=3,
            kmax=12,
            dk=1,
            kwindow="Hanning",
        )  # , dk2=None, kstep=0.05,  nfft=2048, _larch=None)
        epsilon_r = datacopy.epsilon_r
        print(epsilon_r)
        epsilon_r_list.append(epsilon_r)

    noise = list(zip(range(len(data_list)), epsilon_r_list))
    if len(noise) == 1:
        scan_num = noise[0][0]
    else:
        for i in range(1, len(noise)):
            current_value = noise[i][1]
            first_value = noise[0][1]
        if current_value < noise_factor * first_value:
            scan_num = noise[i - 1][0]
        else:
            scan_num = noise[-1][0]

    if figure:
        plt.figure()
        plt.plot(range(len(data_list)), epsilon_r_list)
        plt.xlabel("scan number")
        plt.ylabel("epsilon_r")

    return scan_num


def scan_num_random_noise(folder, data_list, figure=True):
    """
    The random noise method follows Shelly D. Kelly Chapter14 Analysis of Soils and Minerals Using X-ray Absorption SPectroscopy.
    """
    random_noise_list = []

    # find a region to estimate the random noise. The region should not be affected by a sudden drop of data points at the peak wings. So the function find_smoothest_range is used.
    data_path = folder + data_list[0][0]
    data = load_data(data_path)
    datacopy = copy.deepcopy(data)
    data_nor_bg(datacopy, figure=False)
    xftf(
        datacopy,
        kmin=3,
        kmax=12,
        dk=1.000,
        kweight=2.000,
        window="Hanning",
        rmax_out=30.000,
    )
    start_index = find_closest_index(datacopy.k, 9)
    end_index = find_closest_index(datacopy.k, 11)
    # Filter the data to get only the rows where k is in the range [9, 11]
    filtered_data = (datacopy.k[start_index:end_index]) ** 2 * datacopy.chi[
        start_index:end_index
    ]
    data_series = pd.Series(filtered_data)
    # Apply a moving average to estimate the signal
    smoothed_signal = data_series.rolling(window=average_num, center=True).mean()
    # Fill any NaN values that result from the moving average
    smoothed_signal = smoothed_signal.fillna(method="bfill").fillna(method="ffill")
    # Estimate noise as the difference between the original data and the smoothed signal
    noise = data_series - smoothed_signal
    start_index_noise, end_index_noise = find_smoothest_range(
        noise, random_noise_window_size
    )

    for n in range(len(data_list)):
        data_path = folder + data_list[n][0]
        print(data_path)
        data = load_data(data_path)
        datacopy = copy.deepcopy(data)
        data_nor_bg(datacopy, figure=False)

        xftf(
            datacopy,
            kmin=3,
            kmax=12,
            dk=1.000,
            kweight=2.000,
            window="Hanning",
            rmax_out=30.000,
        )
        if figure:
            plt.figure()
            plt.subplot(2, 1, 1)
            plt.plot(datacopy.k, (datacopy.k) ** 2 * datacopy.chi, label=data_path)
            plt.axvspan(9, 11, color="yellow", alpha=0.3)
            plt.xlabel("k (Å^(-1))")
            plt.xlim(0, np.max(datacopy.k))
            plt.ylabel("$k^2\chi(k)$ ($Å^{-2}$)")
            plt.legend(loc="upper left", bbox_to_anchor=(1, 1))

            plt.subplot(2, 1, 2)
            plt.plot(datacopy.k, (datacopy.k) ** 2 * datacopy.chi)
            plt.xlabel("k (Å^(-1))")
            plt.xlim(9, 11)
            plt.ylabel("$k^2\chi(k)$ ($Å^{-2}$)")
            plt.legend(loc="upper left", bbox_to_anchor=(1, 1))

        start_index = find_closest_index(datacopy.k, 9)
        end_index = find_closest_index(datacopy.k, 11)
        filtered_data = (datacopy.k[start_index:end_index]) ** 2 * datacopy.chi[
            start_index:end_index
        ]
        data_series = pd.Series(filtered_data)
        smoothed_signal = data_series.rolling(window=average_num, center=True).mean()
        smoothed_signal = smoothed_signal.fillna(method="bfill").fillna(method="ffill")
        noise = data_series - smoothed_signal
        noise_flat = noise[start_index_noise:end_index_noise]

        if figure:
            plt.figure(figsize=(8, 8))
            plt.subplot(2, 1, 1)
            plt.plot(np.arange(len(smoothed_signal)), smoothed_signal, "r.-")
            plt.title("Smoothed data averaged by 5 data poins")

            plt.subplot(2, 1, 2)
            plt.plot(np.arange(len(noise)), noise, "r.-")
            plt.axvspan(start_index_noise, end_index_noise, color="c", alpha=0.5)
            plt.title("Random noise and the region for the final standard deviation")

        noise_std = np.std(noise_flat)
        print(noise_std)
        random_noise_list.append(noise_std)

    noise = list(zip(range(len(data_list)), random_noise_list))
    if len(noise) == 1:
        scan_num = noise[0][0]
    else:
        for i in range(1, len(noise)):
            current_value = noise[i][1]
            if current_value < 0.1:
                scan_num = noise[i][0]
                break
            else:
                scan_num = noise[-1][0]

    if figure:
        plt.figure()
        plt.plot(range(len(data_list)), random_noise_list)
        plt.xlabel("scan number")
        plt.ylabel("random noise (%)")

    return scan_num
