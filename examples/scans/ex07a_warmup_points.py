# Example 7a: Warmup Points
#
# Basic example of warmup points
#   1. The number of warmup points is set by nwarmup_points
#   2. The value of each warmup point is set 0.0
#   3. The measure method is called once at each warmup point
#   4. self.warming_up is set to true during warmup

from artiq.experiment import *
from scan_framework.scans import *


class WarmupPointsBasicExample(Scan1D, EnvExperiment):
    """ WarmupPointsBasicExample

    """

    # auto create 2 warmup points set to 0.0
    nwarmup_points = 2

    def build(self):
        self.scan_arguments()
        self.setattr_device('core')
        self.setattr_device('scheduler')

    def get_scan_points(self):
        return [1.0, 2.0, 3.0]

    # measure method is called at each warmup point
    @kernel
    def measure(self, point):
        # check if warming up...
        if self.warming_up:
            print('warmup')
        else:
            print('measure')
        print(point)
        return 0


