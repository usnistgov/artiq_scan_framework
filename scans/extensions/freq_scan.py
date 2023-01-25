from artiq.experiment import *
from ..scan import Scan
from collections import OrderedDict


class FreqScan(Scan):
    """Scan class for scanning over frequency values."""
    _freq_center_manual = None

    def build(self, **kwargs):
        self.print('FreqScan.build()', 2)
        self.scan_arguments(FreqScan, init_only=True)
        super().build(**kwargs)
        self.print('FreqScan.build()', -2)

    @staticmethod
    def argdef():
        argdef = OrderedDict()
        argdef['frequencies'] = {
            'processor': Scannable,
            'processor_args': {
                'default': RangeScan,
                'unit': 'MHz',
                'scale': 1 * MHz,
                'global_step': 0.1 * MHz,
                'ndecimals': 4,
            },
            'default_args': {'start': -5 * MHz, 'stop': 5 * MHz, 'npoints': 50},
            'group': 'Scan Range',
            'tooltip': None
        }
        return argdef

    def get_scan_points(self):
        return self.frequencies
