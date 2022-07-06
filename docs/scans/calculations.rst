Performing calculations
---------------------------------------------
Calculations can be performed and written to datasets after each scan point.  To use calculations, create a model
for the calculation and register it with the scan with the name :code:`calc_model` (or simple assign :code:`self.calc_model`
to the model instance in your scan).  After each scan point, a method named :code:`calculate()` which you define in the
model will be called and passed the index of the current scan point.  The :code:`calculate()` method must then return a
tuple of (value, error) which is the calculated value and it's error.  Datasets under the calc model's namespace and
the mirror namespace will be mutated with these calculated values after each scan point.  See
:code:`scans/heating_rate_scan.py` and :code:`lib/models/heating_rate.py` for examples.


.. code-block:: python

    from artiq_scan_framework.scans import *
    from artiq_scan_framework.models import *

    class CalculationScan(Scan1D, EnvExperiment):

        def build(self):
            super().build()

        def prepare(self):
            self.register_model(RsbScanModel(), measurement='bsb')
            self.register_model(BsbScanModel(), measurement='rsb')
            self.register_model(BkgdScanModel(), measurement='bkgd')
            self.register_model(NbarScanModel(), calculation='nbar', fit='nbar', mutate_plot=True)


    class RsbScanModel(TimeModel):
        """ Heating Rate RSB Model"""

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
                return 'us'
            if self.to_scan == 'rf_amplitude':
                return ''

        @property
        def x_scale(self):
            if self.to_scan == 'wait_time':
                return 1*us
            if self.to_scan == 'rf_amplitude':
                return 1

        @property
        def plot_title(self):
            if self.to_scan == 'wait_time':
                return 'rsb vs wait time'
            if self.to_scan == 'rf_amplitude':
                return 'rsb vs rf amplitude'


    class BsbScanModel(TimeModel):
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
                return 'us'
            if self.to_scan == 'rf_amplitude':
                return ''

        @property
        def x_scale(self):
            if self.to_scan == 'wait_time':
                return 1 * us
            if self.to_scan == 'rf_amplitude':
                return 1

        @property
        def plot_title(self):
            if self.to_scan == 'wait_time':
                return 'bsb'
            if self.to_scan == 'rf_amplitude':
                return 'bsb vs rf amplitude'


    class BkgdScanModel(TimeModel):
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
        x_units = 'us'
        x_scale = 1*us
        plot_title = 'bkgd'


    class NbarScanModel(TimeModel):
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
                return 'us'
            if self.to_scan == 'rf_amplitude':
                return ''
            if self.to_scan == 'frequency':
                return 'MHz'

        @property
        def x_scale(self):
            if self.to_scan == 'wait_time':
                return 1 * us
            if self.to_scan == 'rf_amplitude':
                return 1
            if self.to_scan == 'frequency':
                return 1 * MHz

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

        def load_datasets(self):
            """Load previously collected data into local storage within each model"""
            super().load_datasets()
            self.bsb_model.load_datasets()
            self.rsb_model.load_datasets()
            self.bkgd_model.load_datasets()

        def calculate(self, i_point):
            """Calculate nbar and the error in nbar at the given scan point index 'i'"""
            bsb = self.bsb_model.stat_model.means[i_point]
            bsb_error = self.bsb_model.stat_model.errors[i_point]
            rsb = self.rsb_model.stat_model.means[i_point]
            rsb_error = self.rsb_model.stat_model.errors[i_point]
            avgBkgd = np.nanmean(self.bkgd_model.stat_model.means)

            # old calculation
            #ratio = (rsb - avgBkgd) / (bsb - avgBkgd)
            #nbar = ratio / (1 - ratio)

            # new calculation (uses an inverted ratio)
            ratio = (bsb - avgBkgd) / (rsb - avgBkgd)
            if isnan(ratio):
                nbar = 0
                error = 0
            else:
                nbar = 1 / (ratio - 1)
                error = (ratio / (ratio - 1)**2) * ((rsb_error / rsb)**2 + (bsb_error / bsb)**2)**.5
            return nbar, error