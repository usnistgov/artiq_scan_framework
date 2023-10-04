from artiq.experiment import *
from ..scan import Scan
from collections import OrderedDict


class TimeScan(Scan):
    """Scan class for scanning over time values."""

    def build(self, **kwargs):
        self.scan_arguments(TimeScan, init_only=True)
        super().build(**kwargs)

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