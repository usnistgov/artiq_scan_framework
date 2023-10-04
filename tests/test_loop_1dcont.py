from artiq_scan_framework import *


class Test1DContScan(Scan, EnvExperiment):

    def build(self):
        super().build()

        # must be called before creating looper
        self.scan_arguments(Loop1DCont, continuous_measure_point={'unit': 'us', 'scale': us})
        self.setattr_argument('run_on_core', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_mutate', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_pausing', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_count_monitor', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_reporting', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_fitting', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_timing', BooleanValue(default=True), show=True)

        # must be called after calling self.scan_arguments()
        self.looper = Loop1DCont.looper(self)

    def prepare(self):
        self.model = ScanModel(self, namespace='test', fit_function=Line)
        self.register_model(self.model, measurement=True, fit=True, bind=True)

    def get_scan_points(self):
        return range(200)

    @kernel
    def initialize_devices(self):
        self.core.reset()

    @portable
    def measure(self, point):
        if int(self.looper.itr.i / 22) % 8 == 7:
            return 22**2
        elif int(self.looper.itr.i / 22) % 2 == 0:
            return (self.looper.itr.i % 22)**2
        else:
            return 22**2 - (self.looper.itr.i % 22)**2
        return 0