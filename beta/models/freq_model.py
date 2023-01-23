from .scan_model import *


class BetaFreqModel(BetaScanModel):

    @property
    def x_units(self):
        return 'Hz'

    @property
    def x_label(self):
        return 'Frequency'