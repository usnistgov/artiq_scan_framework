# additional fit functions for the analysis sub-package
from scan_framework.analysis.curvefits import FitFunction
from scan_framework.analysis.functions import *
import scipy as scipy
import scipy.special
import numpy as np



class InvCos(FitFunction):
    """Wrapper class for fitting to sine wave amplitude/2 (-cos(pi*x/pi_time + phase) + 1) + y_min"""

    @classmethod
    def names(cls):
        return ['amplitude', 'pi_time', 'phase', 'y_min']

    @staticmethod
    def value(x, amplitude, pi_time, phase, y_min):
        """Value of sine at time t"""
        return amplitude / 2 * (-np.cos(np.pi * x / pi_time + phase) + 1) + y_min

    @staticmethod
    def jacobian(x_data, amplitude, pi_time, phase, y_min):
        """Returns Jacobian matrix of partial derivatives of
        amplitude/2 (sin(pi*x/pi_time + phase) + 1) + y_min, evaluated for all values x
        in xdata, which can be a 1d array or a scalar. Rows are separate values
        of x, columns are partial derivatives w.r.t. different parameters
        """
        xs = np.atleast_1d(x_data)

        jacmat = np.zeros((xs.shape[0], 4))
        for i, x in enumerate(xs):
            jacmat[i, 0] = 1 / 2 * (-np.cos(np.pi * x / pi_time + phase) + 1)  # dy/damplitude
            jacmat[i, 1] = amplitude / 2 * np.sin(np.pi * x / pi_time + phase) * (
                        -np.pi * x / (pi_time ** 2))  # dy/dpi_time
            jacmat[i, 2] = amplitude / 2 * np.sin(np.pi * x / pi_time + phase)  # dy/dphase
            jacmat[i, 3] = 1.  # dy/dy_min
        return jacmat

    @classmethod
    def autoguess(cls, x, y, hold={}, man_guess={}, man_bounds={}, man_scale={}):
        """Returns automated guesses for fit parameter starting points and
        bounds for parameter search.  Use initial to provide manual guesses
        for values of parameters to override automated guesses. Valid keyword
        names are 'A', 'f', 'phi', 'y0'.
        """
        g = dict()
        g['amplitude'] = max(y) - min(y)
        g['pi_time'] = tpi_fft(x, y)
        g['phase'] = 0
        g['y_min'] = max(0, min(y))
        # constrain amplitude, pi_time to be positive, phase to be in range [0, 2*pi], y_min to be positive
        bounds = ([0, 0, 0, 0],
                  [np.inf, np.inf, 2 * np.pi, np.inf])

        # default scales
        x_scale = {
            'amplitude': 1,
            'phase': 1,
            'pi_time': 1e-6,
            'y_min': 1
        }

        # override scales with guesses
        if g['amplitude'] > 0:
            x_scale['amplitude'] = g['amplitude']
        if g['pi_time'] > 0:
            x_scale['pi_time'] = g['pi_time']
        if g['y_min'] > 0:
            x_scale['y_min'] = g['y_min']
        return cls.autoguess_outputs(g, x_scale, bounds, hold, man_guess, man_bounds, man_scale)


class Sinc(FitFunction):
    @classmethod
    def names(cls):
        return ['y_min', 'y_max', 'pi_time', 'frequency']

    @staticmethod
    def simulation_args():
        return {
            'frequency': 0,
            'y_min': 2.5,
            'y_max': 10,
            'pi_time': 20e-6
        }

    @staticmethod
    def value(x, y_min, y_max, pi_time, frequency):
        """Value of lineshape at f"""

        arg = 4 * pi_time ** 2 * (x - frequency) ** 2 + 1
        return y_min + (y_max - y_min) / (2 * arg) * (1 - np.cos(np.pi * np.sqrt(arg)))

    @staticmethod
    def jacobian(xdata, y_min, y_max, pi_time, frequency):
        xs = np.atleast_1d(xdata)
        jacmat = np.zeros((xs.shape[0], 4))
        for i, x in enumerate(xs):
            # f = ymin + ((y_max-y_min)/b)*a
            arg = 4 * pi_time ** 2 * (x - frequency) ** 2 + 1
            a = 1 - np.cos(np.pi * np.sqrt(arg))
            b = 2 * arg

            dt_arg = 8 * pi_time * (x - frequency) ** 2
            df0_arg = -8 * pi_time ** 2 * (x - frequency)

            dt_a = np.sin(np.pi * np.sqrt(arg)) * (np.pi / 2) * (1 / np.sqrt(arg)) * dt_arg
            dt_b = 2 * dt_arg

            df0_a = np.sin(np.pi * np.sqrt(arg)) * (np.pi / 2) * (1 / np.sqrt(arg)) * df0_arg
            df0_b = 2 * df0_arg

            jacmat[i, 0] = 1 - a / b  # dy/dy_min
            jacmat[i, 1] = a / b  # dy/dy_max
            jacmat[i, 2] = (y_max - y_min) * (dt_a * b - dt_b * a) / (np.power(b, 2))  # dy/dpi_time
            jacmat[i, 3] = (y_max - y_min) * (df0_a * b - df0_b * a) / (np.power(b, 2))  # dy/df0
        return jacmat

    @classmethod
    def autoguess(cls, x, y, hold={}, man_guess={}, man_bounds={}, man_scale={}):
        # guesses
        g = {
            'y_min': min(y),
            'y_max': max(y),
            'pi_time': tpi_fwhm(x, y),
            'frequency': x_at_max_y(x, y)
        }
        bounds = ([-np.inf, -np.inf, -np.inf, -np.inf],
                  [np.inf, np.inf, np.inf, np.inf])
        x_scale = {
            'y_min': g['y_min'],
            'y_max': g['y_max'],
            'pi_time': g['pi_time'],
            'frequency': g['frequency']
        }
        if x_scale['y_min'] <= 0:
            x_scale['y_min'] = 1
        if x_scale['y_max'] <= 0:
            x_scale['y_max'] = 1
        return cls.autoguess_outputs(g, x_scale, bounds, hold, man_guess, man_bounds, man_scale)


