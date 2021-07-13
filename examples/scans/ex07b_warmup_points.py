# Example 7b: Warmup Points
#
# Point values and warmup method example
#   1. The value of each warmup point is set by get_warmup_points()
#   2. During warmup, the warmup method is called once for each warmup point.
#   3. self.warming_up is still set to true during warmup

from artiq.experiment import *
from scan_framework.scans import *


class WarmupPointsWarmupMethodExample(Scan1D, EnvExperiment):

    def build(self):
        self.scan_arguments()
        self.setattr_device('core')
        self.setattr_device('scheduler')

    def get_scan_points(self):
        return [1.0, 2.0, 3.0]

    # specify warmup point values
    def get_warmup_points(self):
        return [1.0, 2.0]

    # custom warmup method
    @kernel
    def warmup(self, point):
        print('warmup')
        print(point)

    # measure is not called during warmup
    @kernel
    def measure(self, point):
        print('measure')
        print(point)
        return 0

