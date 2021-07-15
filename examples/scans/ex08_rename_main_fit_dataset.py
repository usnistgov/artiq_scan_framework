# Example 8: Rename the main fit dataset
#
# How to rename the main fit dataset containing the main fit of the scan

from artiq.experiment import *
from scan_framework import *


class Example7Model(ScanModel):
    namespace = 'example_8'
    fit_function = curvefits.Power

    # 1. Define main_fit as a list to rename the fit param
    #   The first entry is the name of the fit parameter and the second is the name of the dataset
    main_fit = ["A", "slope"]  # save the 'A' fit parameter to a dataset named 'slope'

    # force a fit to a linear function
    hold = {
        "alpha": 1
    }


class Example7Scan(Scan1D, EnvExperiment):

    def build(self):
        super().build()
        self.scan_arguments()
        self.model1 = Example7Model(self)
        self.register_model(self.model1, measurement=True, fit=True)

    def get_scan_points(self):
        return [i for i in range(10)]

    @kernel
    def measure(self, point):
        return int(3*point)