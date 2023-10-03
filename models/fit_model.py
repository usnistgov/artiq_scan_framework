from .model import *
from ..analysis.curvefits import *
import numpy as np
from math import *
from ..language.exceptions import *


class FitModel(Model):
    mirror = True
    validation_errors = {}
    valid = True
    validators = {}
    fit_map = {}

    def fit_data(self, x, y, fit_function, hold=None, guess={}, yerr=None, man_bounds={}, man_scale={}):
        """Fit data in x and y to self.fit_function"""
        # make sure x & y are numpy arrays

        if fit_function is None:
            self.logger.warning("No fit function has been set")
            return
        x = np.array(x)
        y = np.array(y)
        # -- fit the data
        guess = guess or {}  # if guess is None
        self.fit = Fit(x, y, fit_function, yerr)
        self.fit.fit_data(hold=hold, man_guess=guess, man_bounds=man_bounds, man_scale=man_scale)

        # fitline in original order of x
        self.fit.fitline_orig = self.fit.func.value(x, *self.fit.popt)

        # -- map params
        FitModel.map(self)

        # -- regression analysis
        """Regression analysis"""
        self.fit.reg_err = round(FitModel.reg_err(y, self.fit.fitline), 3)
        self.fit.r2 = round(FitModel.r2(y, self.fit.fitline), 3)

        self.fit.fitresults['analysis'] = {
            'reg_err': self.fit.reg_err,
            'r2': self.fit.r2
        }

    def map(self):
        """Map fit function parameter names to more descriptive names (e.g. for dataset names)"""
        if self.fit_map:
            for name in self.fit_map:
                mapped = self.fit_map[name]
                self.fit.fitresults[mapped] = self.fit.fitresults[name]
                self.fit.fitresults[mapped + "_err"] = self.fit.fitresults[name + "_err"]

    def pre_validate(self, series, validators=None):
        """Validate data is acceptable to fit"""
        self.validation_errors = {}
        self.valid = True
        if validators == None:
            return True
        for field, rules in validators.items():
            for method, args in rules.items():
                value = series[field]
                self.valid = self._call_validation_method(method, field, value, args)
                if not self.valid:
                    raise CantFit(self.validation_errors[field])
        return True

    def validate(self, validators=None):
        """Validate fit was successful"""

        self.validation_errors = {}
        self.valid = True

        if validators == None:
            return True

        for field, rules in validators.items():
            fields = field.split(".")
            for method, args in rules.items():
                value = self.fit.fitresults
                ok = True
                for f in fields:
                    if f in value:
                        value = value[f]
                    else:
                        self.logger.error("Validation skipped, {0} is not in fitresults".format(field))
                        ok = False
                        break
                if ok:
                    self.valid = self._call_validation_method(method, field, value, args)
                    if not self.valid:
                        raise BadFit(self.validation_errors[f])
        return True

    def simulate(self, x, noise_level=0, simulation_args=None, noise_type='rectangular'):
        """Simulates scan data using a fit function with optional noise added.

        :param x: Value at which the fit function is evaluated.
        :param noise_level: amount of noise added to fit function value.  Only applicable when noise_type='rectangular'.
        Noise signal takes on values between -noise_level and +noise_level.
        :param simulation_args: Additional arguments passed to the fit function.  If set to None, simulation_args defaults to
        either self.simulation_args (if defined, first choice) or self.fit_function.simulation_args() (if self.simulation_args is not
        defined, second choice).
        :param noise_type: What type of noise to simulate.  Allowable values are
        'poisson' - models noise using a poisson distribution (e.g. PMT counts), 'rectangular' - models noise using a rectangular
        distribution, None - no noise is added.  Any other value will result in an exception being raised.
        :return:  Value of fit function, evaluated at x, with optional noise added.
        """
        if simulation_args == None:
            try:
                simulation_args = self.simulation_args
            except(NotImplementedError):
                simulation_args = self.fit_function.simulation_args()

        # -- get the value of the fit function
        ffun_val = self.fit_function.value(x, **simulation_args)

        # -- add noise to the fit function value
        # model noise using a poisson distribution
        if noise_type == 'poisson':
            withnoise = np.random.poisson(ffun_val, 1)[0]
        # model noise using a rectangular distribution
        elif noise_type == 'rectangular':
            # convert expectation value to quantized value
            f = floor(ffun_val)
            c = ceil(ffun_val)
            if np.random.random() > (ffun_val - f):
                value = f
            else:
                value = c
            noise = (2.0 * np.random.random() - 1.0) * noise_level
            withnoise = abs(value + noise)
        # no noise
        elif noise_type is None:
            withnoise = ffun_val
        else:
            raise Exception("Unknown noise_type {} specified".format(noise_type))
        return round(withnoise)

    @staticmethod
    def reg_err(y, fitline):
        """Calculate the standard error in the regression"""
        y = y[~np.isnan(y)]
        N = len(y)
        ss_res = np.sum((y - fitline)**2)     # residual sum of squares
        ss_tot = np.sum((y - np.mean(y))**2)  # total sum of squares
        S = np.sqrt(ss_res/N)
        return S

    @staticmethod
    def r2(y, fitline):
        """Calculate the coefficient of determination (R^2)"""
        y = y[~np.isnan(y)]
        ss_res = np.sum((y - fitline)**2)     # residual sum of squares
        ss_tot = np.sum((y - np.mean(y))**2)  # total sum of squares
        r2 = 1 - ss_res / ss_tot
        return r2
