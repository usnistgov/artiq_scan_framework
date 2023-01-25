from artiq_scan_framework import *
import numpy as np

class Test2DScan(Scan, EnvExperiment):

    def build(self):
        super().build()
        self.nwarmup_points = 10
        self.scan_arguments(Loop2D)
        self.setattr_argument('run_on_core', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_mutate', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_pausing', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_count_monitor', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_reporting', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_fitting', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_timing', BooleanValue(default=True), show=True)
        self.setattr_argument('points0', Scannable(
            default=RangeScan(
                start=0,
                stop=7,
                npoints=8
            ),
            unit='Hz',
            scale=1
        ), scan_points=0)
        self.setattr_argument('points1', Scannable(
            default=RangeScan(
                start=0,
                stop=7,
                npoints=8
            ),
            unit='Hz',
            scale=1
        ), scan_points=1)
        self.looper = Loop2D(self, scan=self)

    def prepare(self):
        self.model = ScanModel(self, namespace='test', fit_function=Line)
        self.register_model(self.model, measurement=True, fit=True, bind=True, dimension=1)
        self.register_model(self.model, fit=True, bind=True, dimension=0)

    @kernel
    def initialize_devices(self):
        self.core.reset()

    def simulate(self, point) -> TInt32:
        lam = point[0] * point[1] + 0.2
        return int(np.random.poisson(lam, 1)[0])

    @portable
    def measure(self, point):
        if self.warming_up:
            print('warmup')
            print(point)
            return 0
        else:
            return self.simulate(point)

    def calculate_dim0(self, dim1_model):
        param = dim1_model.fit.params.slope
        error = dim1_model.fit.errs.slope_err
        return param, error

