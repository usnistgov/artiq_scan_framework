from scan_framework.unit_tests.test_case import *
from scan_framework.models.fit_model import *
from scan_framework.analysis.curvefits import FitFunction


# test validation of fit params
class TestValidation(TestCase):
    def setUp(self):
        super().setUp()
        self.model = FitModel(self, fit_function=InvCos)

        # perform a fit
        points = np.linspace(0, 100*us, 100, dtype=np.float64)
        means = np.full(100, fill_value=0, dtype=np.float64)
        for i_point, point in enumerate(points):
            m = 0
            for i_repeat in range(100):
                m += self.model.simulate(point,
                                         noise_level=0,
                                         simulation_args={
                                              'amplitude': 5,
                                              'pi_time': 10*us,
                                              'phase': 0,
                                              'y_min': 3
                                          })
            means[i_point] = m/100.0

        self.model.fit_data(points, means,
                            fit_function=InvCos,
                            hold={},
                            guess={
                                'amplitude': 5,
                                'pi_time': 10 * us,
                                'phase': 0,
                                'y_min': 3
                            }
        )

    def run_validation(self, validators):
        try:
            valid = True
            self.model.validate(validators=validators)
        except BadFit:
            valid = False
        return valid

    def test_validators(self):
        # between validation
        self.assertEqual(self.run_validation({
            "params.pi_time": {
                'between': [0 * us, 1 * us],
            },
        }), False)
        self.assertEqual(self.run_validation({
            "params.pi_time": {
                'between': [0 * us, 100 * us],
            },
        }), True)

        # reg_err
        self.assertEqual(self.run_validation({
            "analysis.reg_err": {
                "less_than": 0.00001
            },
        }), False, "invalid reg_err")
        self.assertEqual(self.run_validation({
            "analysis.reg_err": {
                "less_than": 10
            },
        }), True, "valid reg_err")


if __name__ == '__main__':
    unittest.main()


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


def tpi_fft(xdata, ydata):
    """Estimates pi time via FFT of rabi flopping data in ydata"""
    return estimate_period(xdata, ydata) / 2


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
