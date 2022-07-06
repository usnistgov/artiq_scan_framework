from artiq.experiment import *
from artiq_scan_framework import *
from artiq_scan_framework.analysis.curvefits import FitFunction
from artiq_scan_framework.analysis.fit_functions import Line
import numpy as np


class RsbModel(TimeModel):
    """ Heating Rate RSB Data Model"""

    # datasets
    namespace = 'heating_rate.rsb.%type'  #: Dataset namespace
    mirror = False

    persist = True
    broadcast = True
    # stats
    enable_histograms = True
    to_scan = 'wait_time'

    # fits
    main_fit = None
    fit_function = Exp

    @property
    def simulation_args(self):
        if self.to_scan == 'wait_time':
            return {
                'A': -5,
                'b': -1/(200*us),
                'y0': 7,
            }
        if self.to_scan == 'rf_amplitude':
            return {
                'A': -5,
                'b': -1,
                'y0': 7,
            }

    # plots
    @property
    def x_label(self):
        if self.to_scan == 'wait_time':
            return 'wait time'
        if self.to_scan == 'rf_amplitude':
            return 'rf amplitude'
    @property
    def x_units(self):
        if self.to_scan == 'wait_time':
            return 's'
        if self.to_scan == 'rf_amplitude':
            return ''

    @property
    def plot_title(self):
        if self.to_scan == 'wait_time':
            return 'rsb vs wait time'
        if self.to_scan == 'rf_amplitude':
            return 'rsb vs rf amplitude'


class BsbModel(TimeModel):
    """ Heating Rate BSB Data Model """

    # datasets
    namespace = 'heating_rate.bsb.%type'  #: Dataset namespace
    persist = True
    broadcast = True
    mirror = False
    to_scan = 'wait_time'

    # stats
    enable_histograms = True

    # fits
    fit_function = Exp
    main_fit = None
    scan = 'wait_time'

    @property
    def simulation_args(self):
        if self.to_scan == 'wait_time':
            return {
                'A': 1,
                'b': -1 / (200 * us),
                'y0': 7,
            }
        if self.to_scan == 'rf_amplitude':
            return {
                'A': 1,
                'b': -1,
                'y0': 7,
            }

    @property
    def x_label(self):
        if self.to_scan == 'wait_time':
            return 'wait time'
        if self.to_scan == 'rf_amplitude':
            return 'rf amplitude'

    @property
    def x_units(self):
        if self.to_scan == 'wait_time':
            return 's'
        if self.to_scan == 'rf_amplitude':
            return ''

    @property
    def plot_title(self):
        if self.to_scan == 'wait_time':
            return 'bsb'
        if self.to_scan == 'rf_amplitude':
            return 'bsb vs rf amplitude'


class BkgdModel(TimeModel):
    """ Heating Rate BSB Data Model """

    # datasets
    namespace = 'heating_rate.bkgd'  #: Dataset namespace
    persist = True
    broadcast = True
    mirror = False

    # stats
    enable_histograms = True

    # fits

    fit_function = Line
    main_fit = None
    simulation_args = {
        'slope': 0,
        'y_intercept': 0
    }

    # plots
    x_units = 's'
    plot_title = 'bkgd'


class NbarModel(TimeModel):
    """Heating Rate Temp Model"""

    # datasets
    namespace = 'heating_rate.nbar.%type'  #: Dataset namespace
    mirror = True
    persist = True
    broadcast = True
    to_scan = 'wait_time'

    # stats
    enable_histograms = False

    # fits
    fit_function = Line
    fit_use_yerr = True
    main_fit = 'heating_rate'
    fit_map = {
        'slope': 'heating_rate'
    }

    # plots
    y_label = 'n bar'
    scan = 'wait_time'

    @property
    def x_label(self):
        if self.to_scan == 'wait_time':
            return 'wait time'
        if self.to_scan == 'rf_amplitude':
            return 'rf amplitude'
        if self.to_scan == 'frequency':
            return 'rf frequency'

    @property
    def x_units(self):
        if self.to_scan == 'wait_time':
            return 's'
        if self.to_scan == 'rf_amplitude':
            return ''
        if self.to_scan == 'frequency':
            return 'Hz'

    @property
    def plot_title(self):
        if self.to_scan == 'wait_time':
            return 'nbar vs wait time'
        if self.to_scan == 'rf_amplitude':
            return 'nbar vs rf amplitude'
        if self.to_scan == 'frequency':
            return 'nbar vs rf frequency'

    def build(self, rsb_model, bsb_model, bkgd_model, **kwargs):
        self.rsb_model = rsb_model
        self.bsb_model = bsb_model
        self.bkgd_model = bkgd_model
        super().build(**kwargs)

    def load(self):
        """Load previously collected data into local storage within each model"""
        super().load()
        self.bsb_model.load()
        self.rsb_model.load()
        self.bkgd_model.load()

    def calculate(self, i_point, calculation):
        """Calculate nbar and the error in nbar at the given scan point index 'i'"""
        bsb = self.bsb_model.means[i_point]
        bsb_error = self.bsb_model.errors[i_point]
        rsb = self.rsb_model.means[i_point]
        rsb_error = self.rsb_model.errors[i_point]
        avgBkgd = np.nanmean(self.bkgd_model.means)


        ratio = (bsb - avgBkgd) / (rsb - avgBkgd)
        nbar = 1 / (ratio - 1)
        error = (ratio / (ratio - 1)**2) * ((rsb_error / rsb)**2 + (bsb_error / bsb)**2)**.5
        return nbar, error


