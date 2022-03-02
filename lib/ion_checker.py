@portable
def lost_ion_threshold(data, length, threshold):
    """Analyze data to determine if the data collected for the last scan point indicates that an ion is still present in the trap.  
    Returns True if it was determined that an ion is still present and False otherwise."""
    
        
class IonChecker:
    def __init__(self, logger, loading, measure_thresholds=True, max_data_signals=2, dark_fraction=[0.9, 1.5], thresholds=[0.6, 2.0]):
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
        self.measure_thresholds = measure_thresholds
        
        # rewind to the earliest scan point where the ion could have been lost.
        self.rewind_num_points = max_data_signals
        
        self.setattr_argument("measure_thresholds", BooleanValue(default=False), 'Ion Checker')
    
    @kernel
    def initialze(self, resume):
        if self.measure_thresholds and not resume:
            # check if ion is present before measuring background
            if self.present_detection(repeats=2):
                # measure the thresholds
                self.logger.debug('> measuring background.')
                self.measure_thresholds()
            # no ion is present, can't measure thresholds
            else:
                self.logger.warning("Can't measure thresholds because no ion is present.")
                raise RewindAndLoadIon
        else:
            self.logger.debug('Skipping background measurement.')
    
    @kernel
    def measure_thresholds(self):
        """Measure dark rate and  set self.thresholds to a percentage of the measured rate."""
        dark_rate = self.loading.measure_dark_rate()
        self.thresholds = [
            self.dark_fraction[0] * dark_rate
            self.dark_fraction[1] * dark_rate
        ]

        self.logger.debug("dark_rate measured at")
        self.logger.debug(dark_rate)
        self.logger.debug("ion_threshold set to")
        self.logger.debug(self.ion_threshold)
        self.logger.debug("ion_second_threshold set to")
        self.logger.debug(self.ion_second_threshold)
    
    @kernel
    def ion_present(self, data, length, last_point=False):
        if last_point:
            if not self.present_detection():
                raise LostIon
            else:
                raise IonPresent
        else:
            if not self.ion_present_data(data, length):
                if not self.ion_present_detection_check():
                    raise LostIon
    
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
    def ion_present_detection_check(self, repeats=1):
        return self.loading.ion_present(repeats, threshold=self.thresholds[1])
        