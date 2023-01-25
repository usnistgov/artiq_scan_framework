from .scan_model import *


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
            return 'Pulse time'

    @property
    def main_fit(self):
        """Return the dataset name where the main fit is saved for the type of scan that is being run
        (frequency or time)."""
        if self.type == 'frequency':
            if hasattr(self, 'frequency_fit'):
                return self.frequency_fit
            else:
                return 'frequency'
        if self.type == 'time':
            if hasattr(self, 'time_fit'):
                    return self.time_fit
            else:
                return 'pi_time'