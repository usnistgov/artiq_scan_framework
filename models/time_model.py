from scan_framework.models.scan_model import *


class TimeModel(ScanModel):

    @property
    def x_units(self):
        return 's'

    @property
    def x_label(self):
        return 'Time'
