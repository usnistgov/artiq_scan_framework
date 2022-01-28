#  Example 9: after_measure() callback example
#
#    1. `after_measure()` is called after the measure method is called
#    2. When `after_measure()` is called self._data has been updated
from artiq.experiment import *
from scan_framework.scans import *


class Example9Scan(Scan1D, EnvExperiment):

    def build(self):
        super().build()
        # force nrepeats to 1
        self.nrepeats = 1

        # nrepeats will not be presented as a GUI argument since it has already been set.
        self.scan_arguments()

        self.measurements = ['m1', 'm2']

    def get_scan_points(self):
        return [1.0, 2.0, 3.0]

    @kernel
    def measure(self, point):
        print('-- measure --')
        print(self.measurement)
        print(point)
        return 0

    # 1. Define the `after_measure()` method
    @kernel
    def after_measure(self, point, measurement):
        print("-- after_measure --")
        # NOTE: The name of the current measurement is passed in
        print(self.measurement)
        # NOTE: along with the current scan point
        print(point)
