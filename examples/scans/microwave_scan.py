# Real world example scan: microwave scan
# Demonstrates how to use the TimeFreqScan class with auto-tracking
#
# Author: Philip Kent / NIST Quantum Processing Group
#
# Note: This example cannot be run as a number of dependencies are not included.
# This scan is provided to give an example of usage of the scan framework in
# an actual lab experiment.


from artiq.experiment import *
from scan_framework.scans import *
from scan_framework.models import *
from scan_framework.analysis.curvefits import AtomLine, Sine


class MicrowaveScan(Scan1D, TimeFreqScan, EnvExperiment):
    """Microwave scan

    Scans frequencies and pulse times of microwave transitions
    """

    def build(self, **kwargs):
        super().build(**kwargs)

        # The atomic transition, identified by an integer to simply logic in
        # the "measure()" method
        self.setattr_argument('transition', EnumerationValue(
            ['0', '1', '2', '3', '4', '5', '6', '7'],
            default='1'))

        # scan settings, scan ranges, etc.
        self.scan_arguments(
            # frequency range can be customized
            frequencies={
                'start': -0.3 * MHz,
                'stop': 0.3 * MHz
            },
            # time range can also be customized
            times={
                'start': 0 * us,
                'stop': 20 * us
            }
        )

        # create devices, instantiate libs, etc.
        ...

    def prepare(self):
        # convert string transition to integer for the "measure()" method
        self.transition = int(self.transition)

        # create and register the scan model
        self.model = MicrowavesScanModel(self,
                                         # set the model's transition attribute to the selected transition in the GUI.
                                         # this allows the %transition token in the model namespace to be replaced
                                         # by the current transition.
                                         transition=self.transition
                                         )
        self.register_model(self.model,
                            # calculate statistics and store all data to the datasets
                            measurement=True,
                            # perform a final fit to the data
                            fit=True,
                            # points will be offset by this model's last fitted frequency value
                            # (a.k.a. it's main fit)
                            auto_track='fit')

    @kernel
    def initialize_devices(self):
        self.core.reset()

    @kernel
    def measure(self, time, frequency):
        self.cooling.doppler()

        if self.transition >= 2:
            self.microwaves.transition_1()
        if self.transition >= 3:
            self.microwaves.transition_2()
        if self.transition >= 4:
            self.microwaves.transition_3()
        if self.transition >= 5:
            self.microwaves.transition_4()

        # pulse dds
        self.microwaves.set_frequency(frequency)
        self.microwaves.pulse(time)

        # detect
        counts = self.detection.detect()
        return counts


class MicrowavesScanModel(TimeFreqModel):
    """Microwave scan model

    Processes data from microwave scans
    """

    # %transition will be replaced by the transition selected in the GUI
    namespace = 'microwaves.%transition'
    y_label = 'Counts'

    # scales for formatting fit params printed to the log window
    scales = {
        'f': {
            'scale': MHz,
            'unit': 'MHz'
        },
        'phi': {
            'scale': 3.14159,
            'unit': 'pi'
        },
        'f0': {
            'scale': MHz,
            'unit': 'MHz'
        },
        'Omega0': {
            'scale': MHz,
            'unit': 'MHz'
        },
        'T': {
            'scale': us,
            'unit': 'us'
        }
    }

    @property
    def main_fit(self):
        if self.type == 'frequency':
            # save fit param 'f0' to dataset named 'frequency'
            return ['f0', 'frequency']
        if self.type == 'time':
            # save calculated fit param 'pi_time'
            return 'pi_time'

    def before_validate(self, fit):
        # calculate the fit param 'pi_time' from the fit param 'f'
        if self.type == 'time':
            fit.fitresults['pi_time'] = 1 / (2 * fit.fitresults['f'])

    @property
    def fit_function(self):
        if self.type == 'frequency':
            # frequency scans use the AtomLine fit function
            return AtomLine
        elif self.type == 'time':
            # times scans use the Sine fit function
            return Sine
        else:
            raise Exception('Unknown scan type {}'.format(self.type))

    @property
    def man_scale(self):
        # fit parameter scales, used by analysis.curvefits while fitting
        if self.type == 'frequency':
            return {
                'A': 1,
                'Omega0': 1 / (10 * us),
                'T': 1 * us,
                'f0': 1 * GHz,
                'y0': 1
            }
        else:
            return {
                'A': 10,
                'f': 1 / (10 * us),
                'phi': 1,
                'y0': 1
            }

    @property
    def guess(self):
        # fit parameter guesses, used by analysis.curvefits while fitting
        if self.type == 'time':
            if self.transition in [1, 3, 5, 6, 7]:
                return {
                    'phi': 0.5 * 3.14159,
                    'y0': 5,
                    'A': 5,
                }
            else:
                return {
                    'phi': 1.5 * 3.14159,
                    'y0': 5,
                    'A': 5,
                }
        else:
            return {
                'T': self.get('pi_time', archive=False)
            }