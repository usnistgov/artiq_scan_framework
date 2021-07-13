# Example 2: Calculating and plotting mean values
#
# How to register a scan model to calculate and plot mean values and standard errors.

from artiq.experiment import *
from scan_framework import *


# 1. Create a scan model.
#    This is a class that inherits from ScanModel and handles all data processing and storage.
class Example2Model(ScanModel):
    # 2. Define a namespace.
    #    Data will be saved under this top level key in the datasets.
    namespace = "example_2"
    plot_title = 'Example 2'


class Example2Scan(Scan1D, EnvExperiment):

    def build(self):
        super().build()  # create the `core` and `scheduler` devices
        self.scan_arguments()

        # User input to define the scan points
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
        # 3. Create an instance of the scan model.
        self.model = Example2Model(self)

        # 4. Register the model with `measurement=True`.
        #    This instructs the framework to, at the end of each scan point,
        #    calculate and plot both the the mean and standard error of the
        #    values returned by `measure()`
        self.register_model(self.model, measurement=True)

    # NOTE: No run method is defined.  Typically, a run method is not necessary.
    #       In this case, the default run method in scan_framework/scans/scan.py is used which handles
    #       initializing, running the scan, yielding/terminating, and performing fits automatically.

    def get_scan_points(self):
        return self.frequencies

    @kernel
    def measure(self, frequency):
        # Return some dummy data to be plotted.
        return int(frequency**2)



