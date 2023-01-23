"""
Microwave Scan Class
Scans frequencies and pulse times of microwave transitions after
ion has been cooled by doppler cooling
"""

# artiq_scan_framework modules

from artiq_scan_framework.beta.extensions import *
from artiq_scan_framework.beta.models import *
from artiq_scan_framework.analysis.fit_functions import InvCos
from artiq_scan_framework.beta.scan_1d import *
import numpy as np

class TestTimeFreqScan(Scan1D, TimeScan, EnvExperiment):


    def build(self, **kwargs):
        self.print('TestTimeScan::build()', 2)
        super().build(**kwargs)

        self.print('creating scan arguments')
        self.scan_arguments(
            times={'start': 0*us, 'stop': 40*us, 'npoints': 50, 'ndecimals': 0, 'global_step': 1*us},
            nrepeats={'default': 100}
        )
        self.setattr_argument('run_on_core', BooleanValue(default=False), show=True)
        self.setattr_argument('enable_mutate', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_pausing', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_count_monitor', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_reporting', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_fitting', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_timing', BooleanValue(default=True), show=True)
        self.print('TestTimeScan::build()', -2)
        self.last_i = -1

    def prepare(self):
        self.model = BetaTimeModel(self, namespace='beta', fit_function=InvCos, plot_title='Time scan test')
        self.register_model(self.model, measurement=True, fit=True, bind=True)

    def simulate(self, time, i) -> TInt32:
        if i != self.last_i:
            self.print('measure(time={:0.1f} us)'.format(time/us))
            self.last_i = i
        lam = 20*np.sin(np.pi*time/(20*us))**2
        return int(np.random.poisson(lam, 1)[0])

    @portable
    def measure(self, time):
        return self.simulate(time, self.looper.itr.i)
