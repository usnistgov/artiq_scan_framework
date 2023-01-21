"""
Microwave Scan Class
Scans frequencies and pulse times of microwave transitions after
ion has been cooled by doppler cooling
"""

# artiq_scan_framework modules

from artiq_scan_framework.beta.extensions import *
from artiq_scan_framework.beta.models import *
from artiq_scan_framework.analysis.fit_functions import Line
from artiq_scan_framework.beta.scan_1d import *

class TestTimeFreqScan(Scan1D, TimeFreqScan, EnvExperiment):


    def build(self, **kwargs):
        self.print('TestTimeFreqScan::build()', 2)
        super().build(**kwargs)

        self.enable_auto_tracking = False
        self.frequency_center = 0
        self.pulse_time = 0

        self.print('creating scan arguments')
        self.scan_arguments()
        self.setattr_argument('run_on_core', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_mutate', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_pausing', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_count_monitor', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_reporting', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_fitting', BooleanValue(default=True), show=True)
        self.setattr_argument('enable_timing', BooleanValue(default=True), show=True)
        # self.scan_arguments(
        #     nrepeats={'default': 50},
        #     frequencies={'start': -0.1 * MHz, 'stop': 0.1 * MHz, 'npoints': 50},
        #     times={'start': 0, 'stop': 40 * us, 'npoints': 50},
        #     fit_options={'default': 'Fit and Save'},
        #     scan=False,
        # )
        self.print('TestTimeFreqScan::build()', -2)

    def prepare(self):
        self.model = BetaScanModel(self, namespace='beta', fit_function=Line)
        self.register_model(self.model, measurement=True, fit=True, bind=True)

    def print_measure(self, time, freq):
        self.print('measure(time={}, freq={}'.format(time, freq))
    @kernel
    def measure(self, time, freq):
        self.print_measure(time, freq)
        return 0