class SincInv(FitFunction):

    @classmethod
    def names(cls):
        return ['y_min', 'y_max', 'pi_time', 'frequency']

    @staticmethod
    def value(x, y_min, y_max, pi_time, frequency):
        arg = 4 * pi_time ** 2 * (x - frequency) ** 2 + 1
        return y_max - (y_max - y_min) / (2 * arg) * (1 - np.cos(np.pi * np.sqrt(arg)))

    @staticmethod
    def jacobian(xdata, y_min, y_max, pi_time, frequency):
        xs = np.atleast_1d(xdata)
        jacmat = np.zeros((xs.shape[0], 4))
        for i, x in enumerate(xs):
            # f = ymin + ((y_max-y_min)/b)*a
            arg = 4 * pi_time ** 2 * (x - frequency) ** 2 + 1
            a = 1 - np.cos(np.pi * np.sqrt(arg))
            b = 2 * arg

            dt_arg = 8 * pi_time * (x - frequency) ** 2
            df0_arg = -8 * pi_time ** 2 * (x - frequency)

            dt_a = np.sin(np.pi * np.sqrt(arg)) * (np.pi / 2) * (1 / np.sqrt(arg)) * dt_arg
            dt_b = 2 * dt_arg

            df0_a = np.sin(np.pi * np.sqrt(arg)) * (np.pi / 2) * (1 / np.sqrt(arg)) * df0_arg
            df0_b = 2 * df0_arg

            jacmat[i, 0] = a / b  # dy/dy_min
            jacmat[i, 1] = 1 - a / b  # dy/dy_max
            jacmat[i, 2] = -(y_max - y_min) * (dt_a * b - dt_b * a) / (np.power(b, 2))  # dy/dpi_time
            jacmat[i, 3] = -(y_max - y_min) * (df0_a * b - df0_b * a) / (np.power(b, 2))  # dy/df0
        return jacmat

    @classmethod
    def autoguess(cls, x, y, hold={}, man_guess={}, man_bounds={}, man_scale={}):
        g = {
            'y_min': min(y),
            'y_max': max(y),
            'pi_time': tpi_fwhm(x, y, inverse=True),
            'frequency': x_at_min_y(x, y)
        }
        bounds = ([-np.inf, -np.inf, -np.inf, -np.inf],
                  [np.inf, np.inf, np.inf, np.inf])

        x_scale = {}
        if abs(g['y_min']) > 0:
            x_scale['y_min'] = abs(g['y_min'])
        else:
            x_scale['y_min'] = 1
        if abs(g['y_max']) > 0:
            x_scale['y_max'] = abs(g['y_max'])
        else:
            x_scale['y_max'] = 1
        if abs(g['pi_time']) > 0:
            x_scale['pi_time'] = abs(g['pi_time'])
        else:
            x_scale['pi_time'] = 1e-6
        if abs(g['frequency']) > 0:
            x_scale['frequency'] = abs(g['frequency'])
        else:
            x_scale['frequency'] = 1e6

        return cls.autoguess_outputs(g, x_scale, bounds, hold, man_guess, man_bounds, man_scale)


class SatParam(FitFunction):

    @classmethod
    def names(cls):
        return ['satParam', 'brightRate']

    @staticmethod
    def value(x, satParam, brightRate):
        """Value of function at time x"""
        return brightRate * (x + 0.000217 / satParam * (np.exp(-4608 * x * satParam) - 1))

    @staticmethod
    def jacobian(xdata, s, b):
        xs = np.atleast_1d(xdata)
        jacmat = np.zeros((xs.shape[0], 2))
        for i, x in enumerate(xs):
            jacmat[i, 0] = b * 0.000217 / s ** 2 * np.exp(-4608 * x * s) * (np.exp(4608 * x * s) - 4608 * x * s - 1)
            jacmat[i, 1] = 0
        return jacmat

    @classmethod
    def autoguess(cls, x, y, hold={}, man_guess={}, man_bounds={}, man_scale={}):
        # guesses
        g = {
            'satParam': 0.5,
            'brightRate': 14000
        }

        bounds = ([0, 1.5],
                  [1000, 200000])
        x_scale = {
            'satParam': g['satParam'],
            'brightRate': g['brightRate']
        }
        return cls.autoguess_outputs(g, x_scale, bounds, hold, man_guess, man_bounds, man_scale)


