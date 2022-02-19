# Example 11: Fit validations
#
# How to prevent saving data from bad fits using fit validations.
#
# In this example the default arguments produce a fit that passes all validations.
# Adjusting the 'Validation' and 'Simulation' arguments will result in fits that do not pass
# validation.
from artiq.experiment import *
from scan_framework import *
import random
from math import pi


class Example11Scan(Scan1D, FreqScan, EnvExperiment):
    run_on_core = False

    def build(self):
        super().build()

        # simulation arguments
        self.setattr_argument('transition_frequency', NumberValue(
            default=1 * GHz, step=0.1 * MHz, unit='GHz', scale=GHz, ndecimals=5), group='Simulation')
        self.setattr_argument('pi_time', NumberValue(
            default=10 * us, step=1 * us, unit='us', scale=us, ndecimals=1), group='Simulation')
        self.frequency_center = self.transition_frequency
        self.pulse_time = self.pi_time

        # validation arguments
        self.setattr_argument('disable_validations', BooleanValue(default=False), group='Validation')
        self.setattr_argument('min_height', NumberValue(
            default=9), group='Validation')
        self.setattr_argument('min_pi_time', NumberValue(
            default=9 * us, scale=us, unit='us'), group='Validation')
        self.setattr_argument('max_pi_time', NumberValue(
            default=11 * us, scale=us, unit='us'), group='Validation')
        self.setattr_argument('max_x0', NumberValue(
            default=1.0001 * GHz, scale=GHz, unit='GHz', ndecimals=6, step=0.1 * MHz), group='Validation')
        self.setattr_argument('min_x0', NumberValue(
            default=0.9999 * GHz, scale=GHz, unit='GHz', ndecimals=6, step=0.1 * MHz), group='Validation')

        self.scan_arguments(frequencies={'start': -0.2*MHz, 'stop': 0.2*MHz})

    def prepare(self):
        self._x_offset = self.transition_frequency
        model = Example11Model(self)

        # 1. Validations can be disabled via the `disable_validations` attribute of the ScanModel that is performing the
        # fits.
        model.disable_validations = self.disable_validations
        self.register_model(model, measurement=True, fit=True)

    def measure(self, frequency):
        pmt_counts = RabiSpectrum.value(frequency, 10, 2*pi/(20*us), self.frequency_center, self.pulse_time, 0) + random.random()
        return pmt_counts


class Example11Model(TimeFreqModel):

    x_label = 'Frequency'
    x_scale = GHz
    x_units = 'GHz'
    y_label = 'PMT Counts'

    # 2. When the fit passes pre-validation and strong-validation, the fitted 'x0' parameter
    # will be broadcast and persisted to the example_11.x0 dataset in the dashboard.
    main_fit = 'x0'

    def build(self, bind=True, **kwargs):
        self.namespace = "example_11"
        self.fit_function = RabiSpectrum
        super().build(bind, **kwargs)

    # 3. Pre-validators decide if the data is good enough to fit.
    #   If they fail, a fit is not performed
    @property
    def pre_validators(self):
        return {
            # pre-validate the y-values being fit to the fit function, i.e. the mean values at each scan point
            "y_data": {
                # Use of the built-in validator, `validate_height`
                "height": {
                    # We required that the height of the data be at least this large.
                    'min_height': self._scan.min_height
                }
            }
        }

    # 4. Strong-validators examine fitted values after a fit has been performed.
    #    If they fail, fit parameters are not saved (i.e not broadcast and persisted).
    @property
    def strong_validators(self):
        validators = {
            "x0": {
                # Custom functions can be defined to perform validations.
                # This validation rule uses the `validate_x0` method defined below
                "validate_x0": {
                    "max_x0": self._scan.max_x0,
                    "min_x0": self._scan.min_x0
                },
            }
        }
        return validators

    # 5. Soft-validators examine fitted values after a fit has been performed.
    #    If they fail, a warning message is printed but fit parameters *are* saved (i.e they are broadcast and persisted).
    @property
    def validators(self):
        return {
            "omega": {
                # Use of the built-in validator `validate_between`
                "between": {
                    "max_": 2 * pi / (2 * self._scan.min_pi_time),
                    "min_": 2 * pi / (2 * self._scan.max_pi_time)
                }
            }
        }

    def validate_x0(self, field, x0, min_x0, max_x0):
        x0 = self.fit.fitresults['x0']
        if min_x0 < x0 < max_x0:
            return True
        else:
            self.validation_errors[field] = "The fitted x0 ({:0.6f} GHz) is not in an acceptable range of ({:0.6f} GHz, {:0.6f} GHz)." .format(x0/GHz, min_x0/GHz, max_x0/GHz)
            return False


