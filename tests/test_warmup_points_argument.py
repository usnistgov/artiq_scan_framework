from artiq.experiment import *
from artiq_scan_framework import *
import numpy as np


class Test1DScan(Scan1D, EnvExperiment):

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
        self.setattr_argument('manually_offset_x', BooleanValue(default=False), show=True)
        self.setattr_argument('scan_points', Scannable(
            default=RangeScan(
                start=0,
                stop=7,
                npoints=8
            ),
            unit='Hz',
            scale=1
        ), scan_points=True)
        self.setattr_argument('warmup_points', Scannable(
            default=RangeScan(
                start=0,
                stop=7,
                npoints=8
            ),
            unit='Hz',
            scale=1
        ), warmup_points=True)
        self.scan_arguments(npasses={'default': 2})

    def prepare(self):
        self.model = ScanModel(self, namespace='test', fit_function=Line)
        self.register_model(self.model, measurement=True, fit=True, bind=True)
        if self.manually_offset_x:
             self._x_offset = 10

    @kernel
    def initialize_devices(self):
        self.core.reset()

    def simulate(self, point) -> TInt32:
        lam = point + 0.2
        return int(np.random.poisson(lam, 1)[0])

    @portable
    def measure(self, point):
        if self.warming_up:
            print('warmup point')
            print(point)
        return self.simulate(point)
