from .scan_model import *


class BetaTimeFreqModel(BetaScanModel):

    @property
    def x_units(self):
        if self._scan.scan == 'frequency':
            return 'Hz'
        if self._scan.scan == 'time':
            return 's'

    @property
    def x_label(self):
        if self._scan.scan == 'frequency':
            return 'Frequency'
        if self._scan.scan == 'time':
            return 'Pulse time'

    @property
    def main_fit(self):
        """Return the dataset name where the main fit is saved for the type of scan that is being run
        (frequency or time)."""
        if self._scan.scan == 'frequency':
            if hasattr(self, 'frequency_fit'):
                return self.frequency_fit
            else:
                return 'frequency'
        if self._scan.scan == 'time':
            if hasattr(self, 'time_fit'):
                    return self.time_fit
            else:
                return 'pi_time'