from .helpers import *
import numpy as np
from .curvefits import FitFunction
from .helpers import *
from ..lib.stats import thermal_dist_nd, fock_states_nd, fock_states, thermal_dist
from ..lib.flopping import rabi_rate_fast_nd, rabi_rate_fast
from ..lib.misc import *
import scipy as scipy
import scipy.special
from scipy import special as sp

import math

kHz = 1e3
us = 1e-6
MHz = 1e6


# work in progress
# class Logistic(FitFunction):
#     @classmethod
#     def names(cls):
#         return ['l', 'k', 'x0']
#
#     @staticmethod
#     def value(x, l, k, x0):
#         """Value of sine at time t"""
#         return l / (1+math.exp(-k*(x-x0)))
#         # 1 = e - e^(-k*(x-x0))
#
#     @staticmethod
#     def jacobian(x_data, l, k, x0):
#         xs = np.atleast_1d(x_data)
#         jacmat = np.zeros((xs.shape[0], 3))
#         for i, x in enumerate(xs):
#             jacmat[i, 0] = 1 / (1+math.exp(-k*(x-x0)))  # dy/dl
#             jacmat[i, 1] = (-l / (1+math.exp(-k*(x-x0)))**2)*(-x*math.exp(-k*(x-x0)))  # dy/dk
#             jacmat[i, 2] = (-l / (1+math.exp(-k*(x-x0)))**2)*(k*math.exp(-k*(x-x0)))  # dy/dx0
#         return jacmat
#
#     @classmethod
#     def autoguess(cls, x, y, hold={}, man_guess={}, man_bounds={}, man_scale={}):
#         g = dict()
#         g['l'] = max(y)
#         # g['k'] = 1
#         # g['x0'] = 0
#         # constrain amplitude, pi_time to be positive, phase to be in range [0, 2*pi], y_min to be positive
#         bounds = ([0, 0, 0],
#                   [np.inf, np.inf, np.inf])
#
#         # default scales
#         x_scale = {
#             'l': 1,
#             'k': 1,
#             'x0': 1
#         }
#
#         # override scales with guesses
#         return cls.autoguess_outputs(g, x_scale, bounds, hold, man_guess, man_bounds, man_scale)


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
            jacmat[i, 1] = amplitude / 2 * np.sin(np.pi * x / pi_time + phase) * (-np.pi * x / (pi_time ** 2))  # dy/dpi_time
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
        g['y_min'] = min(y)
        # constrain amplitude, pi_time to be positive, phase to be in range [0, 2*pi], y_min to be positive
        bounds = ([0, 0, 0, 0],
                  [np.inf, np.inf, 2 * np.pi, np.inf])

        # default scales
        x_scale = {
            'amplitude': 1,
            'phase': 1,
            'pi_time': 1 * us,
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


# instalation instructions for harminv on linux:
# 1. install blas and lapack
#   sudo apt-get install libblas-dev liblapack-dev
# 2. install harminv linux package:
#   sudo apt-get install harminv
# 3. install pharminv python wrapper
#   pip install pharminv
class ExpSine(FitFunction):
    """Wrapper class for fitting to exponentially decaying sine squared"""

    @classmethod
    def names(cls):
        return ['y_min', 'amplitude', 'pi_time', 'phase', 'tau']

    @staticmethod
    def simulation_args():
        return {
            'y_min': 2.5,
            'amplitude': 10,
            'pi_time': 10 * us,
            'phase': 0,
            'tau': 20 * us
        }

    @staticmethod
    def value(x, y_min, amplitude, pi_time, phase, tau):
        """Value of exponential decaying sine squared at x"""

        # f = y_min + (A/2)*(1 - exp[-t/tau]*cos(pi*t/pi_time - phi))

        return y_min + (amplitude) / 2 * (
                1 - np.exp(-x / tau) * np.cos(
            np.pi * x / pi_time - phase
        )
        )

    @staticmethod
    def jacobian(xdata, y_min, amplitude, pi_time, phase, tau):
        """Returns Jacobian matrix of partial derivatives of
        A * sin(2pi*f*t + phi) * exp(-t/tau) + y0, evaluated for all values t
        in tdata, which can be a 1d array or a scalar. Rows are separate values
        of t, columns are partial derivatives w.r.t. different parameters
        """
        xs = np.atleast_1d(xdata)
        jacmat = np.zeros((xs.shape[0], 5))

        for i, x in enumerate(xs):
            # f = y_min + (amplitude/2)B
            B = (
                    1 - np.exp(-x / tau) * np.cos(
                np.pi * x / pi_time - phase
            )
            )
            dtau_B = -(x / tau ** 2) * np.exp(-x / tau) * np.cos(
                np.pi * x / pi_time - phase
            )
            dpitime_B = np.exp(-x / tau) * np.sin(
                np.pi * x / pi_time - phase
            ) * (-np.pi * x / pi_time ** 2)
            dphase_B = -np.exp(-x / tau) * np.sin(
                np.pi * x / pi_time - phase
            )

            dymin_f = 1
            damp_f = B / 2
            dtau_f = (amplitude / 2) * dtau_B
            dphase_f = (amplitude / 2) * dphase_B

            dpitime_f = (amplitude / 2) * dpitime_B

            jacmat[i, 0] = dymin_f  # dy/dy_min
            jacmat[i, 1] = damp_f  # dy/damplitude
            jacmat[i, 2] = dpitime_f  # dy/dpi_time
            jacmat[i, 3] = dphase_f  # dy/dphase
            jacmat[i, 4] = dtau_f  # dy/dtau

        return jacmat

    @staticmethod
    def fallbackguess(x, y):

        amplitude = (np.amax(y) - np.amin(y))
        y_min = min(y)
        y0 = (max(y) - min(y)) / 2
        # yfft= np.split(fft(y - y0), 2)[0] # take FFT, use only positive frequency components
        # don't guess zero frequency, will cause fit to fail
        # pi_time = 0.5*1/(1./(np.amax(x)-np.amin(x))*max(1,np.argmax(np.absolute(yfft))))
        pi_time = tpi_fft(x, y)
        tau = (np.amax(x) - np.amin(x)) / 2.
        phase = 0
        return (amplitude, y_min, pi_time, tau, phase)

    @classmethod
    def autoguess(cls, x, y, hold={}, man_guess={}, man_bounds={}, man_scale={}):
        """Returns automated guesses for fit parameter starting points and
        bounds for parameter search.  Use initial to provide manual guesses
        for values of parameters to override automated guesses. Valid keyword
        names are 'A', 'f', 'tau', 'phi', 'y0'.
        """
        try:
            if 'method' in man_guess and man_guess['method'] == 'harminv':
                import harminv
                # perform harmonic inversion
                print('>> performing harmonic inversion')
                fmin = 0  # default
                fmax = 10000000  # default
                dt = x[1] - x[0]
                if 'fmin' in man_guess:
                    fmin = man_guess['fmin']
                if 'fmax' in man_guess:
                    fmax = man_guess['fmax']
                inversion = harminv.invert(y,
                                           fmin=fmin,
                                           fmax=fmax,
                                           dt=dt)
                print('inversion errors')
                print(inversion.error)
                print('inversion pi times')
                print(0.5 * 1 / inversion.frequency)
                print('inversion taus')
                print(1 / inversion.decay)
                print('inversion amplitudes')
                print(2 * inversion.amplitude)

                # get mode with the smallest error
                i = np.argmin(inversion.error)
                y_min = min(y)
                frequency = abs(inversion.frequency[i])
                pi_time = 0.5 * 1 / frequency
                # amplitude = abs(2*inversion.amplitude[i])
                amplitude = (np.amax(y) - np.amin(y))
                phase = 0  # inversion.phase[i]
                decay_constant = abs(inversion.decay[i])
                tau = 1 / decay_constant
            else:
                print('doing fallback')
                (amplitude, y_min, pi_time, tau, phase) = ExpSine.fallbackguess(x, y)

        # harmonic inversion not installed
        except ImportError:
            (amplitude, y_min, pi_time, tau, phase) = ExpSine.fallbackguess(x, y)

        # if manual guesses are provided, replace autoguesses with manual
        g = {
            'y_min': y_min,
            'amplitude': amplitude,
            'pi_time': pi_time,
            'phase': phase,
            'tau': tau
        }

        # constrain amplitude, pi_time, decay time to be positive
        bounds = ([-np.inf, 0, 0, -np.inf, 0],
                  [np.inf, np.inf, np.inf, np.inf, np.inf])
        x_scale = {
            'y_min': g['y_min'],
            'amplitude': g['amplitude'],
            'pi_time': g['pi_time'],
            'phase': 3,
            'tau': g['tau']
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
            'pi_time': 20 * us
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
            x_scale['pi_time'] = 1 * us
        if abs(g['frequency']) > 0:
            x_scale['frequency'] = abs(g['frequency'])
        else:
            x_scale['frequency'] = 1 * MHz

        return cls.autoguess_outputs(g, x_scale, bounds, hold, man_guess, man_bounds, man_scale)


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

        # estimate b
        # f(x) = Aexp[-b*x0]exp[b*x]+y0 =>
        # f(x2) - f(x1) = df = A exp[-b*x0]*(exp[b*x2] - exp[b*x1]) =>
        # if x3-x2 = x2-x1 =>
        # ratio = df2 / df1 = (exp[b*x3] - exp[b*x2]) / (exp[b*x2] - exp[b*x1]) =>
        #                   = (exp[b*x3] / exp[b*x2]) * ((1 - exp[-b*dx])/(1-exp[-b*dx]))
        #                   = (exp[b*x3] / exp[b*x2])
        # ln(ratio) = b*(x3-x2) = b*dx =>
        # b = ln(ratio)/dx

        xmid = (x[-1] - x[0]) / 2  # middle x
        i = index_at(x, xmid)  # middle index
        ratio = (max(y) - y[i]) / (y[i] - min(y))
        dx = x[-1] - xmid
        b = np.log(ratio) / dx

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
    """Class for fitting to and integrated guassian beam
    """

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


class Lor4thRoot(FitFunction):
    """Class for fitting to the fourth root of a Lorentzian (A * Gamma^2/((x-x0)^2+Gamma^2))**(1/4) + y0
    As defined here Gamma is the HWHM of the Lorentzian.
    """

    @classmethod
    def names(cls):
        """Valid parameter names for this function type, in order for value()
        method arguments"""
        return ['A', 'Gamma', 'x0', 'y0']

    @staticmethod
    def value(x, A, Gamma, x0, y0):
        """Value of Lorentzian at x"""
        return (A * Gamma ** 0.5 / ((x - x0) ** 2 + Gamma ** 2)) ** 0.25 + y0

    @staticmethod
    def jacobian(xdata, A, Gamma, x0, y0):
        """Returns Jacobian matrix of partial derivatives of
        (A * Gamma ** 0.5 / ((x - x0) ** 2 + Gamma ** 2))**(0.25) + y0, evaluated for all values x
        in xdata, which can be a 1d array or a scalar. Rows are separate values
        of x, columns are partial derivatives w.r.t. different parameters
        """
        xs = np.atleast_1d(xdata)
        jacmat = np.zeros((xs.shape[0], 4))
        for i, x in enumerate(xs):
            jacmat[i, 0] = (Gamma ** 0.5) / (((x - x0) ** 0.5 + Gamma ** 2) ** 0.25)  # dy/dA
            jacmat[i, 1] = (A * (x - x0) ** 2) / (2 * Gamma ** 0.5 * ((x - x0) ** 2 + Gamma ** 2) ** 1.25)  # dy/dGamma
            jacmat[i, 2] = (A * (x - x0) * Gamma ** 0.5) / (2 * ((x - x0) ** 2 + Gamma ** 2) ** 1.25)  # dy/dx0
            jacmat[i, 3] = 1.  # dy/dy0

        return jacmat

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

        # pick a range that avoids edges to avoid accidentally guessing
        # edges as a peak
        xfrac = 0.1
        xmin = np.amin(x)
        xmax = np.amax(x)
        xlo = (xmax - xmin) * xfrac + xmin
        xhi = xmax - (xmax - xmin) * xfrac

        # construct autoguess values
        g = {}
        g['A'] = amax - mid if up else amin - mid  # peak to midline
        g['Gamma'] = (np.amax(x) - np.amin(x)) / 6.
        # guess max or min values for peak center, unless too close to the edge
        # in which case use the middle value
        if up and xlo < x[np.argmax(y)] < xhi:
            g['x0'] = x[np.argmax(y)]
        elif not up and xlo < x[np.argmin(y)] < xhi:
            g['x0'] = x[np.argmin(y)]
        else:
            g['x0'] = (xmax + xmin) / 2.
        g['y0'] = mid

        # default bounds: constrain Gamma to be positive
        bounds = ([-np.inf, 0., -np.inf, -np.inf], [np.inf, np.inf, np.inf,
                                                    np.inf])

        # generate rough natural scale values
        xsc = {}
        xsc['A'] = np.absolute(g['A'])
        xsc['Gamma'] = g['Gamma']
        xsc['x0'] = max(np.absolute(xmax), np.absolute(xmin))
        xsc['y0'] = np.absolute(g['A'])

        return cls.autoguess_outputs(g, xsc, bounds, hold, man_guess,
                                     man_bounds, man_scale)


class Shim(FitFunction):

    @classmethod
    def names(cls):
        """Valid parameter names for this function type, in order for value() method arguments"""
        return ['sens', 'x0', 'y_min', 'A']

    @staticmethod
    def value(x, sens, x0, y_min, A):
        """Value of fluorescence at x
        V_dc: DC shim voltage.
        omega_l: Frequency of laser used to excite ion.
        omega_a: Frequency of atomic transition.
        omega_rf: Frequency of trap RF.
        n_max: Max number of terms in Bessel function sum.
        gamma: Line width of transition.
        sens: "Sensitivity" of ion to DC shim voltage.  This term includes all constants that multiply V_dc to give beta.
        x0: Shim offset.
        y_min: Minimum counts.
        A: Multiplied by theoretical amplitude to give difference between max and min counts.
        """
        vdc = x
        omega_a = 0
        omega_l = 0
        # stylus trap parameters (hard coded for now)
        omega_rf = (64.406 * 10 ** 6) / (41.3 * 10 ** 6)
        gamma = 1
        n_max = 2
        y = 0.0
        beta = sens * (vdc - x0)
        for n in range(-n_max, n_max + 1, 1):
            y += scipy.special.jv(n, beta) ** 2 / ((omega_a - omega_l + n * omega_rf) ** 2 + (0.5 * gamma) ** 2)
        y = y_min + A * y
        return y

    @staticmethod
    def jacobian(xdata, sens, x0, y_min, A):
        omega_a = 0
        omega_l = 0
        # stylus trap parameters (hard coded for now)
        omega_rf = (64.406 * 10 ** 6) / (41.3 * 10 ** 6)
        gamma = 1
        n_max = 2

        # Below is hard coded for
        #   1. omega_a = 0
        #   2. omega_l = 0
        #   3. n_max = 2
        xs = np.atleast_1d(xdata)
        jacmat = np.zeros((xs.shape[0], 4))

        for i, x in enumerate(xs):
            vdc = x
            j0 = scipy.special.jv(0, sens * (vdc - x0))
            j1 = scipy.special.jv(1, sens * (vdc - x0))
            j2 = scipy.special.jv(2, sens * (vdc - x0))
            j3 = scipy.special.jv(3, sens * (vdc - x0))
            dy_dvdc = (-1 / (omega_rf ** 6 + 20 * gamma ** 4 * omega_rf ** 2 + 64 * gamma ** 2 * omega_rf ** 4)) * (
                    8 * A * sens * (
                    4 * omega_rf ** 2 * (gamma ** 2 + 16 * omega_rf ** 2) * j0 * j1 +
                    gamma ** 2 * (
                            12 * omega_rf ** 2 * j1 + (gamma ** 2 + 4 * omega_rf ** 2) * j3
                    ) * j2
            )
            )

            jacmat[i, 0] = dy_dvdc  # dy/dvdc
            jacmat[i, 1] = dy_dvdc * ((vdc - x0) / sens)  # dy/dsens
            jacmat[i, 2] = dy_dvdc * -1  # dy/dx0
            jacmat[i, 3] = 1  # dy/ymin
            jacmat[i, 4] = (4 * j0 ** 2) / gamma ** 2 \
                           + (8 * j1 ** 2) / (gamma ** 2 + 4 * omega_rf ** 2) \
                           + (8 * j2 ** 2) / (gamma ** 2 + 16 * omega_rf ** 2)  # dy/dA
        return jacmat

    @classmethod
    def autoguess(cls, x, y, hold={}, man_guess={}, man_bounds={},
                  man_scale={}):
        """Returns automated guesses for fit parameter starting points and
        bounds for parameter search.  Manual guesses, bounds, and scales
        provided in dictionaries will override automatic values unless
        named parameter is being held. Valid keyword names are in cls.names()
        """

        # construct autoguess values
        guess = {
            'sens': 11,
            'x0': x_at_max_y(x, y),
            'y_min': 1.4,
            'A': 1.4
        }

        # default bounds
        bounds = ([0, -np.inf, 0, -np.inf], [np.inf, np.inf, np.inf, np.inf])

        # generate rough natural scale values
        scales = {
            'sens': 1,
            'x0': 1,
            'y_min': 1,
            'A': 1
        }
        return cls.autoguess_outputs(guess, scales, bounds, hold, man_guess,
                                     man_bounds, man_scale)


class IonPosFit(FitFunction):
    """Sin of a gaussian for fitting to the shape of an ion position scan"""
    @classmethod
    def names(cls):
        """Valid parameter names for this function type, in order for value()
        method arguments"""
        return ['A', 'alpha', 'w', 'x0', 'y0']

    @staticmethod
    def value(x, A, alpha, w, x0, y0):
        # added on kyle-687stylab as of 8/13/2020
        return A*np.cos(alpha*(np.pi/2)*np.exp(-2*(x-x0)**2/w**2)) + y0
        # original
        #return A*cos(alpha*(np.pi/2)*exp(-2*(x-x0)**2/w**2)) + y0

    @staticmethod
    def jacobian(xdata, A, alpha, w, x0, y0):
        """Returns Jacobian matrix of partial derivatives of
        A * exp(-(x-x0)^2/(2*sigma^2)) + y0, evaluated for all values x
        in xdata, which can be a 1d array or a scalar. Rows are separate values
        of x, columns are partial derivatives w.r.t. different parameters
        """
        xs = np.atleast_1d(xdata)
        jacmat = np.zeros((xs.shape[0], 5))
        for i, x in enumerate(xs):
            jacmat[i, 0] = np.cos(alpha*(np.pi/2)*np.exp(-2*(x-x0)**2/w**2))  # dy/dA
            jacmat[i, 1] = -A*np.exp(-2*(x-x0)**2/w**2)*np.sin(alpha*(np.pi/2)*np.exp(-2*(x-x0)**2/w**2))  # dy/dalpha
            jacmat[i, 2] = -4*A*np.exp(-2*(x-x0)**2/w**2)*(x-x0)**2*alpha*(np.pi/2)*np.sin(alpha*(np.pi/2)*np.exp(-2*(x-x0)**2/w**2)) / w**3  # dy/dw
            jacmat[i, 3] = -4*A*np.exp(-2*(x-x0)**2/w**2)*(x-x0)*alpha*(np.pi/2)*np.sin(alpha*(np.pi/2)*np.exp(-2*(x-x0)**2/w**2)) / w**2  # dy/dx0
            jacmat[i, 4] = 1  # dy/dy0
        return jacmat

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
        up = True if (p80-mid > mid-p20) else False  # pointing up or down?

        # pick a range near edges to avoid accidentally guessing as a peak
        xfrac = 0.1
        xmin = np.amin(x)
        xmax = np.amax(x)
        xlo = (xmax-xmin)*xfrac+xmin
        xhi = xmax-(xmax-xmin)*xfrac

        # construct autoguess values
        g = {}
        g['A'] = amax-mid if up else amin-mid  # peak to midline
        g['alpha'] = 0.5
        g['w'] = (np.amax(x)-np.amin(x))/6.
        # guess max or min values for peak center, unless too close to the edge
        # in which case use the middle value
        if up and xlo < x[np.argmax(y)] < xhi:
            g['x0'] = x[np.argmax(y)]
        elif not up and xlo < x[np.argmin(y)] < xhi:
            g['x0'] = x[np.argmin(y)]
        else:
            g['x0'] = (xmax+xmin)/2.
        g['y0'] = mid

        # default bounds: constrain sigma to be positive
        bounds = ([-np.inf, -np.inf, -np.inf, -np.inf, -np.inf], [np.inf, np.inf, np.inf, np.inf, np.inf])

        # generate rough natural scale values
        xsc = {}
        xsc['A'] = 1
        xsc['alpha'] = 0.1
        xsc['w'] = 1e-6
        xsc['x0'] = 1e-6
        xsc['y0'] = 1

        return cls.autoguess_outputs(g, xsc, bounds, hold, man_guess,
                                     man_bounds, man_scale)


class TrapSampleDistFit(FitFunction):
    """Fit function for trap to sample distance fit.  This model assumes a reference frame that is stationary
    with respect to the laser beam.  i.e. in a frame where the trap and sample are moving instead of the beam."""

    @classmethod
    def names(cls):
        return ['P0', 'w', 'xtl', 'xtr', 'ytt', 'h', 'xsl', 'xsr', 'hs', 'Pb']

    @staticmethod
    def value(x, P0, w, xtl, xtr, ytt, h, xsl, xsr, hs, Pb):
        """
        w: beam radius
        xtl: x position of the left side of the trap
        xtr: x position of the right side of the trap
        ytt: y position of the top surface of the trap
        h: height of sample above trap (y distance from top of trap to bottom of sample)
        xsl: x position of the left side of the sample
        xsr: x position of the right side of the sample
        hs: height of sample above its bottom surface
        """
        # fraction of the beam power blocked by the trap
        Ft = 0.25 * (sp.erf(2 ** .5 * xtr / w) - sp.erf(2 ** .5 * xtl / w)) * \
             (
                1 + sp.erf(2 ** .5 * (x - ytt) / w)
             )

        # fraction of the beam power blocked by the sample
        Fs = 0.25 * (sp.erf(2 ** .5 * xsr / w) - sp.erf(2 ** .5 * xsl / w)) * \
             (
                sp.erf(2 ** .5 * ((ytt - h) - x) / w)
                -
                sp.erf(2 ** .5 * ((ytt - h - hs) - x) / w)
             )

        return P0 * (1 - Ft - Fs) + Pb

    @classmethod
    def autoguess(cls, x, y, hold={}, man_guess={}, man_bounds={},
                  man_scale={}):
        """Returns automated guesses for fit parameter starting points and
        bounds for parameter search.  Manual guesses, bounds, and scales
        provided in dictionaries will override automatic values unless
        named parameter is being held. Valid keyword names are in cls.names()
        """

        y = np.asarray(y)
        mid_y = (max(y) - min(y))/2 + min(y)
        # better guess for ytt and h
        first = False
        h = 150e-6
        ytt = 0.8e-3
        for i in range(len(y)):
            ii = len(y) - 1 - i
            if not first and y[ii] > mid_y:
                i_tt = ii
                # linear interpolate to find best x
                perc = (mid_y - y[ii+1])/(y[ii] - y[ii+1])
                ytt = x[ii] + perc * (x[ii+1] - x[ii])
                first = True
            if first and y[ii] < mid_y:
                # linear interpolate to find best x
                perc = (mid_y - y[ii]) / (y[ii+1] - y[ii])
                yst = x[ii] + perc * (x[ii + 1] - x[ii])
                h = ytt - yst
                break

        g = {'P0': max(y) - min(y),
             'w': 39e-6,
             'xtl': -60e-6,
             'xtr': 60e-6,
             'ytt': ytt,
             'h': h,
             'xsl': -500e-6,
             'xsr': 500e-6,
             'hs': 1,
             'Pb': min(y)}

        bounds = ([-np.inf, -np.inf, -np.inf, -np.inf, -np.inf, -np.inf, -np.inf, -np.inf, -np.inf, -np.inf],
                  [np.inf, np.inf, np.inf, np.inf, np.inf, np.inf, np.inf, np.inf, np.inf, np.inf])


        # generate rough natural scale values
        xsc = {}
        xsc['P0'] = 10e-9
        xsc['w'] = 10e-6
        xsc['xtl'] = 100e-6
        xsc['xtr'] = 100e-6
        xsc['ytt'] = 1e-3
        xsc['h'] = 100e-6
        xsc['xsl'] = 500e-6
        xsc['xsr'] = 500e-6
        xsc['hs'] = 1
        xsc['Pb'] = 1e-9
        return cls.autoguess_outputs(g, xsc, bounds, hold, man_guess, man_bounds, man_scale)


class RabiSpectrum(FitFunction):
    @classmethod
    def names(cls):
        return ['omega', 't', 'y0']

    @staticmethod
    def value(x, omega, t, y0):
        return omega**2/(omega**2 + x**2) * np.sin(((omega**2 + x**2)**.5/2)*t)**2 + y0

    @staticmethod
    def jacobian(xdata, omega, t, y0):
        xs = np.atleast_1d(xdata)
        jacmat = np.zeros((xs.shape[0], 3))
        for i, x in enumerate(xs):
            # dy/domega
            jacmat[i, 0] = omega * np.sin((t * sqrt(omega ** 2 + x ** 2)) / 2.) * \
                ((omega ** 2 * t * np.cos((t * sqrt(omega ** 2 + x ** 2)) / 2)) / (omega ** 2 + x ** 2) ** 1.5 +
                (2 * x ** 2 * np.sin((t * sqrt(omega ** 2 + x ** 2)) / 2)) / (omega ** 2 + x ** 2) ** 2)

            # dy/dt
            jacmat[i, 1] = (omega ** 2 * np.sin(t * sqrt(omega ** 2 + x ** 2))) / (2 * sqrt(omega ** 2 + x ** 2))

            # dy/dy0
            jacmat[i, 2] = 1
        return jacmat

    @classmethod
    def autoguess(cls, x, y, hold={}, man_guess={}, man_bounds={},
                  man_scale={}):
        # auto guess
        g = {
            'omega': 2*np.pi/(20*us),
            't': 10*us
        }

        # bounds
        bounds = ([0, 0, 0], [np.inf, np.inf, np.inf])

        # rough natural scale values
        xsc = {}
        xsc['omega'] = 2*np.pi/(20*us)
        xsc['t'] = 10*us
        xsc['y0'] = 1

        return cls.autoguess_outputs(g, xsc, bounds, hold, man_guess,
                                     man_bounds, man_scale)


RamanFlopPreCalc = None
class RamanFlop2ModesFast(FitFunction):

    @classmethod
    def pre_calc(cls, etas, ts, carr_pitime, alphas=[0, 0], nstarts=[0, 0], nends=[100, 100]):
        """Pre calculate values that don't change when fit parameters are adjusted to speed up fit times."""
        global RamanFlopPreCalc

        RamanFlopPreCalc = {}

        # Fock states to consider for each mode
        RamanFlopPreCalc['mode_ns'] = fock_states_nd(
            nstarts=nstarts,
            nends=nends
        )

        # Rabi rates of each mode : omega[mode, n]
        RamanFlopPreCalc['mode_omegas'] = rabi_rate_fast_nd(1,
           etas=etas,
           ns=RamanFlopPreCalc['mode_ns'],
           alphas=alphas  # carrier transition
        )

        # Unitless Rabi rate of each Fock state |l,m,n> in the tensor product space M1 x M2 x M3
        RamanFlopPreCalc['Omega_lmn'] = kron2_flat(RamanFlopPreCalc['mode_omegas'][0],
                                                   RamanFlopPreCalc['mode_omegas'][1])

        i_lmn = 0
        RamanFlopPreCalc['Sin2_lmn'] = np.full((len(RamanFlopPreCalc['Omega_lmn']), len(ts)), np.nan)
        for Omega_lmn in RamanFlopPreCalc['Omega_lmn']:
            RamanFlopPreCalc['Sin2_lmn'][i_lmn] = np.sin(0.5 * np.pi / carr_pitime * Omega_lmn * ts) ** 2
            i_lmn += 1

        return RamanFlopPreCalc

    @classmethod
    def names(cls):
        return ['A', 'y0', 'nbar1', 'nbar2']

    @staticmethod
    def value(t, A, y0, nbar1, nbar2):

        # Thermal distributions of each mode : prob[mode, n]
        mode_dists = thermal_dist_nd(
            nbars=[nbar1, nbar2],
            ns=RamanFlopPreCalc['mode_ns']
        )
        print(len(t), A, y0, nbar1, nbar2)
        # Probability of each Fock state |l,m,n> in the tensor product space M1 x M2 x M3
        P_lmn = kron2_flat(mode_dists[0], mode_dists[1])

        return y0 + A*np.sum(P_lmn * RamanFlopPreCalc['Sin2_lmn'].T, axis=1)

    @classmethod
    def autoguess(cls, x, y, hold={}, man_guess={}, man_bounds={}, man_scale={}):
        """Returns automated guesses for fit parameter starting points and
        bounds for parameter search.  Use initial to provide manual guesses
        for values of parameters to override automated guesses. Valid keyword
        names are 'A', 'f', 'phi', 'y0'.
        """
        g = dict()
        g['A'] = 16
        g['y0'] = 1.5
        g['nbar1'] = 15
        g['nbar2'] = 15
        # constrain amplitude, pi_time to be positive, phase to be in range [0, 2*pi], y_min to be positive
        bounds = ([0, 0, 0, 0],
                  [np.inf, np.inf, np.inf, np.inf])

        # default scales
        x_scale = {
            'A': 10,
            'y0': 1,
            'nbar1': 10,
            'nbar2': 10
        }
        return cls.autoguess_outputs(g, x_scale, bounds, hold, man_guess, man_bounds, man_scale)


RamanFlopPreCalc = None
class RamanFlop2Modes(FitFunction):

    @classmethod
    def pre_calc(cls, etas, ts, alphas=[0, 0, 0], nstarts=[0, 0, 0], nends=[100, 100, 100]):
        """Pre calculate values that don't change when fit parameters are adjusted to speed up fit times."""
        global RamanFlopPreCalc

        RamanFlopPreCalc = {}

        # Fock states to consider for each mode
        RamanFlopPreCalc['mode_ns'] = fock_states_nd(
            nstarts=nstarts,
            nends=nends
        )

        # Rabi rates of each mode : omega[mode, n]
        RamanFlopPreCalc['mode_omegas'] = rabi_rate_fast_nd(1,
           etas=etas,
           ns=RamanFlopPreCalc['mode_ns'],
           alphas=alphas  # carrier transition
        )

        # Unitless Rabi rate of each Fock state |l,m,n> in the tensor product space M1 x M2 x M3
        RamanFlopPreCalc['Omega_lmn'] = kron2_flat(RamanFlopPreCalc['mode_omegas'][0],
                                                   RamanFlopPreCalc['mode_omegas'][1])

        return RamanFlopPreCalc

    @classmethod
    def names(cls):
        return ['A', 'y0', 'nbar1', 'nbar2', 'carr_pitime']

    @staticmethod
    def value(t, A, y0, nbar1, nbar2, carr_pitime):
        i_lmn = 0
        Sin2_lmn = np.full((len(RamanFlopPreCalc['Omega_lmn']), len(t)), np.nan)
        for Omega_lmn in RamanFlopPreCalc['Omega_lmn']:
            Sin2_lmn[i_lmn] = np.sin(0.5 * np.pi / carr_pitime * Omega_lmn * t) ** 2
            i_lmn += 1

        # Thermal distributions of each mode : prob[mode, n]
        mode_dists = thermal_dist_nd(
            nbars=[nbar1, nbar2],
            ns=RamanFlopPreCalc['mode_ns']
        )
        # Probability of each Fock state |l,m,n> in the tensor product space M1 x M2 x M3
        P_lmn = kron2_flat(mode_dists[0], mode_dists[1])

        return y0 + A*np.sum(P_lmn * Sin2_lmn.T, axis=1)

    @classmethod
    def autoguess(cls, x, y, hold={}, man_guess={}, man_bounds={}, man_scale={}):
        """Returns automated guesses for fit parameter starting points and
        bounds for parameter search.  Use initial to provide manual guesses
        for values of parameters to override automated guesses. Valid keyword
        names are 'A', 'f', 'phi', 'y0'.
        """
        g = dict()
        g['A'] = 16
        g['y0'] = 1.5
        g['nbar1'] = 15
        g['nbar2'] = 15
        g['carr_pitime'] = 5*us
        # constrain amplitude, pi_time to be positive, phase to be in range [0, 2*pi], y_min to be positive
        bounds = ([0, 0, 0, 0, 0],
                  [np.inf, np.inf, np.inf, np.inf, np.inf])

        # default scales
        x_scale = {
            'A': 10,
            'y0': 1,
            'nbar1': 10,
            'nbar2': 10,
            'carr_pitime': us
        }
        return cls.autoguess_outputs(g, x_scale, bounds, hold, man_guess, man_bounds, man_scale)



class RamanFlop1Mode(FitFunction):

    @classmethod
    def pre_calc(cls, eta, alpha=0, nstart=0, nend=200):
        """Pre calculate values that don't change when fit parameters are adjusted to speed up fit times."""
        global RamanFlopPreCalc

        RamanFlopPreCalc = {}

        # Fock states to consider for each mode
        RamanFlopPreCalc['mode_ns'] = fock_states(
            nstart=nstart,
            nend=nend
        )

        # Rabi rates of each mode : omega[mode, n]
        RamanFlopPreCalc['Omega_n'] = rabi_rate_fast(1,
           eta=eta,
           n=RamanFlopPreCalc['mode_ns'],
           alpha=alpha  # carrier transition
        )
        return RamanFlopPreCalc

    @classmethod
    def names(cls):
        return ['A', 'y0', 'nbar', 'carr_pitime']

    @staticmethod
    def value(t, A, y0, nbar, carr_pitime):
        i_n = 0
        Sin2_n = np.full((len(RamanFlopPreCalc['Omega_n']), len(t)), np.nan)
        for Omega_n in RamanFlopPreCalc['Omega_n']:
            Sin2_n[i_n] = np.sin(0.5 * np.pi / carr_pitime * Omega_n * t) ** 2
            i_n += 1

        # Thermal distributions of each mode : prob[mode, n]
        mode_dist = thermal_dist(
            nbar=nbar,
            ns=RamanFlopPreCalc['mode_ns']
        )
        # Probability of each Fock state |l,m,n> in the tensor product space M1 x M2 x M3
        P = mode_dist
        return y0 + A*np.sum(P * Sin2_n.T, axis=1)

    @classmethod
    def autoguess(cls, x, y, hold={}, man_guess={}, man_bounds={}, man_scale={}):
        """Returns automated guesses for fit parameter starting points and
        bounds for parameter search.  Use initial to provide manual guesses
        for values of parameters to override automated guesses. Valid keyword
        names are 'A', 'f', 'phi', 'y0'.
        """
        g = dict()
        g['A'] = 16
        g['y0'] = 1.5
        g['nbar'] = 15
        g['carr_pitime'] = 5*us
        # constrain amplitude, pi_time to be positive, phase to be in range [0, 2*pi], y_min to be positive
        bounds = ([0, 0, 0, 0],
                  [np.inf, np.inf, np.inf, np.inf])

        # default scales
        x_scale = {
            'A': 10,
            'y0': 1,
            'nbar': 10,
            'carr_pitime': us
        }
        return cls.autoguess_outputs(g, x_scale, bounds, hold, man_guess, man_bounds, man_scale)