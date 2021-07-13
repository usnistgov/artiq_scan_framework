from math import ceil, sqrt
import numpy as np


def decay_constant(xdata, ydata):
    """Estimate """
    length = max(xdata) - min(xdata)
    period = estimate_period(xdata, ydata)
    dt = min(period, length)
    i = index_at(xdata, dt)

    # find max/min y in first period
    maxy = max(ydata[0:i + 1])
    miny = min(ydata[0:i + 1])

    # estimate y offset
    B = (maxy - miny) / 2
    ratio = (maxy - B) / (miny - B)
    tau = dt / np.log(ratio)

    return tau


def halfmax(data):
    """Estimate the half max value of the y-data contained in data"""
    return .5 * (max(data) - min(data)) + min(data)


def hwhm(xdata, ydata, side, inv=False):
    """Estimate the half width half max value of the y-data contained in data
    :param xdata - The x data values.
    :param ydata - The y data values.
    :param side - Which side, left or right, of the peak y value to analyze.
    :param inv - Set to true to analyze data that contains a resonant dip (minimum) instead of a peak (maximum).
    """
    hm = halfmax(ydata)

    # find point of max/min
    if inv:
        i_res = ydata.argmin()
    else:
        i_res = ydata.argmax()

    # data range for either side
    if side == 'left':
        i_start = i_res - 1
        i_stop = 0
        step = -1
    elif side == 'right':
        i_start = i_res + 1
        i_stop = len(ydata) - 1
        step = 1

    # initial guess is half the range
    i_hm = ceil((i_stop - i_start) / 2)

    # find point at which data crosses half-max
    for i in range(i_start, i_stop + step, step):
        i_hm = i
        if inv:
            if ydata[i] >= hm:
                break
        else:
            if ydata[i] <= hm:
                break

    hwhm = abs(xdata[i_res] - xdata[i_hm])
    return hwhm


def fwhm(xdata, ydata, inv=False):
    # calc half-widths
    hwhm_left = hwhm(xdata, ydata, side='left', inv=inv)
    hwhm_right = hwhm(xdata, ydata, side='right', inv=inv)

    # fwhm
    return hwhm_left + hwhm_right


def index_at(data, value):
    """Returns index at which values in data first reach value"""
    return np.abs(data - value).argmin()


def eval(string):
    """Evaluates a string and returns the python result"""
    import ast
    return ast.literal_eval(string)


def estimate_period(x_data, y_data):
    """Estimate period of sinusoidal signal using the FFT"""
    return 1 / estimate_freq(x_data, y_data)


def estimate_freq(x_data, y_data):
    """Estimate frequency of sinusoidal signal using the FFT"""
    n = len(y_data)
    n_mid = ceil(n / 2)
    dt = x_data[1] - x_data[0]

    # FFT (throw away f=0 and negative freqs)
    w = abs(np.fft.fft(y_data)[1:n_mid])  # fft coefficient magnitudes
    fs = np.fft.fftfreq(n, dt)[1:n_mid]  # fft frequencies
    freq = fs[np.argmax(w)]  # largest coefficient is the signal frequency
    return freq


# -- data analysis methods (used in auto guessing)
def x_at_max_y(xdata, ydata):
    """Returns the xdata value at which the maximum ydata value occurs
    xdata: numpy array
    ydata: numpy array
    """
    return xdata[np.argmax(ydata)]


def x_at_min_y(xdata, ydata):
    """Returns the xdata value at which the minimum ydata value occurs
    xdata: numpy array
    ydata: numpy array
    """
    return xdata[np.argmin(ydata)]


def max_y(xdata, ydata):
    """Returns the maximum value in ydata
    xdata: numpy array
    ydata: numpy array
    """
    return max(ydata)


def min_y(xdata, ydata):
    """Returns the minmum value in ydata
    xdata: numpy array
    ydata: numpy array
    """
    return min(ydata)


def x_at_y(xdata, ydata, yval):
    idx = find_nearest_idx(ydata, yval)
    return xdata[idx]


def x_at_mid_y(xdata, ydata):
    """Returns xdata value at which ydata takes on a value half way between it's min and max value"""
    mid_y = min(ydata) + ((max(ydata) - min(ydata)) / 2)
    idx = find_nearest_idx(ydata, mid_y)
    return xdata[idx]


def find_nearest_idx(array, value):
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return idx


def tpi_fwhm(xdata, ydata, inverse=False):
    """Estimates pi time from the full width half max of ydata"""
    return (sqrt(5) / 2) * (1 / fwhm(xdata, ydata, inv=inverse))


def tpi_fft(xdata, ydata):
    """Estimates pi time via FFT of rabi flopping data in ydata"""
    return estimate_period(xdata, ydata) / 2
