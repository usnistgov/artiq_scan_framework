# Example 12: Time & frequency scans
#
# How to create scan over times, frequencies, or both times and frequencies (e.g. atomic transitions)
from artiq.experiment import *
from scan_framework import *
from math import sin, pi

# Custom fit function to fit pi times
class SineSquared(curvefits.FitFunction):
    @classmethod
    def names(cls):
        """Valid parameter names for this function type, in order for value()
        method arguments"""
        return ['A', 'pi_time', 'phi', 'y0']

    @staticmethod
    def value(t, A, pi_time, phi, y0):
        """Value of sine at time t"""
        return (A*np.sin(2*np.pi*t/(4*pi_time)+phi)**2+y0)

    @classmethod
    def autoguess(cls, t, y, hold={}, man_guess={}, man_bounds={},
                  man_scale={}):
        """Returns automated guesses for fit parameter starting points and
        bounds for parameter search.  Manual guesses, bounds, and scales
        provided in dictionaries will override automatic values unless
        named parameter is being held. Valid keyword names are in cls.names()
        """
        # construct autoguess values
        g = {}
        g['A'] = (np.amax(y) - np.amin(y)) / 2
        g['y0'] = (np.amax(y) + np.amin(y)) / 2
        # strip DC level, take FFT, use only positive frequency components
        yfft = fft(y - np.mean(y))[0:len(y) // 2]
        # don't guess zero frequency, will cause fit to fail
        g['pi_time'] = ((np.amax(t) - np.amin(t))
                  / max(1, np.argmax(np.absolute(yfft))))/2
        g['phi'] = 1.5 if y[0] > g['y0'] else 4.7

        # default bounds: constrain A, f to be positive
        bounds = ([0., 0., -np.inf, -np.inf], [np.inf, np.inf, np.inf,
                                               np.inf])

        # generate rough natural scale values
        xsc = {}
        xsc['A'] = g['A']
        xsc['pi_time'] = g['pi_time']
        xsc['phi'] = 3.1
        xsc['y0'] = g['A']

        return cls.autoguess_outputs(g, xsc, bounds, hold, man_guess,
                                     man_bounds, man_scale)


class Example12TimeScan(Scan1D, TimeScan, EnvExperiment):
    run_on_core = False

    def build(self):
        super().build()

        # 1. `scan_arguments()` additionally creates a range of times to scan over
        self.scan_arguments(
            times={
                'start': 0,         # default is 'start': 0
                'stop': 50 * us,    # default is 'stop': 100*us
                # Default values will be used if a settings is omitted.
                #'npoints': 50,      # default is 'npoints': 50
                'unit': 'us',       # default is 'unit': 'us'
                'scale': 1 * us     # default is 'scale': 1*us
            }
        )

    # 2. The get_scan_points() callback does not need to be implemented.

    def prepare(self):
        self.model = Example12TimeModel(self)
        self.register_model(self.model, measurement=True, fit=True)

    def measure(self, time):
        return int(10*sin(time*1.5*2*pi/(100*us))**2)


class Example12TimeModel(TimeModel):
    namespace = "example_12"
    fit_function = SineSquared
    plot_title = 'Example 12'

    # The fitted pi time will be persisted to the datasets when either 'Fit and Save', or 'Fit Only and Save'
    # is selected in the GUI.
    main_fit = 'pi_time'

    # TimeModel classes format the plot x axis in microseconds by default
    #x_scale = us  # <-- set by default in TimeModel
    #x_units = 'us'  # <-- set by default in TimeModel