class Exp(FitFunction):
    """Wrapper class for fitting to  A * exp(b*x) + y0
    """

    @classmethod
    def names(cls):
        return ['A', 'b', 'y0']

    @staticmethod
    def value(x, A, b, y0):
        """Value of exponential at x"""
        return A * np.exp(b * x) + y0

    @staticmethod
    def jacobian(xdata, A, b, y0):
        """Returns Jacobian matrix of partial derivatives of
        A * exp(x*b) + y0, evaluated for all values x
        in xdata, which can be a 1d array or a scalar. Rows are separate values
        of x, columns are partial derivatives w.r.t. different parameters
        """
        xs = np.atleast_1d(xdata)
        jacmat = np.zeros((xs.shape[0], 3))
        for i, x in enumerate(xs):
            jacmat[i, 0] = np.exp(x * b)  # dy/dA
            jacmat[i, 1] = A * x * np.exp(x * b)  # dy/db
            jacmat[i, 2] = 1.  # dy/dy0
        return jacmat

    @classmethod
    def autoguess(cls, x, y, hold={}, man_guess={}, man_bounds={}, man_scale={}):
        """Returns automated guesses for fit parameter starting points and
        bounds for parameter search.  Use initial to provide manual guesses
        for values of parameters to override automated guesses. Valid keyword
        names are 'A', 'b', 'y0'.
        """
        yi = y[0]
        yf = y[-1]
        ymid = y[int(round(len(y) / 2))]

        xmid = (x[-1] - x[0]) / 2  # middle x
        i = index_at(x, xmid)  # middle index
        ratio = (max(y) - y[i]) / (y[i] - min(y))
        dx = x[-1] - xmid
        b = log(ratio) / dx

        # estimate A
        A = (y[-1] - y[0]) / (np.exp(b * x[-1]) - np.exp(b * x[0]))

        # A and b are now known so solve for y0 "exactly"
        y0 = y[i] - A * np.exp(b * (xmid))
        g = {
            'b': b,
            'A': A,
            'y0': y0
        }
        # unbounded optimization
        bounds = ([-np.inf, -np.inf, 0],
                  [np.inf, np.inf, np.inf])
        x_scale = {
            'A': abs(g['A']),
            'b': abs(g['b']),
            'y0': abs(g['y0'])
        }
        return cls.autoguess_outputs(g, x_scale, bounds, hold, man_guess, man_bounds, man_scale)


class Line(FitFunction):
    @classmethod
    def names(cls):
        return ['slope', 'y_intercept']

    @staticmethod
    def value(x, slope, y_intercept):
        """Value of lineshape at f"""
        return slope * x + y_intercept

    @staticmethod
    def jacobian(xdata, y_min, y_max):
        xs = np.atleast_1d(xdata)
        jacmat = np.zeros((xs.shape[0], 2))
        for i, x in enumerate(xs):
            jacmat[i, 0] = x  # dy/dslope
            jacmat[i, 1] = 1  # dy/dy_intercept
        return jacmat

    @classmethod
    def autoguess(cls, x, y, hold={}, man_guess={}, man_bounds={}, man_scale={}):
        # guesses
        g = {
            'slope': (max(y) - min(y)) / (max(x) - min(x)),
            'y_intercept': 0
        }
        bounds = ([-np.inf, -np.inf],
                  [np.inf, np.inf])
        x_scale = {
            'slope': max(1, g['slope']),
            'y_intercept': 1
        }
        return cls.autoguess_outputs(g, x_scale, bounds, hold, man_guess, man_bounds, man_scale)


def index_at(data, value):
    """Returns index at which values in data first reach value"""
    return np.abs(data - value).argmin()