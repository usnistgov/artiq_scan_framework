# Example 10: Fitting guess arguments
#
# How to specify fit guesses using GUI arguments in the dashboard
from artiq.experiment import *
from scan_framework import *


class Example10Scan(Scan1D, EnvExperiment):

    def build(self):
        super().build()
        self.scan_arguments()
        self.setattr_argument('frequencies', Scannable(
            default=RangeScan(
                start=0,
                stop=7,
                npoints=8
            ),
            unit='Hz',
            scale=1
        ))

        # 1. Create fit guess arguments using the FitGuess class
        #    FitGuess has the same arguments as ARTIQ NumberValue arguments
        self.setattr_argument('guess_alpha', FitGuess(
            fit_param='alpha',
            default=2.0,
            scale=1.0,
            unit='',
            # setting
            #   use='ask': Adds a checkbox to select if the guess should be used for fitting or not.
            #   use=True: Entered guess will be used for fitting.
            #   use=False: Entered guess will not be used for fitting.
            use='ask',
            step=0.1
        ))

        # This fit guess is not used, even though there is a gui argument for it
        self.setattr_argument('guess_A', FitGuess(
            fit_param='A',
            default=-1000,
            scale=1.0,
            unit='',
            # setting
            #   use='ask': Adds a checkbox to select if the guess should be used for fitting or not.
            #   use=True: Entered guess will be used for fitting.
            #   use=False: Entered guess will not be used for fitting.
            use=False,
            step=0.1
        ))
        # This fit guess is always used, regardless of what is defined in the model for the guess attribute
        self.setattr_argument('guess_y0', FitGuess(
            fit_param='y0',
            default=0,
            scale=1.0,
            unit='',
            # setting
            #   use='ask': Adds a checkbox to select if the guess should be used for fitting or not.
            #   use=True: Entered guess will be used for fitting.
            #   use=False: Entered guess will not be used for fitting.
            use=True,
            step=1
        ))

    def prepare(self):
        self.model = Example10Model(self)
        self.register_model(self.model, measurement=True, fit=True)

    def get_scan_points(self):
        return self.frequencies

    @kernel
    def measure(self, frequency):
        return int(frequency**2.0)

    def after_fit(self, fit_name, valid, saved, model):
        # 2. Guesses used are always available in the current_scan.fits.guesses dataset
        self.logger.warning('Guesses used:')
        self.logger.warning('alpha: {}'.format(self.get_dataset('current_scan.fits.guesses.alpha')))
        self.logger.warning('A: {}'.format(self.get_dataset('current_scan.fits.guesses.A')))
        self.logger.warning('y0: {}'.format(self.get_dataset('current_scan.fits.guesses.y0')))

        self.logger.warning('Fitted parameters:')
        self.logger.warning('alpha: {}'.format(self.get_dataset('current_scan.fits.params.alpha')))
        self.logger.warning('A: {}'.format(self.get_dataset('current_scan.fits.params.A')))
        self.logger.warning('y0: {}'.format(self.get_dataset('current_scan.fits.params.y0')))


class Example10Model(ScanModel):
    namespace = "example_10"
    fit_function = curvefits.Power

    man_scale = {
        'A': 1,
        'alpha': 1,
        'y0': 1
    }
    man_bounds = {
        'A': [.9, 1.1],
        'alpha': [1.5, 2.5]
    }

    # 3. Specify the fit param to save
    main_fit = ''