class IntBeam(FitFunction):
    """Class for fitting to an integrated gaussian beam.   e.g. for knife edge scans to find feature heights."""

    @classmethod
    def names(cls):
        """Valid parameter names for this function type, in order for value()
        method arguments"""
        return ['A', 'sigma', 'x0', 'y0']

    @staticmethod
    def value(x, A, sigma, x0, y0):
        """Value of Gaussian at x"""
        return A * (1 + scipy.special.erf((x - x0) / (np.sqrt(2) * sigma))) / 2 + y0

    @staticmethod
    def jacobian(xdata, A, sigma, x0, y0):
        """Returns Jacobian matrix of partial derivatives of
        A * exp(-(x-x0)^2/(2*sigma^2)) + y0, evaluated for all values x
        in xdata, which can be a 1d array or a scalar. Rows are separate values
        of x, columns are partial derivatives w.r.t. different parameters
        """
        xs = np.atleast_1d(xdata)
        jacmat = np.zeros((xs.shape[0], 4))
        for i, x in enumerate(xs):
            # dy/dA
            jacmat[i, 0] = np.sqrt(np.pi / 2) * sigma * (1 + scipy.special.erf((x - x0) / np.sqrt(2) * sigma))

            # dy/dsigma
            jacmat[i, 1] = -(
                    (
                            A * np.exp(
                        -((x - x0) ** 2 / (2 * sigma ** 2))
                    ) * (x - x0)
                    ) / sigma
            )
            + A * np.sqrt(np.pi / 2)(1 + scipy.special.erf((x - x0) / (np.sqrt(2) * sigma)))

            # dy/dx0
            jacmat[i, 2] = -A * np.exp(-((x - x0) ** 2 / (2 * sigma ** 2)))

            # dy/dy0
            jacmat[i, 3] = 1.

        return jacmat

    @staticmethod
    def guess_y0(x_data, y_data):
        y0 = min(y_data)
        return y0

    @staticmethod
    def guess_x0(x_data, y_data):
        x0 = x_at_mid_y(x_data, y_data)
        return x0

    @staticmethod
    def guess_A(x_data, y_data):
        A = max(y_data) - min(y_data)
        return A

    @staticmethod
    def guess_sigma(x_data, y_data, A_guess, x0_guess, y0_guess):
        """Guesses sigma given guesses for A, x0, and y0"""

        # what's the value of y at x=sigma?
        ytarget = IntBeam.value(x=1, A=A_guess, sigma=1, x0=0, y0=y0_guess)

        # find datapoint closest to that y-value
        idx = find_nearest_idx(y_data, ytarget)
        xx = x_data - x0_guess
        sigma = xx[idx]
        if sigma == 0:
            sigma = xx[idx + 1]
        return sigma

    @classmethod
    def autoguess(cls, x, y, hold={}, man_guess={}, man_bounds={},
                  man_scale={}):
        """Returns automated guesses for fit parameter starting points and
        bounds for parameter search.  Manual guesses, bounds, and scales
        provided in dictionaries will override automatic values unless
        named parameter is being held. Valid keyword names are in cls.names()
        """
        mid = np.median(y)
        amax = np.amax(y)
        amin = np.amin(y)
        p20 = np.percentile(y, 20)
        p80 = np.percentile(y, 80)
        up = True if (p80 - mid > mid - p20) else False  # pointing up or down?

        # pick a range near edges to avoid accidentally guessing as a peak
        xfrac = 0.1
        xmin = np.amin(x)
        xmax = np.amax(x)
        xlo = (xmax - xmin) * xfrac + xmin
        xhi = xmax - (xmax - xmin) * xfrac

        # construct autoguess values
        g = {
            'A': IntBeam.guess_A(x, y),
            'x0': IntBeam.guess_x0(x, y),
            'y0': IntBeam.guess_y0(x, y)
        }
        g['sigma'] = IntBeam.guess_sigma(x, y, g['A'], g['x0'], g['y0'])

        # default bounds: constrain sigma to be positive
        bounds = ([-np.inf, 0., -np.inf, -np.inf], [np.inf, np.inf, np.inf,
                                                    np.inf])

        # generate rough natural scale values
        xsc = {}
        xsc['A'] = np.absolute(g['A'])
        xsc['sigma'] = g['sigma']
        xsc['x0'] = max(np.absolute(xmax), np.absolute(xmin))
        xsc['y0'] = np.absolute(g['A'])

        if xsc['A'] == 0:
            xsc['A'] = 1
        if xsc['y0'] == 0:
            xsc['y0'] = 1
        if xsc['x0'] == 0:
            xsc['x0'] = 1
        if xsc['sigma'] == 0:
            xsc['sigma'] = 1
        return cls.autoguess_outputs(g, xsc, bounds, hold, man_guess,
                                     man_bounds, man_scale)
