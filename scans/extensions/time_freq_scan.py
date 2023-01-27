from artiq.experiment import *
from ..scan import Scan
from .time_scan import TimeScan
from .freq_scan import FreqScan
from ...components.auto_track import AutoTrack
from collections import OrderedDict
import numpy as np


class TimeFreqScan(Scan):
    """Allows a scan experiment to scan over either a set of time values or a set of frequency values."""
    frequency_center = None  # default must be None so it can be overriden in the scan
    pulse_time = None  # default must be None so it can be overriden in the scan
    enable_auto_tracking = True

    def build(self, **kwargs):
        #self.print('TimeFreqScan.build()', 2)
        self.scan_arguments(TimeFreqScan, init_only=True)
        super().build(**kwargs)
        #self.print('TimeFreqScan.build()', -2)

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
                'default': 100 * MHz,
                'unit': 'MHz',
                'scale': MHz,
                'step': 0.1 * MHz,
                'ndecimals': 4,
            },
            'group': 'Scan Range',
            'tooltip': None,
            'condition': lambda scan, kwargs: (not scan.enable_auto_tracking) and scan.frequency_center is None
        }
        argdef['pulse_time'] = {
            'processor': NumberValue,
            'processor_args': {
                'default': 10 * us,
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
        auto_track = AutoTrack()
        #self.print('TimeFreqScan::_attach_models()', 2)
        self.__bind_models()
        #self.print('self._x_offset={}'.format(self._x_offset))
        #self.print('self.frequency_center={}'.format(self.frequency_center))
        if not self.fit_only:
            # the frequency center is auto-loaded from the fits by this class...
            if self.enable_auto_tracking:
                for entry in self._model_registry:
                    model = entry['model']
                    if 'auto_track' in entry and entry['auto_track']:
                        if self.frequency_center is None:
                            if entry['auto_track'] == 'fitresults':
                                self.frequency_center = auto_track.get(model, use_fit_result=True, _type='frequency')
                                #self.print('auto set frequency_center to {0} from fits'.format(self.frequency_center))
                            elif entry['auto_track'] == 'fit' or entry['auto_track'] is True:
                                self.frequency_center = auto_track.get(model, use_fit_result=False, _type='frequency')
                                #self.print('auto set frequency_center to {0} from fits'.format(self.frequency_center))

                        if self.pulse_time is None:
                            if entry['auto_track'] == 'fitresults':
                                self.pulse_time = auto_track.get(model, use_fit_result=True, _type='time')
                                self.logger.warn('auto set pulse_time to {0} from fits'.format(self.pulse_time))
                            elif entry['auto_track'] == 'fit' or entry['auto_track'] is True:
                                self.pulse_time = auto_track.get(model, use_fit_result=False, _type='time')
                                self.logger.warn('auto set pulse_time to {0} from fits'.format(self.pulse_time))

            # make ARTIQ compiler happy... make sure frequency_center and pulse_time are always float64's
            if self.frequency_center is not None:
                self.frequency_center = np.float64(self.frequency_center)
            else:
                # help user out.  let them know when they probably forgot to register an auto tracking model
                if self.scan == 'time' and self.enable_auto_tracking:
                    self.logger.warning(
                        "scan.frequency_center is None.  Did you forget to register a model with auto_track=True?")
            if self.pulse_time is not None:
                self.pulse_time = np.float64(self.pulse_time)
            else:
                # help user out.  let them know when they probably forgot to register an auto tracking model
                if self.scan == 'frequency' and self.enable_auto_tracking:
                    self.logger.warning(
                        "scan.pulse_time is None.  Did you forget to register a model with auto_track=True?")

        # tell scan to offset x values by the frequency_center
        # this is done even when not auto-tracking in case the user has manually set frequency_center
        if self.scan == 'frequency' and self.frequency_center is not None and self._x_offset is None:
            self._x_offset = self.frequency_center
        #self.print('TimeFreqScan::_attach_models()', -2)

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
