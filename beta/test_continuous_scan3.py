from artiq_stylus.lib.stylus_scan import *
from artiq_stylus.lib.libs import *
from artiq_stylus.lib.models.ramsey import *


class TestContinuousScan2(Scan1D, EnvExperiment):


    def build(self):
        self.setattr_device("core")
        self.setattr_device('scheduler')
        self.scan_arguments()

    def get_scan_points(self):
        return [i for i in range(10)]

    @kernel
    def measure(self, point):
        return 0

