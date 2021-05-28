# Example 0: A minimal Scan
#
# A bare-bones scan running on the core device.  No data is processed, plotted, or saved.
# Only a list of scan points is iterated over.

from artiq.experiment import *

# 1. Import all classes needed the scan framework.
from scan_framework import *


# 2. Create a scan experiment.
#    This is a class that inherits from Scan1D and performs the experimental measurements.
class Example0Scan(Scan1D, EnvExperiment):

    def build(self):
        # NOTE: The next two lines can be replaced by super().build()
        #       Typically a scan will only call super().build() since the 'core' and 'scheduler' devices
        #       are almost always needed.

        # 3. Create a core device and scheduler device.
        # The core device is needed since our measure method runs on the core device.
        self.setattr_device("core")

        # The scheduler device is needed for pausing and cancelling scans
        self.setattr_device('scheduler')

        # 4a. Create GUI arguments for setting the scan parameters (uses scan_framework defaults)
        # self.scan_arguments()

        # 4b. GUI arguments can be created with different defaults via arguments with the same name as the GUI label.
        self.scan_arguments(
            # Turn off fit_options GUI argument
            fit_options=False,
            # Set default values for remaining GUI arguments
            npasses={'default': 2},
            nrepeats={'default': 50, 'step': 2},
            # Each dictionary can contain any argument passed to the corresponding ARTIQ processor (e.g. NumberValue)
            nbins={'default': 100, 'ndecimals': 0, 'step': 1}
        )

    # 5. Define a run method (Optional)
    # NOTE: Typically a run method is not needed (see ex1_models.py)
    #       If a run method is define the `after_scan()` and `lab_after_scan()` callbacks are not executed.
    def run(self, resume=False):
        # 6. Initialize the scan
        self._initialize(resume)

        # run the scan
        if not self.fit_only:
            # 7. Run the scan on the core device
            self._run_scan_core(resume)

            # 8. Yield to other experiments or terminate
            if self._paused:
                self._yield()
                return

        # 9. Perform fits
        self._analyze()

    # 10. Tell the scan class what points to scan over
    def get_scan_points(self):
        return [i for i in range(10)]

    # 11. Define a measurement method that will be repeated self.nrepeats times at each
    #    scan point
    @kernel
    def measure(self, point):
        # The first point is value of the current scan point
        print(point)

        # measure() must return an integer
        return 0