import artiq_scan_framework.beta.scan as beta_scan
from artiq_scan_framework.models import *
from artiq_scan_framework.beta.loops.loop_2d import *
from artiq_scan_framework.analysis.fit_functions import Line
import numpy as np

class Test2DScan(beta_scan.BetaScan, EnvExperiment):

    def build(self):
        super().build()
        self.run_on_core = False
        self.scan_arguments()
        self.looper = Loop2D(self, scan=self, npasses=self.npasses, nrepeats=self.nrepeats)

    def prepare(self):
        self.model = ScanModel(self, namespace='beta', fit_function=Line)
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

    @portable
    def measure(self, point):
        lam = point[0]*point[1] + 0.2
        return np.random.poisson(lam, 1)[0]

    def calculate_dim0(self, dim1_model):
        param = dim1_model.fit.params.slope
        error = dim1_model.fit.errs.slope_err
        return param, error
