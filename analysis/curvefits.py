# -*- coding: utf8 -*-
#
# Author: Daniel Slichter / NIST Ion Storage
# 2016-2022
# 
#
# Automated scientific curve fitting routines
#
# NIST DISCLAIMER
#
# The following information applies to all software listed below as developed
# by employees of NIST.
#
# NIST-developed software is provided by NIST as a public service. You may use, copy, and distribute
# copies of the software in any medium, provided that you keep intact this entire notice. You may
# improve, modify, and create derivative works of the software or any portion of the software, and
# you may copy and distribute such modifications or works. Modified works should carry a notice
# stating that you changed the software and should note the date and nature of any such change.
# Please explicitly acknowledge the National Institute of Standards and Technology as the source of
# the software.
#
# NIST-developed software is expressly provided "AS IS." NIST MAKES NO WARRANTY OF ANY KIND, EXPRESS,
# IMPLIED, IN FACT, OR ARISING BY OPERATION OF LAW, INCLUDING, WITHOUT LIMITATION, THE IMPLIED WARRANTY
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, NON-INFRINGEMENT, AND DATA ACCURACY. NIST
# NEITHER REPRESENTS NOR WARRANTS THAT THE OPERATION OF THE SOFTWARE WILL BE UNINTERRUPTED OR
# ERROR-FREE, OR THAT ANY DEFECTS WILL BE CORRECTED. NIST DOES NOT WARRANT OR MAKE ANY REPRESENTATIONS
# REGARDING THE USE OF THE SOFTWARE OR THE RESULTS THEREOF, INCLUDING BUT NOT LIMITED TO THE
# CORRECTNESS, ACCURACY, RELIABILITY, OR USEFULNESS OF THE SOFTWARE.
#
# You are solely responsible for determining the appropriateness of using and distributing the
# software and you assume all risks associated with its use, including but not limited to the risks
# and costs of program errors, compliance with applicable laws, damage to or loss of data, programs
# or equipment, and the unavailability or interruption of operation. This software is not intended to
# be used in any situation where a failure could cause risk of injury or damage to property. The
# software developed by NIST employees is not subject to copyright protection within the United States.
#
# To see the latest statement, please visit:
# https://www.nist.gov/open/copyright-fair-use-and-licensing-statements-srd-data-software-and-technical-series-publications

from scipy.optimize import curve_fit
from scipy.fftpack import fft
from scipy.interpolate import LSQUnivariateSpline
from scipy.special import erfinv
from collections import namedtuple
from copy import deepcopy
import numpy as np
import logging

__all__ = ["Fit", "ExpSine", "Exp2Sine", "Sine", "Sin4", "Poly", "Lor",
           "Gauss", "AtomLine", "Exp", "Power", "Spline"]

logger = logging.getLogger(__name__)

