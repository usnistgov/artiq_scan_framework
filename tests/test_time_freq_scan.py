"""
Microwave Scan Class
Scans frequencies and pulse times of microwave transitions after
ion has been cooled by doppler cooling
"""

# artiq_scan_framework modules
from artiq.experiment import *
from artiq_scan_framework import *
from artiq_scan_framework.analysis.fit_functions import Sinc, InvCos


class MyScanModel(TimeFreqModel):
    namespace = 'test'

    @property
    def fit_function(self):
        if self._scan.scan == 'frequency':
            return Sinc
        else:
            return InvCos

    @property
    def simulation_args(self):
        if self._scan.scan == 'frequency':
            return {
                'frequency': self.get('frequency'),
                'y_min': 0,
                'y_max': 20,
                'pi_time': self.get('pi_time')
            }
        else:
            return {
             'amplitude': 10,
             'pi_time': self.get('pi_time'),
             'phase': 0,
             'y_min': 0
        }

class MyScanModelExplicit(MyScanModel):

    time_fit = 'pi_time'
    frequency_fit = ['frequency', 'frequency']

class MyScanModelImplicit(MyScanModel):

    @property
    def main_fit(self):
        if self._scan.scan == 'frequency':
            return 'frequency'
        else:
            return 'pi_time'


class TestTimeFreqScan(Scan1D, TimeFreqScan, EnvExperiment):


    def build(self, **kwargs):
        #self.print('TestTimeFreqScan::build()', 2)
        super().build(**kwargs)
        #
        # self.enable_auto_tracking = False
        # self.frequency_center = 0
        # self.pulse_time = 0

        #self.print('creating scan arguments')
        self.scan_arguments(
            fit_options={'default': 'Fit and Save'},
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
        self.setattr_argument('manually_offset_x', BooleanValue(default=False), show=True)
        self.setattr_argument('explicit_time_freq_params', BooleanValue(default=False), show=True)

        # self.scan_arguments(
        #     nrepeats={'default': 50},
        #     frequencies={'start': -0.1 * MHz, 'stop': 0.1 * MHz, 'npoints': 50},
        #     times={'start': 0, 'stop': 40 * us, 'npoints': 50},
        #     fit_options={'default': 'Fit and Save'},
        #     scan=False,
        # )
        #self.print('TestTimeFreqScan::build()', -2)

    def prepare(self):
        if self.manually_offset_x:
             self._x_offset = 1.1*MHz
        if self.explicit_time_freq_params:
            self.model = MyScanModelExplicit(self, _scan=self)
        else:
            self.model = MyScanModelImplicit(self, _scan=self)
        print('simulation_args is', self.model.simulation_args)
        self.register_model(self.model, measurement=True, fit=True, bind=True, auto_track=True)


        self.last_i = -1

    def simulate(self, time, freq, i) -> TInt32:
        if i != self.last_i:
            pass
            #print('measure(time={:0.1f} us, freq={:0.1f} MHz'.format(time/us, freq/MHz))
        if self.scan == 'frequency':
            return self.model.simulate(freq)
        else:
            return self.model.simulate(time)

    @portable
    def measure(self, time, freq):
        return self.simulate(time, freq, self.looper.itr.i)
