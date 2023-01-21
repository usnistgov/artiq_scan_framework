# Extensions to the base scan class which provide commonly used features.

from artiq_scan_framework.scans.extensions import TimeFreqScan
from artiq_scan_framework.beta.scan import BetaScan
from artiq.experiment import *
from collections import OrderedDict
import numpy as np

class TimeFreqScan(BetaScan):
    """Allows a scan experiment to scan over either a set of time values or a set of frequency values."""
    frequency_center = None  # default must be None so it can be overriden in the scan
    pulse_time = None  # default must be None so it can be overriden in the scan
    enable_auto_tracking = True

    def build(self, **kwargs):
        self.print('TimeFreqScan.build()', 2)
        self.scan_arguments(TimeFreqScan, init_only=True)
        super().build(**kwargs)
        self.print('TimeFreqScan.build()', -2)

    @staticmethod
    def argdef():
        argdef = OrderedDict()
        argdef['times'] = {
            'processor': Scannable,
            'processor_args': {
                'default': RangeScan,
                'default_args': {'start': 0, 'stop':10*us, 'npoints':50},
                'unit': 'us',
                'scale': 1 * us,
                'global_step': 10 * us,
                'ndecimals': 3,
            },
            'group': 'Scan Range',
            'tooltip': None
        }
        argdef['frequencies'] = {
            'processor': Scannable,
            'processor_args': {
                'default': RangeScan(start=-5 * MHz, stop=5 * MHz, npoints=50),
                'unit': 'MHz',
                'scale': 1 * MHz,
                'global_step': 0.1 * MHz,
                'ndecimals': 4,
            },
            'group': 'Scan Range',
            'tooltip': None
        }
        argdef['frequency_center'] = {
            'processor': NumberValue,
            'processor_args': {
                'default': 100*MHz,
                'unit': 'MHz',
                'scale': MHz,
                'step': 0.1 * MHz,
                'ndecimals': 4,
            },
            'group': 'Scan Range',
            'tooltip': None,
            'condition': lambda scan : not scan.enable_auto_tracking and scan.frequency_center is None
        }
        argdef['pulse_time'] = {
            'processor': NumberValue,
            'processor_args': {
                'default': 10*us,
                'unit': 'us',
                'scale': us,
                'step': 1 * us,
                'ndecimals': 4,
            },
            'group': 'Scan Range',
            'tooltip': None,
            'condition': lambda scan: not scan.enable_auto_tracking and scan.pulse_time is None
        }
        argdef['scan'] = {
            'processor': EnumerationValue,
            'processor_args': {
                'choices': ['frequency', 'time'],
                'default': 'frequency',
            },
            'group': 'Scan Range',
            'tooltip': None
        }
        return argdef

        # assign default values for scan GUI arguments
        # if times is not False:
        #     for k, v in {'start': 0, 'stop': 10 * us, 'npoints': 50, 'unit': 'us', 'scale': 1 * us, 'global_step': 10 * us, 'ndecimals': 3}.items():
        #         times.setdefault(k, v)
        # if frequencies is not False:
        #     for k, v in {'start': -5 * MHz, 'stop': 5 * MHz, 'npoints': 50, 'unit': 'MHz', 'scale': 1 * MHz, 'ndecimals': 4}.items():
        #         frequencies.setdefault(k, v)
        # if frequency_center is not False:
        #     for k, v in {'unit': 'MHz', 'scale': MHz, 'default': 100 * MHz, 'ndecimals': 4}.items():
        #         frequency_center.setdefault(k, v)
        #if pulse_time is not False:
            # for k, v in {'unit': 'us', 'scale': us, 'default': 100 * us, 'ndecimals': 4}.items():
            #     pulse_time.setdefault(k, v)
        # if scan is not False:
        #     for k, v in {'default': 'frequency', 'group': 'Scan Range'}.items():
        #         scan.setdefault(k, v)

        # create GUI argument to select if scan is a time or a frequency scan
        #if scan is not False:
            #group = scan['group']
            #del scan['group']
            #self.setattr_argument('scan', EnumerationValue(['frequency', 'time'], **scan), group)
        #
        # # create remaining scan arguments for time and frequency scans
        # if frequencies is not False:
        #     self.setattr_argument('frequencies', Scannable(
        #         default=RangeScan(
        #             start=frequencies['start'],
        #             stop=frequencies['stop'],
        #             npoints=frequencies['npoints']
        #         ),
        #         unit=frequencies['unit'],
        #         scale=frequencies['scale'],
        #         ndecimals=frequencies['ndecimals']
        #     ), group='Scan Range')

        # auto tracking is disabled...
        # ask user for the frequency center
        # if not self.enable_auto_tracking:
        #     if self.frequency_center is None:
        #         if frequency_center is not False:
        #             self.setattr_argument('frequency_center', NumberValue(**frequency_center), group='Scan Range')
        #
        #     if self.pulse_time is None:
        #         if pulse_time is not False:
        #             self.setattr_argument('pulse_time', NumberValue(**pulse_time), group='Scan Range')
        # if times is not False:
        #     self.setattr_argument('times', Scannable(
        #         default=RangeScan(
        #             start=times['start'],
        #             stop=times['stop'],
        #             npoints=times['npoints']
        #         ),
        #         unit=times['unit'],
        #         scale=times['scale'],
        #         global_step=times['global_step'],
        #         ndecimals=times['ndecimals']
        #     ), group='Scan Range')
    #
    # def scan_arguments(self, classes=[], classes_only=False, **kwargs):
    #     self.print('TimeFreqScan::scan_arguments()', 2)
    #     super().scan_arguments(classes, classes_only, **kwargs)
    #     self.print('TimeFreqScan::scan_arguments()', -2)

    def _attach_models(self):
        self.__bind_models()
        if not self.fit_only:
            self._load_frequency_center()

        # tell scan to offset x values by the frequency_center
        # this is done even when not auto-tracking in case the user has manually set frequency_center
        if self.scan == 'frequency' and self.frequency_center is not None:
            self._x_offset = self.frequency_center
            self._logger.debug("set _x_offset to frequency_center value of {0}".format(self.frequency_center))

    def __bind_models(self):
        # bind each registered model to the scan type (frequency or time)
        for entry in self._model_registry:
            # tell the model if this a frequency or time scan
            entry['model'].type = self.scan

            # bind model namespace to scan type
            if ('bind' in entry and entry['bind']) or (
                    self.enable_auto_tracking and 'auto_track' in entry and entry['auto_track']):
                entry['model'].bind()

    def _load_frequency_center(self):
        # frequency or pulse time manually set in the scan, state that in the debug logs
        if self.frequency_center is not None:
            self._logger.warn("frequency_center manually set to {0}".format(self.frequency_center))

        if self.pulse_time is not None:
            self._logger.warn("pulse_time manually set to {0}".format(self.pulse_time))

        # the frequency center is auto loaded from the fits by this class...
        if self.enable_auto_tracking:
            for entry in self._model_registry:
                model = entry['model']
                if 'auto_track' in entry and entry['auto_track']:

                    # fetch the last fitted frequency and time values from the datasets
                    fitted_freq, fitted_time = self._get_main_fits(model)

                    # hasn't been set yet, ok to auto load
                    if self.frequency_center is None:
                        # set frequency center from saved fit values
                        self.frequency_center = fitted_freq
                        #self._logger.warn("auto set frequency_center to {0} from fits".format(fitted_freq))

                    # hasn't been set yet, ok to auto load
                    if self.pulse_time is None:
                        # set pulse time from saved fit values
                        self.pulse_time = fitted_time
                        #self._logger.warn("auto set pulse_time to {0} from fits".format(fitted_time))

        self.frequency_center = np.float64(self.frequency_center)
        self.pulse_time = np.float64(self.pulse_time)

    def _get_main_fits(self, model):
        """Get's the last fitted frequency and time values"""

        if hasattr(model, 'type'):
            restore = model.type
        else:
            restore = None

        # get the last fitted frequency
        model.type = 'frequency'
        model.bind()
        freq = model.get_main_fit(archive=False)

        # get the last fitted time
        model.type = 'time'
        model.bind()
        time = model.get_main_fit(archive=False)

        # rebind the model to it's original namespace
        model.type = restore
        model.bind()

        return freq, time

    def get_scan_points(self):
        if self.scan == 'time':
            return self.times
        if self.scan == 'frequency':
            return self.frequencies

    @portable
    def do_measure(self, point):
        # time scan
        if self.scan == 'time':
            pulse_time = point
            return self.measure(pulse_time, self.frequency_center)

        # frequency scan
        if self.scan == 'frequency':
            return self.measure(self.pulse_time, point)
        return 0

    def report(self, location='both'):
        super().report(location)
        if location == 'bottom':
            self.logger.info("Type: %s scan" % self.scan)
            if self.scan == 'frequency':
                if self.frequency_center is not None:
                    self.logger.info('Frequency Center: %f MHz' % (self.frequency_center / MHz))
                if self.pulse_time is not None:
                    self.logger.info("Pulse Time: %f us" % (self.pulse_time / us))
            if self.scan == 'time':
                if self.frequency_center is not None:
                    self.logger.info('Frequency: %f MHz' % (self.frequency_center / MHz))

