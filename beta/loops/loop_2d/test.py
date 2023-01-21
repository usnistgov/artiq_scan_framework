import artiq_scan_framework.beta.scan as beta_scan
from artiq_scan_framework.beta.loops.loop_2d import *
from artiq_scan_framework.analysis.fit_functions import Line
from artiq_scan_framework.beta.models import *
import numpy as np

class Test2DScan(beta_scan.BetaScan, EnvExperiment):

    def build(self):
        super().build()
        self.scan_arguments(Loop2D)
        self.setattr_argument('run_on_core', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_mutate', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_pausing', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_count_monitor', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_reporting', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_fitting', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_timing', BooleanValue(default=True), show=True)
        self.looper = Loop2D(self, scan=self)

    def prepare(self):
        self.model = BetaScanModel(self, namespace='beta', fit_function=Line)
        self.register_model(self.model, measurement=True, fit=True, bind=True, dimension=1)
        self.register_model(self.model, fit=True, bind=True, dimension=0)

    def get_scan_points(self):
        return [
            [i+1 for i in range(2)],
            [i for i in range(3)]
        ]

    @kernel
    def initialize_devices(self):
        self.core.reset()

    def measure(self, point) -> TInt32:
        lam = point[0]*point[1] + 0.2
        return int(np.random.poisson(lam, 1)[0])

    def calculate_dim0(self, dim1_model):
        param = dim1_model.fit.params.slope
        error = dim1_model.fit.errs.slope_err
        return param, error
