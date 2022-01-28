# Example 3: Fitting data
#
# How to instruct the scan framework to perform a fit to the calculated mean values and save a fitted parameter
# to the datasets.
from artiq.experiment import *
from scan_framework import *


class Example3Scan(Scan1D, EnvExperiment):

    def build(self):
        super().build()

        # Meaning of the possible fit_options selections are:
        #   No Fits:            Do not perform fits
        #   Fit:                Perform a fit after scan completes
        #   Fit and Save:       Same as 'Fit' but the 'main_fit' parameter (see below) is broadcast and persisted.
        #   Fit Only:           Perform a fit on the data from the last scan that was run.  The scan loop is not executed.
        #   Fit Only and save:  Same as 'Fit Only' but the 'main_fit' parameter (see below) is broadcast and persisted.
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

    def prepare(self):
        self.model = Example3Model(self)

        # 1. Register the model with fit=True.
        #    This instructs the framework to fit a function to the saved mean values
        #    after the scan completes.
        self.register_model(self.model, measurement=True, fit=True)

    def get_scan_points(self):
        return self.frequencies

    @kernel
    def measure(self, frequency):
        return int(frequency**2.0)


class Example3Model(ScanModel):
    namespace = "example_3"

    # 2. Define the function.
    #    The framework will fit the calculated means to this function.
    fit_function = curvefits.Power

    # 3. Optionally specify guesses, scales, and bound for the fit param.
    guess = {
        'A': 1,
        'alpha': 2
    }
    man_scale = {
        'A': 1,
        'alpha': 1,
        'y0': 1
    }
    man_bounds = {
        'A': [.9, 1.1],
        'alpha': [1.5, 2.5]
    }
    # 4. Fit params can also optionally be fixed to a given value if the fit param value is already known.
    hold = {
        'y0': 0.0
    }

    # 6. Specify the fit param to save
    #    This will broadcast and persist the fitted param to the global dataset store if 'Fit and Save' or
    #    'Fit Only and Save' are selected in the dashboard.
    #     In this example alpha will be saved to 'example_3.alpha'
    main_fit = 'alpha'