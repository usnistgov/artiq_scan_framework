from artiq.experiment import *
from artiq_scan_framework.beta.scan import BetaScan
from .time_scan import TimeScan
from .freq_scan import FreqScan
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
        argdef['scan'] = {
            'processor': EnumerationValue,
            'processor_args': {
                'choices': ['frequency', 'time'],
                'default': 'frequency',
            },
            'group': 'Scan Range',
            'tooltip': None
        }
        argdef.update(TimeScan.argdef())
        argdef.update(FreqScan.argdef())

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
            'condition': lambda scan, kwargs : (not scan.enable_auto_tracking) and scan.frequency_center is None
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
            'condition': lambda scan, kwargs: not scan.enable_auto_tracking and scan.pulse_time is None
        }
        return argdef

    def _attach_models(self):
        print('call: TimeFreqScan::_attach_models()')
        self.__bind_models()
        print('self._x_offset={}'.format(self._x_offset))
        print('self.frequency_center={}'.format(self.frequency_center))
        if not self.fit_only:
            # the frequency center is auto loaded from the fits by this class...
            if self.enable_auto_tracking:
                for entry in self._model_registry:
                    model = entry['model']
                    if 'auto_track' in entry and entry['auto_track']:
                        # fetch the last fitted frequency and time values from the datasets
                        self.print('TimeFreqScan::_get_main_fits()', 2)
                        restore = model.type if hasattr(model, 'type') else None
                        if hasattr(model, 'frequency_fit'):
                            fitted_freq = model.get(model.frequency_fit)
                        else:
                            # get the last fitted frequency
                            model.type = 'frequency'
                            model.bind()
                            fitted_freq = model.get_main_fit(archive=False)
                        if hasattr(model, 'time_fit'):
                            fitted_time = model.get(model.time_fit)
                        else:
                            # get the last fitted time
                            model.type = 'time'
                            model.bind()
                            fitted_time = model.get_main_fit(archive=False)
                        # rebind the model to it's original namespace
                        model.type = restore
                        model.bind()
                        self.print('TimeFreqScan::_get_main_fits()', -2)
                        # hasn't been set yet, ok to auto load
                        if self.frequency_center is None:
                            # set frequency center from saved fit values
                            self.frequency_center = fitted_freq
                            self.print('auto set frequency_center to {0} from fits'.format(fitted_freq))
                            # self._logger.warn("auto set frequency_center to {0} from fits".format(fitted_freq))
                        # hasn't been set yet, ok to auto load
                        if self.pulse_time is None:
                            # set pulse time from saved fit values
                            self.pulse_time = fitted_time
                            self.print('auto set pulse_time to {0} from fits'.format(fitted_time))
                            # self._logger.warn("auto set pulse_time to {0} from fits".format(fitted_time))
            if self.frequency_center is not None:
                self.frequency_center = np.float64(self.frequency_center)
            else:
                if self.scan == 'time' and self.enable_auto_tracking:
                    self.logger.warning(
                        "scan.frequency_center is None.  Did you forget to register a model with auto_track=True?")
            if self.pulse_time is not None:
                self.pulse_time = np.float64(self.pulse_time)
            else:
                if self.scan == 'frequency' and self.enable_auto_tracking:
                    self.logger.warning(
                        "scan.pulse_time is None.  Did you forget to register a model with auto_track=True?")
        # tell scan to offset x values by the frequency_center
        # this is done even when not auto-tracking in case the user has manually set frequency_center
        if self.scan == 'frequency' and self.frequency_center is not None:
            self._x_offset = self.frequency_center
        print('self._x_offset={}'.format(self._x_offset))

    def __bind_models(self):
        # bind each registered model to the scan type (frequency or time)
        for entry in self._model_registry:
            # tell the model if this a frequency or time scan
            entry['model'].type = self.scan

            # bind model namespace to scan type
            if ('bind' in entry and entry['bind']) or (
                    self.enable_auto_tracking and 'auto_track' in entry and entry['auto_track']):
                entry['model'].bind()

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

