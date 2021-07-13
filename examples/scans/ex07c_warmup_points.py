# Example 7c: Warmup Points
#
# Multiple measurements example
#   1. Each warmup point is repeated once for each measurement.

from artiq.experiment import *
from scan_framework.scans import *


class WarmupPointsMeasurementsExample(Scan1D, EnvExperiment):
    def build(self):
        self.scan_arguments()
        self.setattr_device('core')
        self.setattr_device('scheduler')

        # specify two measurements
        self.measurements = ['measurement_1', 'measurement_2']

    def get_scan_points(self):
        return [1.0, 2.0, 3.0]

    def get_warmup_points(self):
        return [1.0, 2.0]

    @kernel
    def warmup(self, point):
        # warmup is called twice at each warmup point (once for each measurement)
        print('warmup')
        print(self.measurement)
        print(point)

    @kernel
    def measure(self, point):
        print('measure')
        print(self.measurement)
        print(point)
        return 0