class Fit():
    """Class for fitting curves and storing/calculating results.

    Fit types
    ---------------------
    ExpSine : exponentially decaying sine, [A, f, tau, phi, y0]
    Exp2Sine : Gaussian decaying sine, [A, f, tau, phi, y0]
    Sine : sine wave, [A, f, phi, y0]
    Sin4 : sin^4, [A, f, phi, y0]
    Poly : N-degree polynomial, [p0, p1, ...., pN]
    Lor : Lorentzian lineshape [A, Gamma, x0, y0]
    Gauss : Gaussian lineshape [A, sigma, x0, y0]
    AtomLine : lineshape for pulsed atomic transition [A, Omega0, T, f0, y0]
    Exp : exponential decay/rise, [A, b, y0]
    Power : power law, [A, alpha, y0]
    Spline : smoothing spline fit to data, variable knot number

    Usage
    ---------------------
    Instantiate a `Fit()` object with the data to fit and the function to use,
    then call `fit_data()` to perform the fitting.  For example, fitting to
    (x,y) data pairs, with one-standard-deviation uncertainties yerr (these are
    optional, and you can fit without providing yerr), using an exponentially
    decaying sine wave:

    >>> fitobj = Fit(x, y, ExpSine, yerr)
    >>> fitobj.fit_data()

    Any data points where x, y, and/or yerr (if given) are NaN or inf are
    removed from the data prior to fitting.  In addition, the data are sorted
    in ascending order in x.  This only affects the internal data stored as
    attributes of fitobj; the original arrays from the user code are not
    modified.  The cleaned, sorted data can be accessed as follows:

    >>> fitobj.x
    >>> fitobj.y
    >>> fitobj.yerr

    If provided, the values in yerr will be used to perform a weighted fit.  If
    any of the values in yerr are zero or negative, a warning will be printed
    and an unweighted fit will be performed instead.  If yerr is not provided,
    the fit defaults to an unweighted fit.

    There are different lines of best fit calculated automatically.  The first
    is calculated at all values in the cleaned, sorted fitobj.x, the second is
    calculated over the full range of fitobj.x but with 10 times as many points
    (finer spacing).  This more finely spaced x data is stored as the attribute
    x_fine of the Fit() object.  Lines of best fit can be accessed as follows:

    >>> fitline = fitobj.fitline  # line of best fit at values x
    >>> fitline = fitobj.fitline_fine  # line of best fit at 10x density

    To plot these fitlines, it is recommended to plot them against the cleaned,
    sorted x values in the attributes fitobj.x and fitobj.x_fine, which may be
    in a different order than the original input x to the Fit() constructor:

    >>> plot(fitobj.x, fitobj.fitline)
    >>> plot(fitobj.x_fine, fitobj.fitline_fine)

    Alternatively, you can calculate the value of the best fit line at any
    point or array of points xi with the `value()` method:

    >>> yi = fitobj.value(xi)

    This can be used to calculate a line of best fit to the original input x,
    rather than the cleaned, sorted fitobj.x, if for example the original input
    x is not given in ascending order.

    The values of the fitted parameters can be accessed in different ways.  For
    example, with an ExpSine, the time constant tau and its uncertainty can be
    found in the following ways:

    >>> fitobj.params.tau
    >>> fitobj.errs.tau_err
    >>> fitobj.tau
    >>> fitobj.tau_err

    Fitted parameter values, errors, and a variety of other relevant output
    data (such as covariance matrices) are stored as attributes of the `Fit()`
    object.  All of these attributes are also stored in a dictionary called
    `fitresults`, which is itself an attribute of the `Fit()` object.  This
    dictionary can be saved in ARTIQ as a dataset in HDF5 format (since the
    `Fit()` object itself cannot be).  For further details on the `fitresults`
    dictionary and a full listing of the attributes of the `Fit()` object, see
    the docstrings for the `fit_data()` and `fitline_conf()` methods.

    If you would like to hold certain parameters fixed during a fit, this can
    be done by listing those parameters and their fixed values with the `hold`
    argument, which is a dictionary where keys are names of parameters to hold
    fixed and values are those values at which they should be held.  Dictionary
    keys which do not correspond to a valid fit parameter name will be ignored
    (in the second line, "foobar" will be ignored).

    >>> fitobj.fit_data(hold={'A': 0.7, 'tau': 25e-5})
    >>> fitobj.fit_data(hold={'A': 0.7, 'tau': 25e-5, 'foobar': 2367234})

    The fitting routines automatically calculate initial guesses for the fit
    parameters, and these are generally fairly robust.  However, if the fit is
    not converging properly, it is possible to supply manual guesses for any
    fit parameter as a dictionary called `man_guess` to `fit_data()`.  Order is
    unimportant, and manual guesses for nonexistent fit parameters will be
    ignored.  For example, with an ExpSine fit, one could provide the following
    manual guesses (in the second line, "foobar" will be ignored).

    >>> fitobj.fit_data(man_guess={'tau': 25e-6, 'f': 300e5})
    >>> fitobj.fit_data(man_guess={'tau': 25e-6, 'f': 300e5, 'foobar': -91})

    The default bounds for parameter values can be changed by passing the
    `man_bounds` argument, while the default scale factors for parameters
    (which are used to give more robust fitting, see the documentation for
    scipy.curve_fit parameter `x_scale`) can be changed with the `man_scale`
    argument.  Usage is similar to `man_guess`, except that for `man_bounds`
    a 2-item tuple or list giving higher and lower bounds must be passed,
    rather than a single value.  As with `man_guess` and `hold`, invalid
    parameter names are ignored.

    >>> fitobj.fit_data(man_bounds={'A': (0,1)}, man_scale={'tau':1e-4})

    Manual guesses, bounds, and scale are all ignored for parameters which are
    being held fixed with `hold`.

    Confidence intervals for fit lines can also be calculated from the fit
    results.  The `fitline_conf()` method calculates confidence bands at a
    specified confidence level at all points x.  This method takes two optional
    arguments, which specify the confidence level (default is 0.95) and whether
    to calculate a confidence band for the more finely spaced `fitline_fine`
    (mentioned above) as well:

    >>> fitobj.fitline_conf()
    >>> fitobj.fitline_conf(conf=0.68, fine=True)

    The `conf_band()` method allows the calculation of confidence bands for any
    point or array of points xi, with an optional argument for the confidence
    level (default 0.95), which returns the standard deviation plus upper and
    lower confidence levels for each point in xi:

    >>> ysigma, yupper, ylower = fitobj.conf_band(xi, conf=0.68)

    A full listing of the attributes of the `Fit()` object which you can
    access is given in the documentation for the `fit_data()` and
    `fitline_conf()` methods.
    """

    def __init__(self, x, y, func, yerr=None, polydeg=4, knots=7):
        """Constructor for Fit() class
        Does not perform any fitting -- for that call fit_data()

        Parameters (for constructor)
        --------------
        x : 1-d array of independent variable
        y : 1-d array of dependent variable (to fit), same shape as x
        func : class of fit function to use.  fit to y = f(x).
        yerr : 1-d array of std. deviations of y, for fit weighting, optional
        polydeg : degree of polynomial fit, optional
        knots : number of knots to use in spline fit, optional
            Knots will be evenly spaced over the range of x.  If knots is
            larger than len(x)/2, it will be rounded down to len(x)/2.  This
            prevents undesirable "spikes" from appearing in the fitted spline.

        The constructor stores deep copies of x, y, and yerr (if given) as 
        attributes of the Fit() object.  Before doing so, it checks for and 
        discards any data points where x, y, and/or yerr (if given) is NaN or 
        inf.  In addition, it sorts all the data in order of increasing x 
        before storing as object attributes.
        """

        xtemp = np.asarray(deepcopy(x))
        ytemp = np.asarray(deepcopy(y))
        # order in ascending order of x for fitting, clean any nans and infs
        if yerr is None:
            keep = np.isfinite(xtemp) & np.isfinite(ytemp)
            xtemp = xtemp[keep]
            ytemp = ytemp[keep]
            self.y = ytemp[np.argsort(xtemp)]
            self.x = xtemp[np.argsort(xtemp)]
            self.yerr = None
        else:
            yerrtemp = np.asarray(deepcopy(yerr))
            keep = (np.isfinite(xtemp) & np.isfinite(ytemp) 
                    & np.isfinite(yerrtemp))
            xtemp = xtemp[keep]
            ytemp = ytemp[keep]
            yerrtemp = yerrtemp[keep]
            self.y = ytemp[np.argsort(xtemp)]
            self.yerr = yerrtemp[np.argsort(xtemp)]
            self.x = xtemp[np.argsort(xtemp)]

        self.func = func
        self.polydeg = polydeg
        self.knots = min(knots, len(x)//2)  # cap max number of spline knots
        self.fit_good = False  # indicates if the fit has succeeded

        # begin populating fitresults dictionary.  This dictionary mirrors the
        # attributes of the Fit() class, but can be saved in ARTIQ (unlike the
        # Fit() class instances themselves) as a dataset.
        self.fitresults = {}
        self.fitresults['fit_good'] = self.fit_good
        self.fitresults['x'] = self.x
        self.fitresults['y'] = self.y
        self.fitresults['yerr'] = self.yerr
        self.fitresults['func'] = self.func
        self.fitresults['knots'] = self.knots
        self.fitresults['polydeg'] = self.polydeg

    def value(self, x):
        """Calculate value of fitted function at x.  Will raise an exception
        if there are no calculated fit parameters yet."""

        if self.func.__name__ == 'Spline':
            try:
                splobj = self.splobj
            except AttributeError:
                logger.error("No available spline fit parameters!\n" + 
                               "Call fit_data() to generate spline fit.")
                raise
            else:
                return splobj(x)
        elif self.func.__name__ == 'Poly':
            try:
                popt = self.popt
            except AttributeError:
                logger.error("No available polynomial fit parameters!\n" + 
                               "Call fit_data() to generate polynomial fit.")
                raise
            else:
                return self.func.value(x, popt)
        else:
            try:
                popt = self.popt
            except AttributeError:
                logger.error("No available polynomial fit parameters!\n" + 
                               "Call fit_data() to generate fit.")
                raise
            else:
                return self.func.value(x, *popt)

    def fit_data(self, hold={}, man_guess={}, man_bounds={}, man_scale={}):
        """Fit data x and y to function f, y = f(x).  Calculates optimal fit
        parameters and their associated uncertainties, including full
        covariance matrix.  By default, function makes automatic guesses
        for initial parameter values.  Optional manual initial guesses can be
        given to override the autoguess function.  If desired, user can specify
        fixed values for some parameters, and these will be held at the
        specified value and not fitted for.  Optional manual parameter bounds
        or scaling factors can be specified to override default values as well.

        Parameters
        -------------------
        hold : dict of parameter name/value pairs, optional
            The named parameters will not be fitted for, but will be held
            constant at the given values while the remaining parameters
            are varied to fit the data.  Not for Poly or Spline.  If a key in
            the dictionary does not correspond to a valid fit parameter, it is
            ignored and a warning is printed.
        man_guess : dict of parameter name/value pairs, optional
            Initial guesses for the fit values of the named parameters will be
            taken from the corresponding values.  Not for Poly or Spline.  If a
            key in the dictionary does not correspond to a valid fit parameter,
            it is ignored and a warning is printed. If a parameter is being
            held with "hold", manual guesses for that parameter are ignored and
            a warning is printed.
        man_bounds : dict of parameter names/lists of upper/lower bounds,
            optional.  Manual bounds (overriding the default bounds) for the
            named parameters will be taken from the corresponding lists.  Each
            list of bounds must have exactly two elements: [lower, upper].
            Not for Poly or Spline.  If a key in the dictionary does not
            correspond to a valid fit parameter, it is ignored and a warning is
            printed. If a parameter is being held with "hold", manual
            bounds for that parameter are ignored and a warning is printed.
        man_scale : dict of parameter name/value pairs, optional
            Values are natural scale factors for the named parameters, passed
            to x_scale of scipy.curve_fit.  Not for Poly or Spline.  If a key
            in the dictionary does not correspond to a valid fit parameter,
            it is ignored and a warning is printed. If a parameter is being
            held with "hold", manual scale for that parameter is ignored and
            a warning is printed.

        The results of the fit are stored as attributes of the instance of
        the Fit() class, as well as key-value pairs in the dictionary
        `fitresults`, which is an attribute of Fit().  This dictionary enables
        saving in ARTIQ/HDF5.  This dictionary is also returned by `fit_data()`

        Attributes set by fit_data():
        ---------------------
        bounds : tuple of lists of constraints on parameter values (see
                    documentation for scipy.optimize.curve_fit)
        c0, c1, c2, ... : polynomial fit coefficients for Poly fit. Form is
                            c0 + c1*x + c2*x^2 + ...
        c0_err, c1_err, ... : errors (one std. dev.) for Poly fit coefficients
        covmat : covariance matrix from fit (not for Spline)
        errs : namedtuple of errors (one std. dev.) on optimal fit parameters
        extrema_locs : x locations of extremal points (zero deriv.) of Spline
        extrema_vals : y values at these x locations of Spline fit
        fit_good : Boolean, indicates successful fitting
        fitline : line of best fit, evaluated at all locations x
        fitline_fine : line of best fit, evaluated at all locations in x_fine
        fitresults : dictionary representation of all attributes of the class
                    instance.
        guess : initial guess for fitting routine (not for Poly or Spline)
        hold : dictionary of fit parameters to hold fixed, with their values
        max : maximum y value of Spline fit
        maxloc : x location of maximum y value of Spline fit
        min : minimum y value of Spline fit
        minloc : x location of minimum y value of Spline fit
        params : namedtuple of optimal fit parameters
        popt : array of optimal fit parameters (duplicates `params`, used as
                a quicker way of accessing a list of the parameters if desired)
        splobj : scipy spline object representing Spline fit
        x_fine : evenly spaced list of x values between x[0] and x[-1],
                 10 times more points than x
        x_scale : rough scaling factor for parameter values (helps convergence)

        Individual attributes are created for each of the named parameters
        of the specific fit function.  Individual attributes are also created
        for their errors, with the suffix '_err'.  Thus for an ExpSine fit,
        the following attributes will be created:
            A
            A_err
            f
            f_err
            tau
            tau_err
            phi
            phi_err
            y0
            y0_err
        """
        # loading these to local vars just to make the code more compact below
        x = self.x
        y = self.y
        yerr = self.yerr
        func = self.func
        polydeg = self.polydeg
        knots = self.knots

        # 10x finer x values for calculating higher-density fit line
        x_fine = np.linspace(x[0], x[-1], 10*len(x))

        # flag any previous fit results as invalid until the new fit is done
        self.fitresults['fit_good'] = False
        self.fit_good = False

        if func.__name__ == 'Poly':
            # use different fit procedure for polynomial fits than others
            # since numpy provides it explicitly for us
            if yerr is None:
                try:
                    popt, pcov = np.polyfit(x, y, polydeg, cov=True)
                except:
                    logger.error("Polynomial fit failed!")
                    raise
            else:
                if np.any(np.less_equal(yerr, [0])):
                    logger.warning("Zero or negative \'yerr\' values " +
                                   "provided!\nIgnoring \'yerr\', performing "+
                                   "unweighted fit.")
                    try:
                        popt, pcov = np.polyfit(x, y, polydeg, cov=True)
                    except:
                        logger.error("Polynomial fit failed!")
                        raise
                else:
                    try:
                        popt, pcov = np.polyfit(x, y, polydeg, w=1/yerr,
                                                cov=True)
                    except:
                        logger.error("Polynomial fit failed!")
                        raise

            fitline = np.polyval(popt, x)
            fitline_fine = np.polyval(popt, x_fine)

            # find extreme points of the polynomial and store them
            roots = np.roots(np.polyder(popt))
            extrema = np.real(roots[np.imag(roots) == 0])
            # ignore extreme values outside the range of the input x
            extrema = extrema[np.logical_and(extrema <= np.amax(x),
                                             extrema >= np.amin(x))]
            extrema_vals = np.polyval(popt, extrema)
            # check to see if we have extrema, if not then manually set to None
            if extrema.size > 0:        
                self.fitresults['max'] = np.amax(extrema_vals)
                self.fitresults['min'] = np.amin(extrema_vals)
                self.fitresults['maxloc'] = extrema[np.argmax(extrema_vals)]
                self.fitresults['minloc'] = extrema[np.argmin(extrema_vals)]
                self.fitresults['extrema_locs'] = extrema
                self.fitresults['extrema_vals'] = extrema_vals
            else:
                self.fitresults['max'] = None
                self.fitresults['min'] = None
                self.fitresults['maxloc'] = None
                self.fitresults['minloc'] = None
                self.fitresults['extrema_locs'] = extrema
                self.fitresults['extrema_vals'] = extrema_vals
            for k in ['max', 'min', 'maxloc', 'minloc', 'extrema_locs',
                      'extrema_vals']:
                setattr(self, k, self.fitresults[k])

            pnames = []
            perrnames = []
            for i in range(self.polydeg+1):
                pnames.append('c'+str(polydeg-i))
                perrnames.append('c'+str(polydeg-i)+'_err')

            # Store fitted parameters and uncertainties
            PolyParams = namedtuple('Params', pnames)
            PolyErrs = namedtuple('Errs', perrnames)
            self.params = PolyParams(*popt)
            self.errs = PolyErrs(*np.diag(pcov)**0.5)
            self.popt = popt
            self.covmat = pcov
            self.fitresults['popt'] = popt
            self.fitresults['covmat'] = pcov
            self.fitresults['params'] = self.params._asdict()
            self.fitresults['errs'] = self.errs._asdict()
            for k, v in self.params._asdict().items():
                setattr(self, k, v)
                self.fitresults[k] = v
            for k, v in self.errs._asdict().items():
                setattr(self, k, v)
                self.fitresults[k] = v

        elif func.__name__ == 'Spline':
            # smoothing spline fits use a separate fit procedure as well
            # use quartic spline so we can find minima/maxima via roots
            # of deriv, which requires deriv to be cubic

            # explicit spline knots may not include endpoints
            t = np.linspace(x[0], x[-1], knots)[1:-1]
            
            if yerr is not None:
                if np.any(np.less_equal(yerr, [0])):
                    logger.warning("Zero or negative \'yerr\' values " +
                                   "provided!\nIgnoring \'yerr\', performing "+
                                   "unweighted fit.")
                    yerr = None
                    
            try:
                splresult = LSQUnivariateSpline(x, y, t, w=yerr, k=4)
            except:
                logger.error("Spline fit failed!")
                raise

            fitline = splresult(x)
            fitline_fine = splresult(x_fine)
            # find the extreme points of the spline and store them
            extrema = splresult.derivative(1).roots()
            self.fitresults['max'] = np.amax(splresult(extrema))
            self.fitresults['min'] = np.amin(splresult(extrema))
            self.fitresults['maxloc'] = extrema[np.argmax(splresult(extrema))]
            self.fitresults['minloc'] = extrema[np.argmin(splresult(extrema))]
            self.fitresults['extrema_locs'] = extrema
            self.fitresults['extrema_vals'] = splresult(extrema)
            self.fitresults['splobj'] = splresult
            for k in ['max', 'min', 'maxloc', 'minloc', 'extrema_locs',
                      'extrema_vals', 'splobj']:
                setattr(self, k, self.fitresults[k])

        else:
            # functions other than polynomials or splines need to use
            # scipy.optimize.curve_fit which requires initial guesses
            guess, bounds, x_scale = func.autoguess(x, y, hold, man_guess,
                                                    man_bounds, man_scale)
            self.guess = guess
            self.bounds = bounds
            self.x_scale = x_scale
            self.fitresults['guess'] = guess
            self.fitresults['bounds'] = bounds
            self.fitresults['x_scale'] = x_scale

            # housekeeping for holding fit parameters fixed
            self.hold = hold
            self.fitresults['hold'] = hold
            holdvec, holdvals = self._make_hold_vector()

            # wrap the fitting function to allow fitting to only a subset of
            # parameters, with the rest held fixed at user-defined values
            def _wrap_func(x, *params):
                if hold:
                    fullparams = []
                    param_count = 0
                    for i in range(len(holdvec)):
                        if holdvec[i]:  # get from hold, won't be varied
                            fullparams.append(holdvals[i])
                        else:  # get from input, will be varied
                            fullparams.append(params[param_count])
                            param_count += 1
                    return func.value(x, *np.asarray(fullparams))
                else:
                    return func.value(x, *params)

            # strip out any held parameters from guess/bounds/x_scale
            guess = guess[~holdvec]
            x_scale = x_scale[~holdvec]
            bounds = (np.asarray(bounds[0])[~holdvec],
                      np.asarray(bounds[1])[~holdvec])

            # now we fit the curve, weighted by yerr.  if there are no
            # weights provided by the user, or if the weights are invalid (zero
            # or negative) yerr is None and curve_fit() does an unweighted fit.
            if yerr is not None:
                if np.any(np.less_equal(yerr, [0])):
                    logger.warning("Zero or negative \'yerr\' values " +
                                   "provided!\nIgnoring \'yerr\', performing "+
                                   "unweighted fit.")
                    yerr = None
            # The x_scale parameter is important for producing robust fits,
            # because the values of the fit parameters can vary widely.  The
            # use of x_scale is only available to us if curve_fit calls
            # least_squares() instead of leastsq(), so we fix the method
            # as 'trf' to enforce this.
            try:
                popt, pcov = curve_fit(_wrap_func, x, y, p0=guess, sigma=yerr,
                                       absolute_sigma=False, bounds=bounds,
                                       max_nfev=10000, x_scale=x_scale,
                                       method='trf')
            except:
                logger.error(func.__name__ + " fit failed!")
                raise

            # rebuild popt and pcov so they include all parameters (including
            # held parameters)
            for i in range(len(holdvec)):
                if holdvec[i]:
                    popt = np.insert(popt, i, holdvals[i])
                    n = np.shape(pcov)[0]
                    col = np.zeros((n, 1))
                    row = np.zeros((1, n+1))
                    pcov = np.concatenate((pcov[:, 0:i], col, pcov[:, i:]),
                                          axis=1)
                    pcov = np.concatenate((pcov[0:i, :], row, pcov[i:, :]),
                                          axis=0)

            fitline = func.value(x, *popt)  # generate lines of best fit
            fitline_fine = func.value(x_fine, *popt)

            # find out the names of the parameters of the fit function
            pnames = func.names()
            perrnames = []
            for name in pnames:
                perrnames.append(name+'_err')

            # Store fit parameters and uncertainties
            FuncParams = namedtuple('Params', pnames)
            FuncErrs = namedtuple('Errs', perrnames)
            self.params = FuncParams(*popt)
            self.errs = FuncErrs(*np.diag(pcov)**0.5)
            self.popt = popt
            self.covmat = pcov
            self.fitresults['popt'] = popt
            self.fitresults['covmat'] = pcov
            self.fitresults['params'] = self.params._asdict()
            self.fitresults['errs'] = self.errs._asdict()
            for k, v in self.params._asdict().items():
                setattr(self, k, v)
                self.fitresults[k] = v
            for k, v in self.errs._asdict().items():
                setattr(self, k, v)
                self.fitresults[k] = v

        # all fit types: store lines of best fit
        self.fitresults['fitline'] = fitline
        self.fitresults['x_fine'] = x_fine
        self.fitresults['fitline_fine'] = fitline_fine
        self.fitresults['fit_good'] = True
        for k in ['fitline', 'x_fine', 'fitline_fine', 'fit_good']:
            setattr(self, k, self.fitresults[k])

        return self.fitresults

    def _make_hold_vector(self):
        """Look up all parameters in hold dictionary, create arrays for masking
        and providing values of held parameters as appropriate for func"""
        names = self.func.names()
        holdvec = [False] * len(names)
        holdvals = [0] * len(names)
        for i, name in enumerate(names):
            if self.hold:
                for k, v in self.hold.items():
                    if k == name:
                        holdvec[i] = True
                        holdvals[i] = v

        return np.asarray(holdvec), np.asarray(holdvals)

    def conf_band(self, x, conf=0.95):
        """Calculates confidence bands on line of best fit at locations x with
        specified confidence interval.

        See Tellinghuisen, J. Phys. Chem. A 105, 3917 (2001)
        http://dx.doi.org/10.1021/jp003484u

        NIST Engineering Statistics Handbook Section 2.5.5
        http://www.itl.nist.gov/div898/handbook/mpc/section5/mpc55.htm

        Parameters:
        -------------
        x : values of independent variable x at which to evaluate confidence
            interval.  Can be scalar or 1-d array.
        conf : confidence level for confidence bands, between 0 and 1

        Outputs:
        -------------
        ysigma : standard deviation in list of best fit at location(s) x
        yupper : upper confidence band for line of best fit at specified
                 confidence level.
        ylower : lower confidence band for line of best fit at specified
                 confidence level.
        """
        # errors on fit line and parameters are not relevant for spline fits
        if self.func.__name__ == 'Spline':
            logger.error("No confidence bands for smoothing splines!")
            return
        elif self.fit_good is False:
            logger.error("No valid fit parameters for calculating confidence" + 
                        " bands!")
            return

        # calculate partial derivatives wrt all fit parameters at locations x
        d = self.func.jacobian(x, *self.popt)
        # faster throwing away off-diagonal elements than using a for loop
        yvar = np.diag(d.dot(self.covmat).dot(d.T))
        ysigma = np.sqrt(yvar)  # turn variances into std devs.
        yupper = self.value(x) + erfinv(conf)*np.sqrt(2)*ysigma
        ylower = self.value(x) - erfinv(conf)*np.sqrt(2)*ysigma

        return ysigma, yupper, ylower

    def fitline_conf(self, conf=.95, fine=False):
        """Calculates confidence bands for lines of best fit.  The user should
        be careful that if parameters are held during fitting, the confidence
        bands assume there is no uncertainty in these parameters and no
        covariance with other parameters, which may not be a valid assumption.

        inputs:
        -------------
        conf - confidence level for fit error bars, between 0 and 1.
        fine - Boolean, make confidence bands on the fine fit line as well

        Attributes set by fitline_conf()
        -------------
        ysigma - 1-d numpy array of standard deviations in y values of line of
                best fit
        ysigma_fine - same as ysigma for for fitline_fine
        yupper - upper error bar for best fit line at specified confidence
        yupper_fine - same as yupper for for fitline_fine
        ylower - lower error bar for best fit line at specified confidence
        ylower_fine - same as lower for for fitline_fine
        """
        # errors on fit line and parameters are not relevant for spline fits
        if self.func.__name__ == 'Spline':
            logger.error("No confidence bands for smoothing splines!")
            self.fitresults['ysigma'] = 0.*self.fitline
            self.fitresults['yupper'] = self.fitline
            self.fitresults['ylower'] = self.fitline
            for k in ['ysigma', 'yupper', 'ylower']:
                setattr(self, k, self.fitresults[k])
            if fine is True:
                self.fitresults['ysigma_fine'] = 0.*self.fitline_fine
                self.fitresults['yupper_fine'] = self.fitline_fine
                self.fitresults['ylower_fine'] = self.fitline_fine
                for k in ['ysigma_fine', 'yupper_fine', 'ylower_fine']:
                    setattr(self, k, self.fitresults[k])
            return
        elif self.fit_good is False:
            logger.error("No valid fit parameters for calculating confidence" +
                         " bands!")
            return

        ysigma, yupper, ylower = self.conf_band(self.x, conf)

        self.fitresults['ysigma'] = ysigma
        self.fitresults['yupper'] = yupper
        self.fitresults['ylower'] = ylower
        for k in ['ysigma', 'yupper', 'ylower']:
            setattr(self, k, self.fitresults[k])

        if fine is True:
            ysigma_fine, yupper_fine, ylower_fine = self.conf_band(self.x_fine,
                                                                   conf)

            self.fitresults['ysigma_fine'] = ysigma_fine
            self.fitresults['yupper_fine'] = yupper_fine
            self.fitresults['ylower_fine'] = ylower_fine
            for k in ['ysigma_fine', 'yupper_fine', 'ylower_fine']:
                setattr(self, k, self.fitresults[k])

###############################################################################
# Fit function classes below this line
###############################################################################


class FitFunction():
    """Parent class for all fit functions, wrapping shared functionality"""
    def __init__():
        pass

    @classmethod
    def names(cls):
        return []  # override in subclass

    @classmethod
    def autoguess_outputs(cls, g, xsc, bounds, hold, man_guess, man_bounds,
                          man_scale):
        """Combine autoguess, default bounds, and autoscale with any manual
        overrides of these in a form suitable for scipy.curve_fit.  Issue
        warnings for any invalid parameter names, or if manual guesses, bounds,
        and/or scale are provided for any parameters being held."""

        names = cls.names()  # list of parameter names defined in subclass

        # if manual guesses are provided, replace autoguesses with manual
        if man_guess:
            for k, v in man_guess.items():
                if k in names:
                    if k in hold.keys():
                        logger.warning('\'' + k + '\' is being held, manual ' +
                                       'guess ignored!')
                    else:
                        g[k] = v
                else:
                    logger.warning('\'' + k + '\' is not a valid parameter ' +
                                   'name for man_guess!')

        # if manual scales are provided, replace autoscale with manual
        if man_scale:
            for k, v in man_scale.items():
                if k in names:
                    if k in hold.keys():
                        logger.warning('\'' + k + '\' is being held, manual ' +
                                       'scale ignored!')
                    else:
                        if v <= 0:
                            logger.warning('Manual scale for \'' + k +
                                           '\' must be greater than zero.\n' +
                                    'Ignoring manual scale for \'' + k + '\'.')
                        elif np.isinf(v):
                            logger.warning('Manual scale for \'' + k +
                                  '\' cannot be infinite.\nIgnoring manual ' +
                                  'scale for \'' + k + '\'.')
                        else:
                            xsc[k] = v
                else:
                    logger.warning('\'' + k + '\' is not a valid parameter ' +
                                   'name for man_scale!')

        # replace default bounds with any user-supplied manual bounds
        if man_bounds:
            for k, v in man_bounds.items():
                if k in names:
                    if k in hold.keys():
                        logger.warning('\'' + k + '\' is being held, manual ' +
                                       'scale ignored!')
                    elif len(v) != 2:
                        logger.warning('Bounds for \'' + k + '\' must have ' +
                                       'exactly two elements [lower, upper].' +
                                       '\nIgnoring manual bounds for \'' + 
                                       k + '\'.')
                    elif v[0] >= v[1]:
                        logger.warning('Lower bound for \'' + k + '\' must ' +
                                       'be strictly less than upper bound.' +
                                       '\nIgnoring manual bounds for \'' + 
                                       k + '\'.')
                    elif g[k] <= v[0] or g[k] >= v[1]:
                        logger.warning('Initial guess for \'' + k + '\' ' + 
                                       'must be between manual bounds.' +
                                       '\nIgnoring manual bounds for \'' + 
                                       k + '\'.\nProvide suitable manual ' +
                                       'guess between bounds.')
                    else:
                        bounds[0][names.index(k)] = v[0]
                        bounds[1][names.index(k)] = v[1]
                else:
                    logger.warning('\'' + k + '\' is not a valid parameter ' +
                                   'name for man_bounds!')
        # construct guess and x_scale output arrays
        guess = np.zeros(np.shape(names))
        x_scale = np.zeros(np.shape(names))
        for i, n in enumerate(names):
            x_scale[i] = xsc[n]
            guess[i] = g[n]

        return guess, bounds, x_scale


class Poly(FitFunction):
    """Class for fitting to polynomial functions
    Coefficients ci are numbered as below:

    f(x) = c0 + (c1 * x) + (c2 * x^2) + ... + (cn * x^n)

    List of fit parameters is in order [cn, .... , c1, c0]
    """
    @staticmethod
    def value(x, pcoeff):
        return np.polyval(pcoeff, x)

    @staticmethod
    def jacobian(x, *args):
        '''Jacobian for polynomial is x**n for the coefficient cn.'''
        ncoeff = len(list(args))
        xs = np.atleast_1d(x)
        jacmat = np.zeros((len(xs), ncoeff))
        for i in range(len(xs)):
            for j in range(ncoeff):
                jacmat[i, j] = xs[i]**(ncoeff-j-1)
        return jacmat


class Spline(FitFunction):
    """Class for smoothing spline fit with n knots.  This is a dummy, just used
    as a name to pass in.  All the "guts" are handled by scipy spline routines.
    """
    def __init__():
        pass


class ExpSine(FitFunction):
    """Class for fitting to exponentially decaying sine
    of form A * sin(2pi*f*t + phi) * exp(-t/tau) + y0
    A and f are defined to be always positive numbers.
    """
    @classmethod
    def names(cls):
        """Valid parameter names for this function type, in order for value()
        method arguments"""
        return ['A', 'f', 'tau', 'phi', 'y0']

    @staticmethod
    def value(t, A, f, tau, phi, y0):
        """Value of exponentially decaying sine at time t"""
        return (A*np.sin(2*np.pi*f*t+phi)*np.exp(-t/tau)+y0)

    @staticmethod
    def jacobian(tdata, A, f, tau, phi, y0):
        """Returns Jacobian matrix of partial derivatives of
        A * sin(2pi*f*t + phi) * exp(-t/tau) + y0, evaluated for all
        values t in tdata, which can be a 1d array or a scalar. Rows are
        separate values of t, columns are partial derivatives w.r.t.
        different parameters
        """
        ts = np.atleast_1d(tdata)
        jacmat = np.zeros((ts.shape[0], 5))
        for i, t in enumerate(ts):
            jacmat[i, 0] = np.sin(2*np.pi*f*t+phi)*np.exp(-t/tau)  # dy/dA
            jacmat[i, 1] = (2*np.pi*t*A*np.cos(2*np.pi*f*t+phi)
                            * np.exp(-t/tau))  # dy/df
            jacmat[i, 2] = (t/(tau**2)*A*np.sin(2*np.pi*f*t+phi)
                            * np.exp(-t/tau))  # dy/dtau
            jacmat[i, 3] = A*np.cos(2*np.pi*f*t+phi)*np.exp(-t/tau)  # dy/dphi
            jacmat[i, 4] = 1.  # dy/dy0

        return jacmat

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
        g['A'] = (np.amax(y) - np.amin(y))/2
        g['y0'] = (np.amax(y)+np.amin(y))/2
        # strip DC level, take FFT, use only positive frequency components
        yfft = fft(y - np.mean(y))[0:len(y)//2]
        # don't guess zero frequency, will cause fit to fail
        g['f'] = (1./(np.amax(t)-np.amin(t))
                  * max(1, np.argmax(np.absolute(yfft))))
        g['tau'] = (np.amax(t)-np.amin(t))/4.
        g['phi'] = 1.5 if y[0] > g['y0'] else 4.7

        # default bounds: constrain A, f to be positive
        bounds = ([0, 0, -np.inf, -np.inf, -np.inf],
                  [np.inf, np.inf, np.inf, np.inf, np.inf])

        # generate rough natural scale values
        xsc = {}
        xsc['A'] = g['A']
        xsc['f'] = g['f']
        xsc['tau'] = g['tau']
        xsc['phi'] = 3.1
        xsc['y0'] = g['A']

        return cls.autoguess_outputs(g, xsc, bounds, hold, man_guess,
                                     man_bounds, man_scale)


class Exp2Sine(FitFunction):
    """Class for fitting to Gaussian decaying sine
    of form A * sin(2pi*f*t + phi) * exp(-(t/tau)^2) + y0
    """
    @classmethod
    def names(cls):
        """Valid parameter names for this function type, in order for value()
        method arguments"""
        return ['A', 'f', 'tau', 'phi', 'y0']

    @staticmethod
    def value(t, A, f, tau, phi, y0):
        """Value of Gaussian decaying sine at time t"""
        return (A*np.sin(2*np.pi*f*t+phi)*np.exp(-(t/tau)**2)+y0)

    @staticmethod
    def jacobian(tdata, A, f, tau, phi, y0):
        """Returns Jacobian matrix of partial derivatives of
        A * sin(2pi*f*t + phi) * exp(-(t/tau)^2) + y0, evaluated for all values
        t in tdata, which can be a 1d array or a scalar. Rows are separate
        values of t, columns are partial derivatives w.r.t. different params
        """
        ts = np.atleast_1d(tdata)
        jacmat = np.zeros((ts.shape[0], 5))
        for i, t in enumerate(ts):
            jacmat[i, 0] = np.sin(2*np.pi*f*t+phi)*np.exp(-(t/tau)**2)  # dy/dA
            jacmat[i, 1] = (2*np.pi*t*A*np.cos(2*np.pi*f*t+phi)
                            * np.exp(-(t/tau)**2))  # dy/df
            jacmat[i, 2] = (2*t**2/(tau**3)*A*np.sin(2*np.pi*f*t+phi)
                            * np.exp(-(t/tau)**2))  # dy/dtau
            jacmat[i, 3] = (A*np.cos(2*np.pi*f*t+phi)
                            * np.exp(-(t/tau)**2))  # dy/dphi
            jacmat[i, 4] = 1.  # dy/dy0

        return jacmat

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
        g['A'] = (np.amax(y) - np.amin(y))/2
        g['y0'] = (np.amax(y)+np.amin(y))/2
        # strip DC level, take FFT, use only positive frequency components
        yfft = fft(y - np.mean(y))[0:len(y)//2]
        # don't guess zero frequency, will cause fit to fail
        g['f'] = (1./(np.amax(t)-np.amin(t))
                  * max(1, np.argmax(np.absolute(yfft))))
        g['tau'] = (np.amax(t)-np.amin(t))/2.
        g['phi'] = 1.5 if y[0] > g['y0'] else 4.7

        # default bounds: constrain A, f to be positive
        bounds = ([0., 0., -np.inf, -np.inf, -np.inf], [np.inf, np.inf, np.inf,
                  np.inf, np.inf])

        # generate rough natural scale values
        xsc = {}
        xsc['A'] = g['A']
        xsc['f'] = g['f']
        xsc['tau'] = g['tau']
        xsc['phi'] = 3.1
        xsc['y0'] = g['A']

        return cls.autoguess_outputs(g, xsc, bounds, hold, man_guess,
                                     man_bounds, man_scale)


class Sine(FitFunction):
    """Class for fitting to sine wave A * sin(2pi*f*t + phi) + y0
    """
    @classmethod
    def names(cls):
        """Valid parameter names for this function type, in order for value()
        method arguments"""
        return ['A', 'f', 'phi', 'y0']

    @staticmethod
    def value(t, A, f, phi, y0):
        """Value of sine at time t"""
        return (A*np.sin(2*np.pi*f*t+phi)+y0)

    @staticmethod
    def jacobian(tdata, A, f, phi, y0):
        """Returns Jacobian matrix of partial derivatives of
        A * sin(2pi*f*t + phi) + y0, evaluated for all values t
        in tdata, which can be a 1d array or a scalar. Rows are separate values
        of t, columns are partial derivatives w.r.t. different parameters
        """
        ts = np.atleast_1d(tdata)
        jacmat = np.zeros((ts.shape[0], 4))
        for i, t in enumerate(ts):
            jacmat[i, 0] = np.sin(2*np.pi*f*t+phi)  # dy/dA
            jacmat[i, 1] = 2*np.pi*t*A*np.cos(2*np.pi*f*t+phi)  # dy/df
            jacmat[i, 2] = A*np.cos(2*np.pi*f*t+phi)  # dy/dphi
            jacmat[i, 3] = 1.  # dy/dy0

        return jacmat

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
        g['A'] = (np.amax(y) - np.amin(y))/2
        g['y0'] = (np.amax(y)+np.amin(y))/2
        # strip DC level, take FFT, use only positive frequency components
        yfft = fft(y - np.mean(y))[0:len(y)//2]
        # don't guess zero frequency, will cause fit to fail
        g['f'] = (1./(np.amax(t)-np.amin(t))
                  * max(1, np.argmax(np.absolute(yfft))))
        g['phi'] = 1.5 if y[0] > g['y0'] else 4.7

        # default bounds: constrain A, f to be positive
        bounds = ([0., 0., -np.inf, -np.inf], [np.inf, np.inf, np.inf,
                  np.inf])

        # generate rough natural scale values
        xsc = {}
        xsc['A'] = g['A']
        xsc['f'] = g['f']
        xsc['phi'] = 3.1
        xsc['y0'] = g['A']

        return cls.autoguess_outputs(g, xsc, bounds, hold, man_guess,
                                     man_bounds, man_scale)


class Sin4(FitFunction):
    """Class for fitting to sin^4: A * (sin(2pi*f*t + phi))^4 + y0
    """
    @classmethod
    def names(cls):
        """Valid parameter names for this function type, in order for value()
        method arguments"""
        return ['A', 'f', 'phi', 'y0']

    @staticmethod
    def value(t, A, f, phi, y0):
        """Value of sine^4 at time t"""
        return (A*(np.sin(2*np.pi*f*t+phi))**4+y0)

    @staticmethod
    def jacobian(tdata, A, f, phi, y0):
        """Returns Jacobian matrix of partial derivatives of
        A * (sin(2pi*f*t + phi))^4 + y0, evaluated for all values t
        in tdata, which can be a 1d array or a scalar. Rows are separate values
        of t, columns are partial derivatives w.r.t. different parameters
        """
        ts = np.atleast_1d(tdata)
        jacmat = np.zeros((ts.shape[0], 4))
        for i, t in enumerate(ts):
            jacmat[i, 0] = (np.sin(2*np.pi*f*t+phi))**4  # dy/dA
            jacmat[i, 1] = (4*A*(np.sin(2*np.pi*f*t+phi))**3
                             * (np.cos(2*np.pi*f*t+phi))*2*np.pi*t)  # dy/df
            jacmat[i, 2] = (4*A*(np.sin(2*np.pi*f*t+phi))**3
                             * (np.cos(2*np.pi*f*t+phi)))  # dy/dphi
            jacmat[i, 3] = 1.  # dy/dy0

        return jacmat

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
        g['A'] = (np.amax(y) - np.amin(y))
        g['y0'] = np.amin(y)
        # strip DC level, take FFT, use only positive frequency components
        yfft = fft(y - np.mean(y))[0:len(y)//2]
        # don't guess zero frequency, will cause fit to fail
        g['f'] = (0.5/(np.amax(t)-np.amin(t))
                  * max(1, np.argmax(np.absolute(yfft))))
        g['phi'] = 1.5 if y[0] > g['y0'] else 0.

        # default bounds: constrain A, f to be positive
        bounds = ([0., 0., -np.inf, -np.inf], [np.inf, np.inf, np.inf,
                  np.inf])

        # generate rough natural scale values
        xsc = {}
        xsc['A'] = g['A']
        xsc['f'] = g['f']
        xsc['phi'] = 3.1
        xsc['y0'] = g['A']

        return cls.autoguess_outputs(g, xsc, bounds, hold, man_guess,
                                     man_bounds, man_scale)


class Lor(FitFunction):
    """Class for fitting to Lorentzian A * Gamma^2/((x-x0)^2+Gamma^2) + y0
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
        return (A * Gamma**2/((x-x0)**2+Gamma**2)+y0)

    @staticmethod
    def jacobian(xdata, A, Gamma, x0, y0):
        """Returns Jacobian matrix of partial derivatives of
        A * Gamma^2/((x-x0)^2+Gamma^2) + y0, evaluated for all values x
        in xdata, which can be a 1d array or a scalar. Rows are separate values
        of x, columns are partial derivatives w.r.t. different parameters
        """
        xs = np.atleast_1d(xdata)
        jacmat = np.zeros((xs.shape[0], 4))
        for i, x in enumerate(xs):
            jacmat[i, 0] = Gamma**2/((x-x0)**2+Gamma**2)  # dy/dA
            jacmat[i, 1] = (2*A*Gamma*(x-x0)**2
                            / ((x-x0)**2+Gamma**2)**2)  # dy/dGamma
            jacmat[i, 2] = (2*A*(x-x0)*Gamma**2
                            / ((x-x0)**2+Gamma**2)**2)  # dy/dx0
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
        up = True if (p80-mid > mid-p20) else False  # pointing up or down?

        # pick a range that avoids edges to avoid accidentally guessing
        # edges as a peak
        xfrac = 0.1
        xmin = np.amin(x)
        xmax = np.amax(x)
        xlo = (xmax-xmin)*xfrac+xmin
        xhi = xmax-(xmax-xmin)*xfrac

        # construct autoguess values
        g = {}
        g['A'] = amax-mid if up else amin-mid  # peak to midline
        g['Gamma'] = (np.amax(x)-np.amin(x))/6.
        # guess max or min values for peak center, unless too close to the edge
        # in which case use the middle value
        if up and xlo < x[np.argmax(y)] < xhi:
            g['x0'] = x[np.argmax(y)]
        elif not up and xlo < x[np.argmin(y)] < xhi:
            g['x0'] = x[np.argmin(y)]
        else:
            g['x0'] = (xmax+xmin)/2.
        g['y0'] = mid

        # default bounds: constrain Gamma to be positive
        bounds = ([-np.inf, 0., -np.inf, -np.inf], [np.inf, np.inf, np.inf,
                  np.inf])

        # generate rough natural scale values
        xsc = {}
        xsc['A'] = np.absolute(g['A'])
        if xsc['A'] <= 0:
            xsc['A'] = 1
        xsc['Gamma'] = g['Gamma']
        if xsc['Gamma'] <= 0:
            xsc['Gamma'] = 1
        xsc['x0'] = max(np.absolute(xmax), np.absolute(xmin))
        if xsc['x0'] <= 0:
            xsc['x0'] = 1
        xsc['y0'] = np.absolute(g['A'])
        if xsc['y0'] <= 0:
            xsc['y0'] = 1

        return cls.autoguess_outputs(g, xsc, bounds, hold, man_guess,
                                     man_bounds, man_scale)


class Gauss(FitFunction):
    """Class for fitting to Gaussian A * exp(-(x-x0)^2/(2*sigma^2)) + y0
    """
    @classmethod
    def names(cls):
        """Valid parameter names for this function type, in order for value()
        method arguments"""
        return ['A', 'sigma', 'x0', 'y0']

    @staticmethod
    def value(x, A, sigma, x0, y0):
        """Value of Gaussian at x"""
        return (A*np.exp(-(x-x0)**2/(2*sigma**2))+y0)

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
            jacmat[i, 0] = np.exp(-(x-x0)**2/(2*sigma**2))  # dy/dA
            jacmat[i, 1] = (A*(x-x0)**2*np.exp(-(x-x0)**2/(2*sigma**2))
                            / (sigma**3))  # dy/dsigma
            jacmat[i, 2] = (A*(x-x0)*np.exp(-(x-x0)**2/(2*sigma**2))
                            / (sigma**2))  # dy/dx0
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
        g['sigma'] = (np.amax(x)-np.amin(x))/6.
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
        bounds = ([-np.inf, 0., -np.inf, -np.inf], [np.inf, np.inf, np.inf,
                  np.inf])

        # generate rough natural scale values
        xsc = {}
        xsc['A'] = np.absolute(g['A'])
        xsc['sigma'] = g['sigma']
        xsc['x0'] = max(np.absolute(xmax), np.absolute(xmin))
        xsc['y0'] = np.absolute(g['A'])

        return cls.autoguess_outputs(g, xsc, bounds, hold, man_guess,
                                     man_bounds, man_scale)


class AtomLine(FitFunction):
    """Wrapper class for fitting to pulsed lineshape for atomic resonances
    vs probe frequency: A * (2*pi*Omega0)^2/Omega^2 * sin^2(Omega*T/2) + y0
    - Omega0 is Rabi frequency on resonance in Hz (not angular frequency)
    - f0 is resonance frequency in Hz (not angular frequency)
    - Omega = 2*pi*sqrt(Omega0^2 + (f-f0)^2) (angular frequency)
    - T is pulse duration in sec.
    - A and y0 are scaling factor and offset
    """
    @classmethod
    def names(cls):
        """Valid parameter names for this function type, in order for value()
        method arguments"""
        return ['A', 'Omega0', 'T', 'f0', 'y0']

    @staticmethod
    def value(f, A, Omega0, T, f0, y0):
        """Value of lineshape at f"""
        Omega = 2*np.pi*np.sqrt(Omega0**2 + (f-f0)**2)
        return (A*(2*np.pi*Omega0)**2/Omega**2*(np.sin(Omega*T/2))**2 + y0)

    @staticmethod
    def jacobian(fdata, A, Omega0, T, f0, y0):
        """Returns Jacobian matrix of partial derivatives of
        A * Omega0^2/Omega^2 * sin^2(Omega*T/2) + y0, where
        Omega = sqrt(Omega0^2 + (2*pi*f-2*pi*f0)^2).  Derivatives are evaluated
        for all values f in fdata, which can be a 1d array or a scalar. Rows
        are separate values of f, columns are partial derivatives w.r.t.
        different parameters
        """
        fs = np.atleast_1d(fdata)
        jacmat = np.zeros((fs.shape[0], 5))
        for i, f in enumerate(fs):
            Omega = 2*np.pi*np.sqrt(Omega0**2 + (f-f0)**2)
            s = np.sin(Omega*T/2)
            c = np.cos(Omega*T/2)
            jacmat[i, 0] = (2*np.pi*Omega0)**2/Omega**2 * s**2  # dy/dA
            jacmat[i, 1] = (A*(2*np.pi*Omega0/Omega)**3*T*c*s  # dy/dOmega0
                            - 2*A*(2*np.pi*Omega0)**3/Omega**4*s**2
                            + 2*A*(2*np.pi*Omega0)/Omega**2*s**2)
            jacmat[i, 2] = A*(2*np.pi*Omega0)**2/Omega*s*c  # dy/dT
            jacmat[i, 3] = (4*A*(f-f0)*(2*np.pi*Omega0)**2*np.pi**2*s
                            * (2*s/Omega**4 - T*c/Omega**3))  # dy/df0
            jacmat[i, 4] = 1.  # dy/dy0

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
        g['Omega0'] = (np.amax(x)-np.amin(x))/8.
        g['A'] = amax-mid if up else amin-mid  # peak to midline
        g['T'] = 4./(np.amax(x)-np.amin(x))
        # guess max or min values for peak center, unless too close to the edge
        # in which case use the middle value
        if up and xlo < x[np.argmax(y)] < xhi:
            g['f0'] = x[np.argmax(y)]
        elif not up and xlo < x[np.argmin(y)] < xhi:
            g['f0'] = x[np.argmin(y)]
        else:
            g['f0'] = (xmax+xmin)/2.
        g['y0'] = mid

        # default bounds: constrain Omega0, T to be positive, A to be no more
        # than 1.5 times the max depth now.
        bounds = ([1.5*(amin-amax), 0., 0., -np.inf, -np.inf],
                  [1.5*(amax-amin), np.inf, np.inf, np.inf, np.inf])

        # generate rough natural scale values
        xsc = {}
        xsc['A'] = np.absolute(g['A'])
        xsc['Omega0'] = g['Omega0']
        xsc['T'] = g['T']
        xsc['f0'] = max(np.absolute(xmax), np.absolute(xmin))
        xsc['y0'] = np.absolute(g['A'])

        return cls.autoguess_outputs(g, xsc, bounds, hold, man_guess,
                                     man_bounds, man_scale)


class Exp(FitFunction):
    """Wrapper class for fitting to  A * exp(x*b) + y0.
    Note that putting an offset (x-x0) in the exponent is mathematically
    equivalent to rescaling A, so no x offset is provided in this function.
    """
    @classmethod
    def names(cls):
        """Valid parameter names for this function type, in order for value()
        method arguments"""
        return ['A', 'b', 'y0']

    @staticmethod
    def value(x, A, b, y0):
        """Value of exponential at x"""
        return (A*np.exp(x*b) + y0)

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
            jacmat[i, 0] = np.exp(x*b)  # dy/dA
            jacmat[i, 1] = A*x*np.exp(x*b)  # dy/db
            jacmat[i, 2] = 1.  # dy/dy0

        return jacmat

    @classmethod
    def autoguess(cls, x, y, hold={}, man_guess={}, man_bounds={},
                  man_scale={}):
        """Returns automated guesses for fit parameter starting points and
        bounds for parameter search.  Manual guesses, bounds, and scales
        provided in dictionaries will override automatic values unless
        named parameter is being held. Valid keyword names are in cls.names()
        """
        yi = y[0]
        yf = y[-1]
        ymid = y[round(len(y)/2)]

        # construct autoguess values
        g = {}
        if yi > yf:
            if (yi-ymid) > (ymid-yf):
                g['A'] = yi - yf
                g['b'] = -2/(x[-1]-x[0])
                g['y0'] = yf
            else:
                g['A'] = yf - yi
                g['b'] = 2/(x[-1]-x[0])
                g['y0'] = yi
        else:
            if (yf-ymid) > (ymid-yi):
                g['A'] = yf - yi
                g['b'] = 2/(x[-1]-x[0])
                g['y0'] = yi
            else:
                g['A'] = yi - yf
                g['b'] = -2/(x[-1]-x[0])
                g['y0'] = yf

        # default bounds: unbounded optimization
        bounds = ([-np.inf, -np.inf, -np.inf], [np.inf, np.inf, np.inf])

        # generate rough natural scale values
        xsc = {}
        xsc['A'] = np.absolute(g['A'])
        xsc['b'] = np.absolute(g['b'])
        xsc['y0'] = np.absolute(g['A'])

        return cls.autoguess_outputs(g, xsc, bounds, hold, man_guess,
                                     man_bounds, man_scale)


class Power(FitFunction):
    """Wrapper class for fitting to power law  A * x^alpha + y0
    Only works for positive values of A, and positive values of x.  If data
    has A<0, fit to (x, -y) instead of (x,y).
    """
    @classmethod
    def names(cls):
        """Valid parameter names for this function type, in order for value()
        method arguments"""
        return ['A', 'alpha', 'y0']

    @staticmethod
    def value(x, A, alpha, y0):
        """Value of power law at x"""
        return (A*x**alpha+y0)

    @staticmethod
    def jacobian(xdata, A, alpha, y0):
        """Returns Jacobian matrix of partial derivatives of
        A * x^alpha + y0, evaluated for all values x
        in xdata, which can be a 1d array or a scalar. Rows are separate values
        of x, columns are partial derivatives w.r.t. different parameters
        """
        xs = np.atleast_1d(xdata)
        jacmat = np.zeros((xs.shape[0], 3))
        for i, x in enumerate(xs):
            jacmat[i, 0] = x**alpha  # dy/dA
            jacmat[i, 1] = A*np.log(x)*x**(alpha)  # dy/dalpha
            jacmat[i, 2] = 1.  # dy/dy0

        return jacmat

    @classmethod
    def autoguess(cls, x, y, hold={}, man_guess={}, man_bounds={},
                  man_scale={}):
        """Returns automated guesses for fit parameter starting points and
        bounds for parameter search.  Manual guesses, bounds, and scales
        provided in dictionaries will override automatic values unless
        named parameter is being held. Valid keyword names are in cls.names()
        """
        xpos = x[np.sign(x) > 0]
        ypos = y[np.sign(x) > 0]
        logx = np.log(xpos)
        logy = np.log(ypos)
        p = np.polyfit(logx, logy, deg=1)

        # construct autoguess values
        g = {}
        g['A'] = np.exp(p[1])
        g['alpha'] = p[0]
        g['y0'] = np.amin(ypos)/10.

        # default bounds: require A to be positive
        bounds = ([0, -np.inf, -np.inf], [np.inf, np.inf, np.inf])

        # generate rough natural scale values
        xsc = {}
        xsc['A'] = np.absolute(g['A'])
        xsc['alpha'] = np.absolute(g['alpha'])
        xsc['y0'] = np.absolute(g['A'])

        return cls.autoguess_outputs(g, xsc, bounds, hold, man_guess,
                                     man_bounds, man_scale)


def main():

    import matplotlib.pyplot as plt
    import logging
    
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)
    
    """Testing basic errors
    """
    logger.info("\n\n=====Calling value or conf without fit parameters====\n")
    for func in [Spline, Poly, Lor]:
        fitobj = Fit([0,1],[0,1], func)
        try:
            fitobj.value(1)
        except:
            pass
        try:
            fitobj.fitline_conf()
        except:
            pass
        try:
            fitobj.conf_band(1)
        except:
            pass
    
    logger.info("\n\n=====Testing example noisy data curve fits====\n")
    
    
    """Quick testing for curve fits - run on simulated noisy data for all
    curve fit types.  The main purpose is to check for breaking code if
    things are refactored or updated.
    """
    # independent variables
    t = np.linspace(0, 50e-6, 40)
    f = np.linspace(2e6, 3e6, 30)
    f2 = np.linspace(6e5, 3e6, 40)
    x = np.linspace(-2e3, 2e3, 60)
    
    # parameters and noise amplitudes
    expsinep0 = [0.6, 3e4, 26e-6, np.pi/2, 0.5]
    exp2sinep0 = [0.5, 5e4, 35e-6, 3*np.pi/2, 0.5]
    sinep0 = [0.5, 3e4, 5*np.pi/4, 0.5]
    atomlinep0 = [-0.7, 5e4, 10e-6, 2.55e6, 1.]
    gaussp0 = [0.6, 520, 300, -2]
    lorp0 = [-0.6, 800, -450, 6]
    expp0 = [1, -1e5, 2.3]
    powerp0 = [2e-6, -0.35, 2.5e-10]
    namp = 0.1
    namppow = 1.3e-9
    
    rng = np.random.default_rng()
    
    # create simulated data
    expsine = ExpSine.value(t, *expsinep0) + namp*rng.normal(size=t.shape[0])
    exp2sine = (Exp2Sine.value(t, *exp2sinep0)
                + namp*rng.normal(size=t.shape[0]))
    sine = Sine.value(t, *sinep0) + namp*rng.normal(size=t.shape[0])
    sin4 = Sin4.value(t, *sinep0) + namp*rng.normal(size=t.shape[0])
    gauss = Gauss.value(x, *gaussp0) + namp*rng.normal(size=x.shape[0])
    lor = Lor.value(x, *lorp0) + namp*rng.normal(size=x.shape[0])
    atomline = (AtomLine.value(f, *atomlinep0)
                + namp*rng.normal(size=f.shape[0]))
    exp = Exp.value(t, *expp0) + namp*rng.normal(size=t.shape[0])
    power = Power.value(f2, *powerp0) + namppow*rng.normal(size=f2.shape[0])
    
    # lists of different fit types to do to different data, with the
    # option of holding some parameters
    
    # build some sets of data and fitting options to test.
    # tuples are:
    # (x data, y data, function, holds, man_guess, man_scale, man_bounds,
    # datanames, actual parameters, kwargs for fit)
    # some tuples contain intentionally invalid values for some options
    # to test error/warning messages
    fitsets = [(t, expsine, ExpSine, {'A': 0.65}, {'A': 0.65}, {'A': -2}, 
                {'A': [-10, 10]}, 'expsine', expsinep0, {}),
               (t, exp2sine, Exp2Sine, {'f': 50000.0, 'y0': 0.5}, 
                {'f': 50000.0, 'y0': 0.5}, {'f': 50000.0, 'y0': 0}, 
                {'f': [50000.0, 40000.0], 'y0': (-np.inf,np.inf)}, 'exp2sine', 
                exp2sinep0, {}),
               (t, sine, Sine, {'tau': 0.2, 'f': 30000.0}, 
                {'tau': 0.2, 'f': 30000.0}, {'tau': 0.2, 'f': 30000.0}, {},
                'sine', sinep0, {}),
               (x, gauss, Gauss, {'sigma': 500}, {'sigma': 900}, 
                {'sigma': 500}, {'sigma': [800, 1000]}, 'gauss', gaussp0, {}),
               (x, lor, Lor, {'x0': -460}, {'x0': -460}, {'x0': 1000}, 
                {'x0': [-1000, 1100, 4], 'Gamma': [200, 400]}, 'lor', lorp0, 
                {}),
               (f, atomline, AtomLine, {'T': 1e-05, 'tau':np.inf}, 
                {'T': 5e-06, 'tau':np.inf}, {'T': 5e-06, 'tau':np.inf}, {}, 
                'atomline', atomlinep0, {}),
               (x, gauss, Poly, {}, {}, {}, {}, 'gauss', gaussp0, {}),
               (f, atomline, Spline, {}, {}, {}, {}, 'atomline', atomlinep0,
                {}),
               (x, gauss, Spline, {}, {}, {}, {}, 'gauss', gaussp0, {}),
               (t, sine, ExpSine, {'tau': 3.3e-05}, {'tau': 3.3e-05}, 
                {'tau': 3.3e-05}, {}, 'sine', sinep0, {}),
               (t, exp, Exp, {'A': 0.8}, {'A': 0.8}, {'A': 0.8, 'f':np.inf}, 
                {'Ap': [0.8, 1.2]}, 'exp', expp0, {}),
               (t, sin4, Sin4, {'y0': 0.25}, {'y0': 0.25}, {'y0': 0.25}, {}, 
                'sin4', sinep0, {}),
               (f2, power, Power, {'y0': 6e-10}, {'y0': 6e-10}, {'y0': 6e-10}, 
                {'y0': [-np.inf, 0]}, 'power', powerp0, {}),
               (x, lor, Spline, {}, {}, {}, {}, 'lor', lorp0, {}),
               (x, lor, Poly, {}, {}, {}, {}, 'lor', lorp0, {}),
               (x, lor, Poly, {}, {}, {}, {}, 'lor', lorp0, {'polydeg':1}),
               (x, lor, Spline, {}, {}, {}, {}, 'lor', lorp0, {'knots':4}),
               (f, atomline, Spline, {}, {}, {}, {}, 'atomline', atomlinep0,
                {'knots':24}),
               (f, atomline, Lor, {}, {}, {}, {}, 'atomline', atomlinep0,
                {}),
               (x, gauss, Poly, {}, {}, {}, {}, 'gauss', gaussp0, 
                {'polydeg':12})
              ]
    
    results = []
    
    # fit each data/function combo, with holds, man guesses, etc.
    for fitset in fitsets:
        xi, yi, funci, hi, gi, sci, bi, _, _, kwi = fitset
        # normal
        res = Fit(xi, yi, funci, **kwi)
        res.fit_data()
        res.fitline_conf(fine=True)
        results.append(res)
        # repeat for manual guesses
        res = Fit(xi, yi, funci, **kwi)
        res.fit_data(man_guess=gi)
        res.fitline_conf(fine=True)
        results.append(res)
        # repeat for hold parameters
        res = Fit(xi, yi, funci, **kwi)
        res.fit_data(hold=hi)
        res.fitline_conf(fine=True)
        results.append(res)
        # repeat for man scale, bounds, and guesses
        res = Fit(xi, yi, funci, **kwi)
        res.fit_data(man_scale=sci, man_bounds=bi, man_guess=gi)
        res.fitline_conf(fine=True)
        results.append(res)
    
    ncurv = len(fitsets)
    datanames = [fi[7] for fi in fitsets]
    funcs = [fi[2] for fi in fitsets]
    kws = [fi[9] for fi in fitsets]
    
    for i in range(ncurv // 5):
        tempresults = results[20*i:]
        fig, ax = plt.subplots(5, 4, figsize=(14, 10))
    
        for j in range(20):
            outs = tempresults[j]
            ax[j // 4, j % 4].plot(outs.x, outs.y, 'bo')
            if outs.fit_good:
                ax[j // 4, j % 4].plot(outs.x_fine, outs.fitline_fine, 'r-')
                ax[j//4, j % 4].fill_between(outs.x_fine, outs.yupper_fine,
                                                 outs.ylower_fine,
                                                 facecolor='green', alpha=0.8)
                hi = np.max(outs.y)
                lo = np.min(outs.y)
                ax[j // 4, j % 4].set_ylim = ([lo - (hi - lo)/8,
                                               hi + (hi - lo)/8])
                ax[j // 4, j % 4].locator_params(axis='x', nbins=4)
                ticks = ax[j // 4, j % 4].get_xticks().tolist()
                ax[j // 4, j % 4].set_xticklabels(['{:3g}'.format(tick) for
                                                   tick in ticks])
    
        cols = ['Auto fit', 'Manual guess', 'Hold',
                'Man bounds']
        rows = [str(5*i+j) + '\n' + fi.__name__ + ' Fit \n' + di + ' Data \n' + str(ki)
                for j, (fi, di, ki) in enumerate(zip(funcs[5*i:], datanames[5*i:], kws[5*i:]))]
    
        pad = 5  # in points
    
        for axi, col in zip(ax[0, :], cols):
            axi.annotate(col, xy=(0.5, 1), xytext=(0, pad),
                         xycoords='axes fraction', textcoords='offset points',
                         size='large', ha='center', va='baseline')
    
        for axi, row in zip(ax[:, 0], rows):
            axi.annotate(row, xy=(0, 0.5), xytext=(-axi.yaxis.labelpad-pad, 0),
                         xycoords=axi.yaxis.label, textcoords='offset points',
                         size='large', ha='right', va='center')
    
        fig.tight_layout()
        fig.subplots_adjust(left=0.15, top=0.95)
        plt.draw()
    
    plt.show()
    return results, fitsets

if __name__ == "__main__":
    main()
