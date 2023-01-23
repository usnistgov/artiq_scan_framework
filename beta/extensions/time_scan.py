from artiq.experiment import *
from artiq_scan_framework.beta.scan import BetaScan
from collections import OrderedDict
import numpy as np


class TimeScan(BetaScan):
    """Scan class for scanning over time values."""

    def build(self, **kwargs):
        self.print('TimeScan.build()', 2)
        self.scan_arguments(TimeScan, init_only=True)
        super().build(**kwargs)
        self.print('TimeScan.build()', -2)

    @staticmethod
    def argdef():
        argdef = OrderedDict()
        argdef['times'] = {
            'processor': Scannable,
            'processor_args': {
                'default': RangeScan,
                'unit': 'us',
                'scale': 1 * us,
                'global_step': 10 * us,
                'ndecimals': 3,
            },
            'default_args': {'start': 0, 'stop': 10 * us, 'npoints': 50},
            'group': 'Scan Range',
            'tooltip': None
        }
        return argdef

    def get_scan_points(self):
        return self.times

