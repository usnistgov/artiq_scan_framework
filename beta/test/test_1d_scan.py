import artiq_scan_framework.beta.scan as beta_scan
from artiq_scan_framework.models import *
from artiq_scan_framework.beta.loops.loop_1d import *
from artiq_scan_framework.lib.loading_interface import *
from artiq_scan_framework.lib.ion_checker import *
from artiq_scan_framework.analysis.fit_functions import Line
import numpy as np


class Test1DScan(beta_scan.BetaScan, EnvExperiment):

    def build(self):
        super().build()
        self.run_on_core = False
        self.debug = True
        self.scan_arguments()
        self.looper = Loop1D(self, scan=self, npasses=self.npasses, nrepeats=self.nrepeats)
        self.load_component('ion_load',
                            ion_checker=IonChecker(self,
                                                   logger=self.logger,
                                                   loading=LoadingInterface(self)
                                                   )
                            )

    def prepare(self):
        self.model = ScanModel(self, namespace='beta', fit_function=Line)
        self.register_model(self.model, measurement=True, fit=True, bind=True)

    def get_scan_points(self):
        return [i for i in range(10)]

    @kernel
    def initialize_devices(self):
        self.core.reset()

    @portable
    def measure(self, point):
        lam = point + 0.2
        return np.random.poisson(lam, 1)[0]
