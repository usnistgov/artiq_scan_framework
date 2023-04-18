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
        if r is False:
            raise Exception('Automation Terminated')
        else:
            scan.analyze()
        return scan


class CoreScanRunner(HasEnvironment):
    """Scan wrapper to run a scan multiple times on the core device"""

    def build(self, scan):
        self.setattr_device('core')
        self.setattr_device('scheduler')
        self.scan = scan
        self.logger = logging.getLogger()

    def prepare(self):
        self.scan.prepare()

    def init(self, resume=False, dynamic_attributes=[], kernel_invariants=[]):
        """Initializes the scan on the host before executing the scan multiple times on the core.

        Initializes core storage, binds datasets to the scan, and initializes datasets
        """
        self.scan._initialize(resume=resume)

        # remove/add kernel invariants
        self._make_dynamic(dynamic_attributes)
        self._make_invariant(kernel_invariants)

    @kernel
    def run(self):
        """Executes one run of the scan on the core and fits the data after the run is complete"""

        # run the scan
        self.scan._run_scan_core()
        if self.scan._paused:
            return True
        else:
            # note: after_scan_core and lab_after_scan_core will execute in _run_scan_core() and the ion will be contained
            # before fitting below on the host when the scan inherits from StylusContainScan

            self.scan.after_scan()

            # perform fit on host, this is an RPC call
            self.scan._analyzed = False
            self.scan._analyze()
            return False

    def _yield(self, callback):
        try:
            self.core.comm.close()
            self.scheduler.pause()
            callback()
        except TerminationRequested:
            self.scan.logger.warning("Scan terminated.")
            self.scan._terminated = True
            self.scan.looper.terminate()
        finally:
            pass

    @kernel
    def reset(self):
        # Must be called before syn_with_host() so that host variables are set.
        #   reset_scan_host() will reset the host variables (by calling scan._initialize()), and
        #   syn_with_host() expects that the host variables have been set when it is called.
        self._reset_scan_host()
        self.scan.looper.itr.sync_with_host()

    # RPC
    def _reset_scan_host(self):
        """Initializes the host copy of scan and it's model before each run on the core device."""
        self.scan._x_offset = None  # this is required so that Scan::_attach_models() sets scan._x_offset to the last fitted value when auto tracking
        if hasattr(self.scan, 'frequency_center'):
            self.scan.frequency_center = None  # this is required so that TTimeFreqScan::_attach_models() sets scan._x_offset to the last fitted value when auto tracking
        self.scan.enable_reporting = False
        self.scan._initialize(resume=False)
        self.scan.enable_reporting = True
        self.scan.model.fits_saved = {}

    def _make_dynamic(self, attributes):
        """Transforms scan attributes into dynamic variables that an be changed on the core"""
        for attr in attributes:
            if attr in self.scan.kernel_invariants:
                self.scan.kernel_invariants.remove(attr)

    def _make_invariant(self, attributes):
        """Transforms scan attributes into dynamic variables that an be changed on the core"""
        for attr in attributes:
            if attr not in self.scan.kernel_invariants:
                self.scan.kernel_invariants.add(attr)
