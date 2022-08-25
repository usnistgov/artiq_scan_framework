from artiq.experiment import *
from artiq.experiment import *
import logging


class Automation:
    """Utility for automating scans"""

    @staticmethod
    def run_scan(scan):
        """Helper method to run a scan manually from another experiment or sub-component"""
        scan.prepare()
        r = scan.run()
        if r == False:
            raise Exception('Automation Terminated')
        else:
            scan.analyze()
        return scan


class CoreScanRunner(HasEnvironment):
    """Scan wrapper to run a scan multiple times on the core device"""

    def build(self, scan):
        self.scan = scan
        self.logger = logging.getLogger()

    def initialize(self, addtl={}, dynamic_attributes=[], kernel_invariants=[]):
        """Initializes the scan on the host before executing the scan multiple times on the core.

        Initializes core storage, binds datasets to the scan, and initializes datasets
        """

        # call prepare
        self.scan.prepare()

        for key, val in addtl.items:
            if key == 'TimeFreqScan':
                self._initialize_time_freq_scan(val['_type'])


        # initialize storage, etc.
        # initialize things common to each scan run like initializing point storage and running callbacks
        self.initialize_scan()

        # remove/add kernel invariants
        self.make_dynamic(dynamic_attributes)
        self.make_invariant(kernel_invariants)

    def _initialize_time_freq_scan(self, _type, dynamic_attributes=[], kernel_invariants=[]):
        # force manual auto-tracking
        self.scan.enable_auto_tracking = False
        self.scan.frequency_center = 0.0
        self.scan.pulse_time = 0.0

        # auto tracking is disabled so we have to set model type to 'frequency' or 'time' ourselves
        self.scan.model.type = _type

    def initialize_scan(self):
        """Initializes the host copy of scan and it's model before each run on the core"""
        self.scan.enable_reporting = False
        self.scan._initialize(resume=False)
        self.scan.enable_reporting = True
        self.scan.model.fits_saved = {}

    # RPC
    def initialize_time_freq_scan_rpc(self, transition) -> TList(TFloat):

        # bind modselfel to new transition
        model = self.scan.model
        model.transition = transition
        model.bind()

        # get pi_time, frequency, and amplitude
        model.bind()
        model.type = 'frequency'
        frequency = model.get_main_fit(archive=False)  # last fitted frequency
        model.type = 'time'
        pi_time = model.get_main_fit(archive=False)  # last fitted pi time
        amplitude = model.get('amplitude', archive=False)  # dds amplitude
        model.type = _type

        if _type == 'frequency':
            point_scale = 2 / pi_time / (self.scan.npi_pulses + 1)
        else:
            point_scale = self.scan.nflops * 2 * pi_time

        # init datasets, etc.
        self.init_sub_scan()

        data = [pi_time, frequency, amplitude, point_scale]
        return data

    def pause(self):
        """Yield to scheduled experiments with higher priority"""
        try:
            self.scan.core.comm.close()
            self.scan.scheduler.pause()
        except TerminationRequested:
            self.logger.warning("Calibration terminated.")
            raise TerminationRequested()

    @kernel
    def run_and_fit(self):
        """Executes one run of the scan on the core and fits the data after the run is complete"""

        # run the scan
        self.logger.debug('calibration: running core scan')
        self.scan._run_scan_core()
        if self.scan._paused:
            self.pause()
        else:
            # note: after_scan_core and lab_after_scan_core will execute in _run_scan_core() and the ion will be contained
            # before fitting below on the host when the scan inherits from StylusContainScan

            self.scan.after_scan()

            # perform fit on host, this is an RPC call
            self.logger.debug('calibration: fitting')
            self.scan._analyzed = False
            self.scan._analyze()

    # --- helpers ---
    def make_dynamic(self, attributes):
        """Transforms scan attributes into dynamic variables that an be changed on the core"""
        for attr in attributes:
            if attr in self.scan.kernel_invariants:
                self.scan.kernel_invariants.remove(attr)

    def make_invariant(self, attributes):
        """Transforms scan attributes into dynamic variables that an be changed on the core"""
        for attr in attributes:
            if attr not in self.scan.kernel_invariants:
                self.scan.kernel_invariants.add(attr)
