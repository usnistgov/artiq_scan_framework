# Real world example scan: shim scan
#
# Author: Philip Kent / NIST Quantum Processing Group
#
# Note: This example cannot be run as a number of dependencies are not included.
# This scan is provided to give an example of usage of the scan framework in
# an actual lab experiment.



from artiq.experiment import *
from scan_framework import *
from lib.stylus_scan import *
from lib.models.shim_model import *
from lib.cooling import *
from lib.detection import *
from lib.shims import *
from lib.loading import *


class ShimScan(Scan1D, ReloadingScan, EnvExperiment):
    """ Shim Scan

    Scans the x, y, and z shim voltage.
    """

    def build(self, **kwargs):
        super().build(**kwargs)

        # arguments
        self.setattr_argument('shim', EnumerationValue(['x', 'y', 'z']))
        self.scan_arguments('top')
        self.setattr_argument('npasses', NumberValue(default=2, ndecimals=0, step=1), group = 'Scan Settings')
        self.setattr_argument('offsets', Scannable(default=LinearScan(
            start=-0.3,
            stop=0.3,
            npoints=40),
            scale=1,
            unit="volts",
            ndecimals=3), 'Scan Range')
        self.scan_arguments('bottom')

    def prepare(self):
        self.cooling = Cooling(self)
        self.detection = Detection(self)
        self.shims = Shims(self)
        self.loading = Loading(self, detection=self.detection)
        self.model = ShimScanModel(self, type=self.shim)
        self.register_model(self.model, measurement=True, fit=True)

    def prepare_scan(self):
        self.shims.load_voltages()

    def get_scan_points(self):
        return self.offsets

    @kernel
    def initialize_devices(self):
        self.core.reset()
        self.cooling.contain()

        # setup spi bus for shims
        self.core.break_realtime()
        self.shims.setup_bus()
  
    @kernel
    def set_scan_point(self, offset):
        """Set the shim voltage for the current scan point"""
        self.core.break_realtime()
        self.shims.offset(self.shim, offset)

    @kernel
    def measure(self, offset):
        self.cooling.doppler()
        counts = self.detection.detect()
        return counts

    @kernel
    def cleanup(self):
        """reset shims to setup values"""
        self.core.break_realtime()
        self.shims.reset()
