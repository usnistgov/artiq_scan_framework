from scan_framework.models.scan_model import *


class FreqModel(ScanModel):

    @property
    def x_units(self):
        return 'Hz'

    @property
    def x_label(self):
        return 'Frequency'