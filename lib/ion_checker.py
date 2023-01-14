from artiq.experiment import *
from ..exceptions import *
from ..snippets import *


@portable
def lost_ion_threshold(data, length, threshold):
    """Analyze data to determine if the data collected for the last scan point indicates that an ion is still present in the trap.  
    Returns True if it was determined that an ion is still present and False otherwise."""
    
        
class IonChecker(HasEnvironment):
    def build(self, logger, loading, measure_thresholds=None, max_data_signals=2, dark_fraction=[0.9, 1.5], thresholds=[0.4, 1.5]):
        """
        :param max_data_signals: Number of lost ion signals seen in data before a detection check is performed]
        """
        self.measure_thresholds = measure_thresholds
        self.loading = loading
        self.data_signal_counter = 0
        self.max_data_signals = max_data_signals
        self.dark_fraction = dark_fraction
        self.logger = logger
        self.thresholds = thresholds

        self.setattr_device('core')

        # rewind to the earliest scan point where the ion could have been lost.
        self.rewind_num_points = max_data_signals + 2
        
        setattr_argument(self, "measure_thresholds", BooleanValue(default=True), 'Ion Checker')
    
    @kernel
    def initialze(self, resume):
        if self.measure_thresholds and not resume:
            # check if ion is present before measuring background
            if self.ion_present_detection():
                # measure the thresholds
                #self.logger.debug('> measuring background.')
                self.run_measure_thresholds()
            # no ion is present, can't measure thresholds
            else:
                self.logger.warning("Can't measure thresholds because no ion is present.")
                raise LoadIon
        #else:
        #    pass
            #self.logger.debug('Skipping background measurement.')
    
    @kernel
    def run_measure_thresholds(self):
        """Measure dark rate and  set self.thresholds to a percentage of the measured rate."""
        bright_rate = self.loading.measure_bright_rate()
        dark_rate = self.loading.measure_dark_rate()
        #self.logger.info('measuring thresholds')
        # likely that we do know the MW T1 frequency
        comp = (bright_rate - dark_rate) / dark_rate  # compare bright to dark to see if we know the MW T1 frequency
        if comp < 0:  # take abs(comp)
            comp = -comp
        if comp > 0.75:
            self.thresholds[0] = self.dark_fraction[0] * dark_rate
            self.thresholds[1] = self.dark_fraction[1] * dark_rate
        # likely that we don't know the MW T1 frequency
        else:
            # Simply use the default thresholds passed to build()
            #self.thresholds[0] = self.dark_fraction[0] * dark_rate
            #self.thresholds[1] = self.dark_fraction[1] * dark_rate
            pass

        # self.logger.warn('dark_fraction is set to')
        # self.logger.warn(self.dark_fraction)
        # self.logger.warn("dark_rate measured at")
        # self.logger.warn(dark_rate)
        # self.logger.warn("thresholds set to")
        # self.logger.warn(self.thresholds)
    
    @kernel
    def ion_present(self, data, length, last_point=False):
        if last_point:
            if not self.ion_present_detection():
                raise LostIon
        else:
            if not self.ion_present_data(data, length):
                if not self.ion_present_detection():
                    raise LostIon
        raise IonPresent

    @kernel
    def ion_present_data(self, data, length):
        sum_ = 0.0
        for i in range(length):
            sum_ += data[i]
        mean = sum_ / length
        if mean >= self.thresholds[0]:
            self.data_signal_counter = 0
        else:
            self.data_signal_counter += 1
            
        if self.data_signal_counter == self.max_data_signals:
            self.data_signal_counter = 0
            return False
        else:
            return True

    @kernel        
    def ion_present_detection(self):
        return self.loading.ion_present(threshold=self.thresholds[1])
        