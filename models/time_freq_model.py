from scan_framework.models.scan_model import *


class TimeFreqModel(ScanModel):

    @property
    def x_units(self):
        if self.type == 'frequency':
            return 'Hz'
        if self.type == 'time':
            return 's'

    @property
    def x_label(self):
        if self.type == 'frequency':
            return 'Frequency'
        if self.type == 'time':
            return 'Pulse Time'
