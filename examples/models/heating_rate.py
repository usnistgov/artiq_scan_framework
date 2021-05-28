from scan_framework import *


class RsbModel(TimeModel):
    """ Heating Rate RSB Data Model"""

    # datasets
    namespace = 'heating_rate.rsb.%type'  #: Dataset namespace
    mirror = False

    persist = True
    broadcast = True
    # stats
    enable_histograms = True
    to_scan = 'wait_time'

    # fits
    main_fit = None
    fit_function = fit_functions.Exp

    @property
    def simulation_args(self):
        if self.to_scan == 'wait_time':
            return {
                'A': -5,
                'b': -1/(200*us),
                'y0': 7,
            }
        if self.to_scan == 'rf_amplitude':
            return {
                'A': -5,
                'b': -1,
                'y0': 7,
            }

    # plots
    @property
    def x_label(self):
        if self.to_scan == 'wait_time':
            return 'wait time'
        if self.to_scan == 'rf_amplitude':
            return 'rf amplitude'
    @property
    def x_units(self):
        if self.to_scan == 'wait_time':
            return 's'
        if self.to_scan == 'rf_amplitude':
            return ''

    @property
    def plot_title(self):
        if self.to_scan == 'wait_time':
            return 'rsb vs wait time'
        if self.to_scan == 'rf_amplitude':
            return 'rsb vs rf amplitude'


class BsbModel(TimeModel):
    """ Heating Rate BSB Data Model """

    # datasets
    namespace = 'heating_rate.bsb.%type'  #: Dataset namespace
    persist = True
    broadcast = True
    mirror = False
    to_scan = 'wait_time'

    # stats
    enable_histograms = True

    # fits
    fit_function = fit_functions.Exp
    main_fit = None
    scan = 'wait_time'

    @property
    def simulation_args(self):
        if self.to_scan == 'wait_time':
            return {
                'A': 1,
                'b': -1 / (200 * us),
                'y0': 7,
            }
        if self.to_scan == 'rf_amplitude':
            return {
                'A': 1,
                'b': -1,
                'y0': 7,
            }

    @property
    def x_label(self):
        if self.to_scan == 'wait_time':
            return 'wait time'
        if self.to_scan == 'rf_amplitude':
            return 'rf amplitude'

    @property
    def x_units(self):
        if self.to_scan == 'wait_time':
            return 's'
        if self.to_scan == 'rf_amplitude':
            return ''

    @property
    def plot_title(self):
        if self.to_scan == 'wait_time':
            return 'bsb'
        if self.to_scan == 'rf_amplitude':
            return 'bsb vs rf amplitude'


class BkgdModel(TimeModel):
    """ Heating Rate BSB Data Model """

    # datasets
    namespace = 'heating_rate.bkgd'  #: Dataset namespace
    persist = True
    broadcast = True
    mirror = False

    # stats
    enable_histograms = True

    # fits

    fit_function = fit_functions.Line
    main_fit = None
    simulation_args = {
        'slope': 0,
        'y_intercept': 0
    }

    # plots
    x_units = 's'
    plot_title = 'bkgd'

class NbarModel(TimeModel):
    """Heating Rate Temp Model"""

    # datasets
    namespace = 'heating_rate.nbar.%type'  #: Dataset namespace
    mirror = True
    persist = True
    broadcast = True
    to_scan = 'wait_time'

    # stats
    enable_histograms = False

    # fits
    fit_function = fit_functions.Line
    fit_use_yerr = True
    main_fit = 'heating_rate'
    fit_map = {
        'slope': 'heating_rate'
    }

    # plots
    y_label = 'n bar'
    scan = 'wait_time'

    @property
    def x_label(self):
        if self.to_scan == 'wait_time':
            return 'wait time'
        if self.to_scan == 'rf_amplitude':
            return 'rf amplitude'
        if self.to_scan == 'frequency':
            return 'rf frequency'

    @property
    def x_units(self):
        if self.to_scan == 'wait_time':
            return 's'
        if self.to_scan == 'rf_amplitude':
            return ''
        if self.to_scan == 'frequency':
            return 'Hz'

    @property
    def plot_title(self):
        if self.to_scan == 'wait_time':
            return 'nbar vs wait time'
        if self.to_scan == 'rf_amplitude':
            return 'nbar vs rf amplitude'
        if self.to_scan == 'frequency':
            return 'nbar vs rf frequency'

    def build(self, rsb_model, bsb_model, bkgd_model, **kwargs):
        self.rsb_model = rsb_model
        self.bsb_model = bsb_model
        self.bkgd_model = bkgd_model
        super().build(**kwargs)

    def load(self):
        """Load previously collected data into local storage within each model"""
        super().load()
        self.bsb_model.load()
        self.rsb_model.load()
        self.bkgd_model.load()

    def calculate(self, i_point):
        """Calculate nbar and the error in nbar at the given scan point index 'i'"""
        bsb = self.bsb_model.means[i_point]
        bsb_error = self.bsb_model.errors[i_point]
        rsb = self.rsb_model.means[i_point]
        rsb_error = self.rsb_model.errors[i_point]
        avgBkgd = np.nanmean(self.bkgd_model.means)

        # old calculation
        #ratio = (rsb - avgBkgd) / (bsb - avgBkgd)
        #nbar = ratio / (1 - ratio)

        # new calculation (uses an inverted ratio)
        ratio = (bsb - avgBkgd) / (rsb - avgBkgd)
        nbar = 1 / (ratio - 1)
        error = (ratio / (ratio - 1)**2) * ((rsb_error / rsb)**2 + (bsb_error / bsb)**2)**.5
        return nbar, error
