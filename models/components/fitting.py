import numpy as np
from ...ex
from ...language.exceptions import *
from artiq.language import *
import logging
from ..model import Model


class Fitting:

    def __init__(self, model):
        self.model = model

    def __getattr__(self, name):
        return getattr(self.model, name)

    def __setattr__(self, key, value):
        setattr(self.model, key, value)

    # TODO: remove from scan_model.py
    # Doesn't look like this is being used anymore??? should we just remove this method??
    def set_main_fit(self, value):
        """Helper method.  Broadcasts, persists, and saves to the datasets the main fit param specified
        by the model's main_fit attribute.

        :param value: value of the main fit that will be saved.
        """
        self.set(self.main_fit_ds, value, which='main', broadcast=True, persist=True, save=True)

    # TODO: remove from scan_model.py
    # Doesn't look like this is being used anymore??? should we just remove this method??
    def get_fit(self, name, use_fit_result=False, i=None):
        """Helper method.  Fetches the value of fit param that was found during the last fit performed.
        The fit param returned will either be read from the datasets or from the model's fit object
        attribvute.

        :param name: Name of the fit param
        :type name: string
        :param use_fit_result: If True, the fit param is fetched from the models' fit object (self.fit) instead
                               of from the datasets.
        :type use_fit_result: bool
        """
        if use_fit_result:
            return self.fit.fitresults[name]
        else:
            key = self._map_fit_param(name)
            if self.default_fallback:
                default = self.get("defaults."+key)
            else:
                default = NoDefault
            return self.get("fits.params."+key, default=default)

    # TODO: remove from scan_model.py
    def get_main_fit(self, use_fit_result=False, i=None, archive=False) -> TFloat:
        """Helper method. Fetches the value of the main fit from its dataset or from the fitresults.

        :param use_fit_result: If True, the fit param value in the models fit object is returned. Otherwise
                               the fir param value will be fetched from the datasets.
        value.
        """
        #print('ScanModel::get_main_fit()')
        if use_fit_result:
            if self.main_fit_param is None:
                raise Exception("Can't get the main fit.  The 'main_fit' attribute needs to be set in the scan model.")
            return self.fit.fitresults[self.main_fit_param]
        else:
            if self.main_fit_ds is None:
                raise Exception("Can't get the main fit.  The 'main_fit' attribute needs to be set in the scan model.")

            if self.default_fallback:
                default = self.get("defaults."+self.main_fit_ds, archive=archive)
            else:
                default = NoDefault
            #print('main_fit_ds is', self.main_fit_ds)
            return self.get(self.main_fit_ds, default=default, archive=archive)

    # TODO: remove from scan_model.py and update loops to call scan.model.fitting.get_fit_data() instead of scan.model.get_fit_data(0
    def get_fit_data(self, use_mirror):
        """Helper method.  Returns the experimental data to use for fitting."""
        x_data = self.get('stats.points', mirror=use_mirror)
        y_data = self.get('stats.mean', mirror=use_mirror)
        return x_data, y_data

    # TODO: remove from scan_model.py
    def get_guess(self, x_data, y_data):
        """Helper method.  Returns the fit guesses to use for fitting."""
        return self.guess or {}

    # TODO: remove from scan_model.py
    def get_hold(self, x_data, y_data):
        """Helper method.  Returns the fit guesses to use for fitting."""
        return self.hold or {}

    # TODO: remove fit_data method (this method replaces the fit_data method) from scan_model.py
    def fit(self, x_data, y_data, errors, fit_function, guess={}, hold={}, i=None, validate=True, set=True, save=False,
                 man_bounds={}, man_scale={}):
        """Perform a fit of the x values, y values, and errors to the specified fit function.

        :param x_data: X values of the experimental data
        :param y_data: Y values of the experimental data
        :param errors: Error in each corresponding Y value of the experimental data
        :param fit_function: The function being fit to the data points and errors given by x_data, y_data, and errors.
        :param guess: Dictionary containing the initial guess for each fit param.  Keys specify fit param names and values
                      the initial guess of that fit param.
        :type guess: dict
        :param validate: If True, fit validations will be performed
        :param set: If True, all generated data pertaining to the fit will be saved to the datasets under the model's namespace
        :param save: If True, the main fit will be saved to the datasets, as long as any defined strong validations pass.
        :param man_bounds: Dictionary containing the allowed bounds for each fit param.  Keys specify fit param names and values
                           are set to a list to specify the bounds of that fit param.
        :param man_scale: Dictionary containing the scale of each fit param.  Keys specify fit param names and values
                          are set to floats that specify the scale of that fit param.
        """
        #self._scan.print('call: ScanModel::fit_data(save={})'.format(save), 2)
        # class name of the last run scan
        class_name = self.get('class_name', mirror=True)
        if class_name != self.model._scan.__class__.__name__:
            raise Exception("Attempting to perform a fit on data generated by a different scan.")
        x_sorted = sorted(x_data)
        fit_performed = False
        saved = False
        errormsg = ""
        valid_pre = False
        valid_strong = False

        # update class variables used in validations.
        self.min_point = min(x_sorted)
        self.max_point = max(x_sorted)
        self.tick = x_sorted[1] - x_sorted[0]

        # don't validate if validations have been disabled
        if self.disable_validations:
            validate = False

        # - pre-validate data
        if validate:
            #self._scan.print('validating')
            try:
                valid_pre = self.validate_fit('pre', x_data, y_data)
            except CantFit as msg:
                valid_pre, errormsg = False, msg
            self.fit_valid_pre = valid_pre

        # - fit
        if not validate or valid_pre:
            # get data to fit
            guess_all = self.get_guess(x_data, y_data)  # guesses from model
            guess_all.update(guess)  # guesses from gui (overrides guesses from model)
            hold_all = self.get_hold(x_data, y_data)  # guesses from model
            hold_all.update(hold)  # guesses from gui (overrides guesses from model)
            try:
                yerr = errors if self.fit_use_yerr else None
                self.fit_data(x_data, y_data, fit_function, hold=hold_all, guess=guess_all, yerr=yerr, man_bounds=man_bounds, man_scale=man_scale)
                fit_performed = True
            except ValueError as msg:
                self.logger.error("ERROR Fit Failed: {0}".format(msg))

        # - post-validation & save fits
        if fit_performed:
            #self._scan.print('fit was performed')
            if not hasattr(self, 'fit'):
                self.logger.warn('No fit was performed')
            else:
                # append x/y dataset
                self.fit.fitresults['x_dataset'] = self.get_xs_key()
                self.fit.fitresults['y_dataset'] = self.get_means_key()

                self.before_validate(self.fit)

                # - set all fitted params to datasets
                if set:
                    self.set_fits(i)

                # - post-validate the fit
                if validate:
                    #self._scan.print('post validating fit')
                    # - strong validations:
                    #   * fit params not saved if this fails.
                    try:
                        valid_strong = True
                        errormsg = ""
                        self.validate_fit('strong')
                    except BadFit as msg:
                        valid_strong = False
                        errormsg = msg
                    self.fit_valid_strong = valid_strong

                    # - soft validations:
                    #   * fit params *are* saved if this fails
                    #   * this is not performed if the strong validations failed
                    if valid_strong:
                        try:
                            valid_soft = True
                            errormsg = ""
                            self.validate_fit('soft')
                        except BadFit as msg:
                            valid_soft = False
                            errormsg = msg
                        self.fit_valid_soft = valid_soft

                # - save fitted params to datasets
                # is it ok to save the fit params?
                #self._scan.print('valid_strong is {}'.format(valid_strong))
                #self._scan.print('save is {}'.format(save))
                if save and (not validate or valid_strong):
                    #self._scan.print('saving')
                    # - save the main fit
                    if self.main_fit_param and self.main_fit_ds:
                        self.save_fit(fitparam=self.main_fit_param, dskey=self.main_fit_ds, broadcast=True, persist=True, save=True)
                        saved = True
                    else:
                        self.logger.warning("Fits cannot be saved because a main fit param has not be specified in the model")

                    # - save other fits
                    for fitparam, dskey in self.fits_to_save.items():
                        if fitparam and fitparam is not self.main_fit_param:
                            self.save_fit(fitparam=fitparam, dskey=dskey, broadcast=True, persist=True, save=True)

        # store status of fit to class variables.
        self.fit_performed = fit_performed
        if not validate:
            self.fit_valid = None
        else:
            self.fit_valid = self.fit_valid_pre and self.fit_valid_strong and self.fit_valid_soft
        self._fit_saved = saved

        # tell the user about any fit validation errors or warnings that occurred.
        if self.fit_valid_pre is False:
            self.logger.warning("Fit skipped {}".format(errormsg))
        if self.fit_valid_soft is False:
            self.logger.warning("Invalid fit {}".format(errormsg))
        if self.fit_valid_strong is False:
            self.logger.error("Invalid fit. {}".format(errormsg))

        # save fit state to datasets
        self.set('fits.fit_performed', fit_performed)
        self.set('fits.fit_valid', self.fit_valid)
        self.set('fits.fit_saved', self._fit_saved)
        self.set('fits.fit_errormsg', errormsg)
        #self._scan.print('return: ScanModel::fit_data()', -2)
        return fit_performed, self.fit_valid, saved, errormsg

    # TODO: remove from fit_model.py
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
        self.map()

        # -- regression analysis
        """Regression analysis"""
        self.fit.reg_err = round(self.reg_err(y, self.fit.fitline), 3)
        self.fit.r2 = round(self.r2(y, self.fit.fitline), 3)

        self.fit.fitresults['analysis'] = {
            'reg_err': self.fit.reg_err,
            'r2': self.fit.r2
        }

    # TODO: remove from scan_model.py
    def _map_fit_param(self, name):
        """ Maps a fit param name to it's dataset key """
        if self.fit_map is not None and name in self.fit_map:
            return self.fit_map[name]
        return name

    # TODO: remove from scan_model.py
    @property
    def main_fit_param(self):
        p = self.main_fit
        if isinstance(p, list):
            return p[0]
        else:
            return p

    # TODO: remove from scan_model.py

    @property
    def main_fit_ds(self):
        p = self.main_fit
        if isinstance(p, list):
            return p[1]
        else:
            return p


    # TODO: remove from fit_model.py
    def map(self):
        """Map fit function parameter names to more descriptive names (e.g. for dataset names)"""
        if self.fit_map:
            for name in self.fit_map:
                mapped = self.fit_map[name]
                self.fit.fitresults[mapped] = self.fit.fitresults[name]
                self.fit.fitresults[mapped + "_err"] = self.fit.fitresults[name + "_err"]

    # TODO: remove from scan_model.py
    def save_fit(self, fitparam, dskey, broadcast=False, persist=False, save=True):
        """Helper method.  Saves the specified fit param to the datasets under the model's namespace.

        :param fitparam: Name of the fit param to save
        :type fitparam: string
        :param dskey: Datset key to save the fit param value to
        :param broadcast: Indicates if the dataset should be broadcast, defaults to False
        :param persist: Indicates if the dataset should be persisted, defaults to False
        :param save: Indicates if the dataset should be saved to the hdf5 file, defaults to True
        """
        # get the fitted param
        fitval = self.fit.fitresults[fitparam]

        # save it to a dataset
        self.set(dskey, fitval, which='main', broadcast=broadcast, persist=persist, save=save)

        # record what's been saved
        if broadcast is True:
            self.fits_saved[self.key(dskey)] = fitval


    # TODO: remove from scan_model.py
    def set_fits(self, i=None):
        """Helper method.  Set's all data generated during fitting to datasets under the model's namespace.
        """

        # fitted params
        for key, value in zip(self.fit.params._fields, self.fit.params):
            key = "fits.params.{0}".format(key)
            if i is not None:
                key = "fits.{0}.{1}".format(i, key)
            self.set(key, value)

        # guess
        for key, value in zip(self.fit.params._fields, self.fit.guess):
            key = "fits.guesses.{0}".format(key)
            if i is not None:
                key = "fits.{0}.{1}".format(i, key)
            self.set(key, value)

        # fitted param errors
        for key, value in zip(self.fit.errs._fields, self.fit.errs):
            key = "fits.errors.{0}".format(key)
            if i is not None:
                key = "fits.{0}.{1}".format(i, key)
            self.set(key, value)

        # fitline
        key = 'fitline'
        if i is not None:
            key = "fits.{0}.{1}".format(i, key)
        else:
            # this must update the current_scan so fitlines show up in the plots
            mirror = self.mirror
            self.mirror = True
            self.set('plots.fitline', self.fit.fitline_orig)
            self.set('plots.x_fine', self.fit.fitresults['x_fine'])
            self.set('plots.fitline_fine', self.fit.fitresults['fitline_fine'])
            self.mirror = mirror

        self.set(key, self.fit.fitline_orig)

        # regression analysis
        key = 'fits.analysis.r2'
        if i is not None:
            key = "fits.{0}.{1}".format(i, key)
        self.set(key, self.fit.r2)
        key = 'analysis.reg_err'
        if i is not None:
            key = "fits.{0}.{1}".format(i, key)
        self.set(key, self.fit.reg_err)

    # TODO: remove from scan_model.py and update scan.py to call model.fitting.report_fit() instead of model.report_fit()
    def report_fit(self, logger=None):
        """Helper method.  Prints fit results to the console"""
        if not hasattr(self, 'fit'):
            return
        if logger is None:
            if hasattr(self, '_scan'):
                logger = self._scan.logger
            else:
                logger = logging.getLogger()

        # display fitted parameters
        logger.info("Fitted Parameters:")
        for key, param, error in zip(self.fit.params._fields, self.fit.params, self.fit.errs):
            unit, scaled, text = Model._format(key, param, self)
            error_unit, error_scaled, error_text = Model._format(key, error, self)
            logger.info("{0} = {1} +/- {2} {3}".format(key, scaled, error_scaled, unit))

        # display regression analysis
        if hasattr(self.fit, 'r2'):
            logger.info("r2 = {0}".format(self.fit.r2))
        if hasattr(self.fit, 'reg_err'):
            logger.info("reg_err = {0}".format(self.fit.reg_err))

        # display every fit that was set
        if self.fits_saved:
            self._scan.logger.info("Fits Saved:")
            for key, value in self.fits_saved.items():
                s = key.split('.')
                unit, _, scaled = Model._format(s[-1], value)
                logger.info("%s set to %s" % (key, scaled))
                logger.info("")

        # display datasets that we're updated
        if self.fits_set:
            self._scan.logger.info("Datasets Updated:")
            for key, value in self.fits_set.items():
                s = key.split('.')
                unit, _, scaled = Model._format(s[-1], value)
                logger.info("%s set to %s" % (key, scaled))

    # TODO: remove from fit_model.py
    @staticmethod
    def reg_err(y, fitline):
        """Calculate the standard error in the regression"""
        y = y[~np.isnan(y)]
        N = len(y)
        ss_res = np.sum((y - fitline) ** 2)  # residual sum of squares
        ss_tot = np.sum((y - np.mean(y)) ** 2)  # total sum of squares
        S = np.sqrt(ss_res / N)
        return S

    # TODO: remove from fit_model.py
    @staticmethod
    def r2(y, fitline):
        """Calculate the coefficient of determination (R^2)"""
        y = y[~np.isnan(y)]
        ss_res = np.sum((y - fitline) ** 2)  # residual sum of squares
        ss_tot = np.sum((y - np.mean(y)) ** 2)  # total sum of squares
        r2 = 1 - ss_res / ss_tot
        return r2

    # TODO: remove old method from scan_model.py
    def validate_fit(self, rule, x_data=None, y_data=None):
        # check pre-validation rules
        if rule == 'pre':
            return self.pre_validate(
                series={'x_data': x_data, 'y_data': y_data},
                validators=self.pre_validators)
        elif rule == 'strong':
            self.validate(self.strong_validators)
        elif rule == 'soft':
            self.validate(self.validators)

    # TODO: remove old method from fit_model.py
    def pre_validate(self, series, validators=None):
        """Validate data is acceptable to fit"""
        self.validation_errors = {}
        self.valid = True
        if validators is None:
            return True
        for field, rules in validators.items():
            for method, args in rules.items():
                value = series[field]
                self.valid = self._call_validation_method(method, field, value, args)
                if not self.valid:
                    raise CantFit(self.validation_errors[field])
        return True

    # TODO: remove old method from fit_model.py
    def validate(self, validators=None):
        """Validate fit was successful"""

        self.validation_errors = {}
        self.valid = True

        if validators is None:
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