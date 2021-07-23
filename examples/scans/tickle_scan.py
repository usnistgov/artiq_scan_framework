# Real world example scan: tickle scan
# Demonstrates how to extend an already defined scan.
#
# Author: Philip Kent / NIST Quantum Processing Group
#
# Note: This example cannot be run as a number of dependencies are not included.
# This scan is provided to give an example of usage of the scan framework in
# an actual lab experiment.


from artiq.experiment import *
from scan_framework import *
from lib.models.tickle_model import *
import lib.device_params as params
from lib.detection import *
from lib.cooling import *
from lib.microwaves import *
from lib.shims import *


class TickleScan(Scan1D, FreqScan, EnvExperiment):
    """Tickle Scan
    Scans the tickle frequency.
    """

    # features for the Secular Frequency Calibration scan, but can be used in normal tickle scans as well
    enable_auto_tracking = False
    offset_shims = False
    mode1_shim_offset = 0.0
    mode2_shim_offset = 0.0

    def build(self, **kwargs):
        super().build(**kwargs)

        # devices
        self.setattr_device('ttl_tickle')
        self.setattr_device('dds_tickle')

        # arguments
        self.setattr_argument('mode', EnumerationValue(['mode_1', 'mode_2'], default='mode_1'))
        self.scan_arguments('top')
        self.setattr_argument('nrepeats', NumberValue(default=50, ndecimals=0, step=100), group='Scan Settings')
        self.setattr_argument('tickle_pulse_time', NumberValue(unit='us', scale=us, step=100*us, default=100*us))
        self.setattr_argument('tickle_amplitude', NumberValue(default=1.0))

        group = 'Scan Range'

        # for Secular Frequency Calibration Scan
        if self.enable_auto_tracking:
            self.setattr_argument('frequencies', Scannable(
                default=LinearScan(
                    start=-1*MHz,
                    stop=1*MHz,
                    npoints=50
                ),
                unit='MHz',
                scale=1 * MHz,
                ndecimals=4
            ), group=group)
        else:
            self.setattr_argument('frequencies', Scannable(
                default=LinearScan(
                    start=4,
                    stop=5 * MHz,
                    npoints=100
                ),
                unit='MHz',
                scale=1 * MHz,
                ndecimals=4
            ), group=group)

        if self.offset_shims:
            self.setattr_argument('mode1_shim_offset', NumberValue(default=0.2, step=0.1))
            self.setattr_argument('mode2_shim_offset', NumberValue(default=0.03, step=0.1))

        self.scan_arguments('bottom')

    def prepare(self):
        self.detection = Detection(self)
        self.cooling = Cooling(self)
        self.microwaves = Microwaves(self)
        self.shims = Shims(self)
        self.rf_trap_frequency = params.rf_trap_frequency
        self.model = TickleScanModel(self, mode=self.mode)
        self.register_model(self.model, measurement=True, fit=True, auto_track=True)

    def prepare_scan(self):
        self.shims.load_voltages()
        self.microwaves.load_transitions()

    @kernel
    def initialize_devices(self):
        """Called on core device at the very beginning of the scan."""

        # offset shims to induce micro-motion
        if self.offset_shims:

            # setup spi bus for shims
            self.core.break_realtime()
            self.shims.setup_bus()

            offset = 0.0
            if self.mode == 'mode_1':
                self.core.break_realtime()
                self.shims.offset('y', self.mode1_shim_offset)
            if self.mode == 'mode_2':
                self.core.break_realtime()
                self.shims.offset('x', self.mode2_shim_offset)

    @kernel
    def measure(self, frequency):
        # cool
        self.cooling.doppler()

        # induce micro-motion
        if self.auto_track:
            self.dds_tickle.set(self.rf_trap_frequency + frequency, amplitude=self.tickle_amplitude)
        else:
            self.dds_tickle.set(self.rf_trap_frequency + frequency, amplitude=self.tickle_amplitude)
        delay(const.set_dds_delay)
        self.ttl_tickle.pulse(self.tickle_pulse_time)
        delay(2*us)
        # Messing around with Histograms hack 6/2/17
        #self.microwaves.transition_1()

        # detect
        counts = self.detection.detect()
        return counts

    @kernel
    def cleanup(self):
        # set shims back to their dataset values
        if self.offset_shims:
            self.core.break_realtime()
            self.shims.reset()
