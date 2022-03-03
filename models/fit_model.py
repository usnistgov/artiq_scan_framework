from scan_framework.models.model import *
from scan_framework.analysis.curvefits import *
import numpy as np
from math import *


class BadFit(Exception):
    pass


class CantFit(Exception):
    pass


class FitModel(Model):
    mirror = True
    validation_errors = {}
    valid = True
    validators = {}
    fit_map = {}

    def fit_data(self, x, y, fit_function, hold=None, guess={}, yerr=None, man_bounds={}, man_scale={}):
        """Fit data in x and y to self.fit_function"""
        # make sure x & y are numpy arrays
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
                        self.logger.warning("Validation skipped, {0} is not in fitresults".format(field))
                        ok = False
                        break
                if ok:
                    self.valid = self._call_validation_method(method, field, value, args)
                    if not self.valid:
                        raise BadFit(self.validation_errors[field])
        return True

    def simulate(self, x, noise_level=0, simulation_args = None):
        if simulation_args == None:
            try:
                simulation_args = self.simulation_args
            except(NotImplementedError):
                simulation_args = self.fit_function.simulation_args()
        value = self.fit_function.value(x, **simulation_args)

        # convert expectation value to quantized value
        f = floor(value)
        c = ceil(value)
        if np.random.random() > (value - f):
            value = f
        else:
            value = c

        noise = (2.0 * np.random.random() - 1.0) * noise_level
        return int(abs(value + noise))

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
