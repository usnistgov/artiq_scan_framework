"""
Microwave Scan Class
Scans frequencies and pulse times of microwave transitions after
ion has been cooled by doppler cooling
"""

# artiq_scan_framework modules

from artiq_scan_framework.beta.extensions import *
from artiq_scan_framework.beta.models import *
from artiq_scan_framework.analysis.fit_functions import Sinc, InvCos
from artiq_scan_framework.beta.scan_1d import *

class TestTimeFreqScan(Scan1D, TimeFreqScan, EnvExperiment):


    def build(self, **kwargs):
        self.print('TestTimeFreqScan::build()', 2)
        super().build(**kwargs)
        #
        # self.enable_auto_tracking = False
        # self.frequency_center = 0
        # self.pulse_time = 0

        self.print('creating scan arguments')
        self.scan_arguments(
            nrepeats={'default': 50},
            times={'start': 0*us, 'stop': 40*us, 'npoints': 40, 'ndecimals': 0, 'global_step': 1*us},
            frequencies={'start': -0.1*MHz, 'stop': 0.1*MHz, 'npoints': 50, 'global_step': 0.1*MHz}
        )
        self.setattr_argument('run_on_core', BooleanValue(default=False), show=True)
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
        self.model = BetaTimeFreqModel(self,
                                   namespace='beta',
                                   fit_function=Sinc if self.scan == 'frequency' else InvCos,
                                   simulation_args={
                                        'frequency': self.get_dataset('beta.frequency'),
                                        'y_min': 0,
                                        'y_max': 20,
                                        'pi_time': self.get_dataset('beta.pi_time')
                                   } if self.scan=='frequency' else {
                                         'amplitude': 10,
                                         'pi_time': self.get_dataset('beta.pi_time'),
                                         'phase': 0,
                                         'y_min': 0
                                   },
                                   time_fit='pi_time',
                                   frequency_fit='frequency'
                                   )
        print('simulation_args is', self.model.simulation_args)
        self.register_model(self.model, measurement=True, fit=True, bind=True, auto_track=True)
        self.last_i = -1

    def simulate(self, time, freq, i) -> TInt32:
        if i != self.last_i:
            print('measure(time={:0.1f} us, freq={:0.1f} MHz'.format(time/us, freq/MHz))
        if self.scan == 'frequency':
            return self.model.simulate(freq)
        else:
            return self.model.simulate(time)

    @portable
    def measure(self, time, freq):
        return self.simulate(time, freq, self.looper.itr.i)