class RabiSpectrum(curvefits.FitFunction):
    @classmethod
    def names(cls):
        return ['A', 'omega', 'x0', 't', 'y0']

    @staticmethod
    def value(x, A, omega, x0, t, y0):
        """
        x: Frequency of applied field
        t: Pulse time in seconds
        omega: Rabi frequency in Hz,
        A: Maximum counts (less background)
        y0: Background counts
        """
        return A * omega**2 / (omega**2 + (2*pi*(x - x0))**2) \
               * \
               np.sin(
                   (
                        (omega**2 + (2*pi*(x - x0))**2)**.5 / 2
                   ) * t
               )**2 \
               + y0

    @staticmethod
    def jacobian(xdata, A, omega, x0, t, y0):
        xs = np.atleast_1d(xdata)
        jacmat = np.zeros((xs.shape[0], 4))
        for i, x in enumerate(xs):
            # dy/dA
            jacmat[i, 0] = \
                (
                    omega**2 * np.sin(
                        (t*np.sqrt(omega**2 + (2*pi*x - 2*pi*x0)**2))/-2.
                    )**2
                ) / (
                omega**2 + (omega - 2*pi*x0)**2
                )

            # dy/domega
            jacmat[i, 1] = \
                (
                    A * omega * (
                        2 * pi * x0 * (omega - 2 * pi * x0) *
                        (
                            -1 + np.cos(t * np.sqrt(omega ** 2 + (2 * pi * x - 2 * pi * x0) ** 2))
                        )
                        +
                        (
                            omega ** 2 * t * (omega ** 2 - 2 * omega * pi * x0 + 2 * pi ** 2 * x0 ** 2) * np.sin(
                                t * np.sqrt(omega ** 2 + (2 * pi * x - 2 * pi * x0) ** 2)
                            )
                        )
                        /
                        np.sqrt(omega ** 2 + (2 * pi * x - 2 * pi * x0) ** 2)
                    )
                ) / (
                        4. * (omega ** 2 - 2 * omega * pi * x0 + 2 * pi ** 2 * x0 ** 2) ** 2
                )

            # dy/dx0
            jacmat[i, 2] = \
                (
                    2 * A * omega**2 * pi * np.sin(
                        (t*np.sqrt(omega**2 + (2*pi*x - 2*pi*x0)**2))/2.
                    )
                    *
                    (
                        (
                            -2*pi*t*(x - x0)*(omega**2 + (omega - 2*pi*x0)**2)*np.cos
                            (
                                (t*np.sqrt(omega**2 + (2*pi*x - 2*pi*x0)**2))/2.
                            )
                        ) / np.sqrt(omega**2 + (2*pi*x - 2*pi*x0)**2)
                        +
                        2 * (omega - 2*pi*x0)*np.sin(
                            (t*np.sqrt(omega**2 + (2*pi*x - 2*pi*x0)**2))/2.
                        )
                    )
                )/(
                    omega**2 + (omega - 2*pi*x0)**2
                )**2


            # dy/dt
            jacmat[i, 3] = \
                (
                    A*omega**2*np.sqrt(omega**2 + (2*pi*x - 2*pi*x0)**2)
                    *
                    np.sin(
                        t*np.sqrt(omega**2 + (2*pi*x - 2*pi*x0)**2)
                    )
                ) /\
                (
                    4.*(omega**2 - 2*omega*pi*x0 + 2*pi**2*x0**2)
                )

            # dy/dy0
            jacmat[i, 4] = 1
        return jacmat

    @classmethod
    def autoguess(cls, xs, ys, hold={}, man_guess={}, man_bounds={},
                  man_scale={}):
        miny = min(ys)
        maxy = max(ys)
        hmax = (maxy - miny)/2

        if ys[0] > 0.5*(maxy - miny) + miny:
            polarity = -1
        else:
            polarity = 1

        x0_guess = (max(xs) - min(xs))/2
        for i, y in enumerate(ys):
            if (polarity == -1 and y == miny) or (polarity == 1 and y == maxy):
                x0_guess = xs[i]
                break
        hwhm = 0
        for i, y in enumerate(ys):
            if polarity == 1 and y > miny + hmax:
                hwhm = abs(x0_guess - xs[i])
                break
            if polarity == -1 and y < miny + hmax:
                hwhm = abs(x0_guess - xs[i])
                break

        # auto guess
        if polarity == 1:
            A_guess = max(ys) - min(ys)
            y0_guess = min(ys)
        else:
            A_guess = min(ys) - max(ys)
            y0_guess = min(ys) - A_guess

        # omega guess
        omega_guess = pi/(10*us)

        # t guess
        x = (x0_guess + hwhm)
        t_guess = (2*(pi - asin((omega_guess**2 + x**2 - 2*x*x0_guess + x0_guess**2)/(2.*omega_guess**2)) + 2*pi*0))/sqrt(omega_guess**2 + x**2 - 2*x*x0_guess + x0_guess**2)

        g = {
            'omega': omega_guess,
            't': t_guess,
            'y0': y0_guess,
            'A': A_guess,
            'x0': x0_guess
        }

        # bounds
        if polarity == 1:
            A_bounds = [0, 20]
            y_bounds = [0, 2]
        else:
            A_bounds = [-20, 0]
            y_bounds = [0, 22]
        bounds = ([A_bounds[0], 0, 0, 0, y_bounds[0]], [A_bounds[1], np.inf, np.inf, np.inf, y_bounds[1]])

        # rough natural scale values
        xsc = {}
        xsc['omega'] = abs(g['omega'])
        xsc['t'] = us
        xsc['y0'] = 1
        xsc['A'] = 1
        xsc['x0'] = abs(g['x0'])

        return cls.autoguess_outputs(g, xsc, bounds, hold, man_guess, man_bounds, man_scale)


