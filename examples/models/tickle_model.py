from artiq.experiment import *
from scan_framework import *
import scan_framework.analysis.curvefits as curvefits


class SincInv(curvefits.FitFunction):

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


class TickleModel(Model):
    namespace = "tickle.%mode"  #: Dataset namespace
    default_fallback = True

    def build_datasets(self):
        """Create missing tickle datasets"""

        # code isn't falling back to defaults for these
        self.create('frequency', 500 * MHz)
        self.create('mode_1.defaults.frequency', 500 * MHz)
        self.create('mode_2.defaults.frequency', 500 * MHz)


class TickleScanModel(TickleModel, FreqModel):
    """Models ion interaction with the trap tickle."""
    fit_function = SincInv
    main_fit = 'frequency'
    default_fallback = True

    @property
    def simulation_args(self):
        auto_track = hasattr(self.scan, 'auto_track') and self.scan.auto_track
        if self.mode == 'mode_1':
            return {
                'y_min': 1.5,
                'y_max': 10,
                'pi_time': 1*us,
                'frequency': self.scan.frequency_center if auto_track else 1*MHz
            }
        if self.mode == 'mode_2':
            return {
                'y_min': 1.5,
                'y_max': 10,
                'pi_time': 1*us,
                'frequency': self.scan.frequency_center if auto_track else 2*MHz
            }

    @property
    def pre_validators(self):
        return {
            "y_data": {
                "height": {
                    'min_height': 1
                }
            }
        }

    @property
    def strong_validators(self):
        """Scan is halted with a BadFit exception when these validations fail."""
        return {
            "params.y_max": {
                "validate_fit_height": {
                    "min_height": 1.5
                },
            },
            "params.frequency": {
                "between": {
                    "min_": self.scan.min_point - self.tick,
                    "max_": self.scan.max_point + self.tick
                }
            }
        }

    def validate_fit_height(self, field, y_max, min_height):
        """Validates height of y_max above y_min"""
        y_min = self.fit.fitresults['y_min']
        if y_max - y_min >= min_height:
            return True
        else:
            self.validation_errors[field] = "Fitted amplitude of {0} less than minimum " \
                                            "amplitude for tickle fits of {1}" .format(round(y_max-y_min, 1), min_height)
            return False

    # plots
    @property
    def plot_title(self):
        return "Tickle"



def x_at_min_y(xdata, ydata):
    """Returns the xdata value at which the minimum ydata value occurs
    xdata: numpy array
    ydata: numpy array
    """
    return xdata[np.argmin(ydata)]


def tpi_fwhm(xdata, ydata, inverse=False):
    """Estimates pi time from the full width half max of ydata"""
    return (sqrt(5) / 2) * (1 / fwhm(xdata, ydata, inv=inverse))


def fwhm(xdata, ydata, inv=False):
    # calc half-widths
    hwhm_left = hwhm(xdata, ydata, side='left', inv=inv)
    hwhm_right = hwhm(xdata, ydata, side='right', inv=inv)

    # fwhm
    return hwhm_left + hwhm_right


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


def halfmax(data):
    """Estimate the half max value of the y-data contained in data"""
    return .5 * (max(data) - min(data)) + min(data)

