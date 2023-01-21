import artiq_scan_framework.beta.scan as beta_scan
from artiq_scan_framework.beta.loops.loop_1d import *
from artiq_scan_framework.lib.loading_interface import *
from artiq_scan_framework.lib.ion_checker import *
from artiq_scan_framework.analysis.fit_functions import Line
from artiq_scan_framework.beta.models import *
import numpy as np
import pprint
pp = pprint.PrettyPrinter(indent=4)


class Test1DScan(beta_scan.BetaScan, EnvExperiment):

    def build(self):
        super().build()
        self.debug = True
        self.scan_arguments(Loop1D, init_only=True)
        self.setattr_argument('run_on_core', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_mutate', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_pausing', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_count_monitor', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_reporting', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_fitting', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_timing', BooleanValue(default=True), show=True)
        print('***************')
        self.scan_arguments(npasses={'default': 22})
        self.looper = Loop1D(self, scan=self)

    def prepare(self):
        self.model = BetaScanModel(self, namespace='beta', fit_function=Line)
        self.register_model(self.model, measurement=True, fit=True, bind=True)

    def get_scan_points(self):
        return [i for i in range(10)]

    @kernel
    def initialize_devices(self):
        self.core.reset()

    def measure(self, point) -> TInt32:
        lam = point + 0.2
        return int(np.random.poisson(lam, 1)[0])
