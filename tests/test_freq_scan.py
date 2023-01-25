"""
Microwave Scan Class
Scans frequencies and pulse times of microwave transitions after
ion has been cooled by doppler cooling
"""

# artiq_scan_framework modules
from artiq.experiment import *
from artiq_scan_framework import *
from artiq_scan_framework.analysis.fit_functions import Sinc


class TestFreqScan(Scan1D, FreqScan, EnvExperiment):


    def build(self, **kwargs):
        self.print('TestFreqScan::build()', 2)
        super().build(**kwargs)

        self.print('creating scan arguments')
        self.scan_arguments(
            frequencies={'start': 1.7999*GHz, 'stop': 1.8001*GHz, 'npoints': 25, 'ndecimals': 5, 'global_step': 100*kHz, 'scale': GHz, 'unit': 'GHz'},
            nrepeats={'default': 50}
        )
        self.setattr_argument('run_on_core', BooleanValue(default=False), show=True)
        self.setattr_argument('enable_mutate', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_pausing', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_count_monitor', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_reporting', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_fitting', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_timing', BooleanValue(default=True), show=True)
        self.print('TestFreqScan::build()', -2)
        self.last_i = -1

    def prepare(self):
        self.model = FreqModel(self, namespace='test', fit_function=Sinc, main_fit='frequency')
        self.register_model(self.model, measurement=True, fit=True, bind=True)

    def simulate(self, freq, i) -> TInt32:
        if i != self.last_i:
            self.print('measure(freq={:0.5f} GHz)'.format(freq/(1*GHz)))
            self.last_i = i
        lam = Sinc.value(freq, 0.1, 20, 10*us, 1.8*GHz)
        return int(np.random.poisson(lam, 1)[0])

    @portable
    def measure(self, freq):
        return self.simulate(freq, self.looper.itr.i)
