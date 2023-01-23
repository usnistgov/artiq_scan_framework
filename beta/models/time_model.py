from .scan_model import *


class BetaTimeModel(BetaScanModel):

    @property
    def x_units(self):
        return 's'

    @property
    def x_label(self):
        return 'Time'
