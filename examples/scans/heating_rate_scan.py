# Real world example scan: heating rate scan
#
# Author: Philip Kent / NIST Quantum Processing Group
#
# Note: This example cannot be run as a number of dependencies are not included.
# This scan is provided to give an example of usage of the scan framework in
# an actual lab experiment.

# Include the scan_framework files.
from artiq.experiment import *
from scan_framework import *

# Include the model for this scan.
# Source code is in examples/models/heating_rate.py.
from scan_framework.examples.models.heating_rate import *

# Lab specific libraries not included in the scan_framework source.
# Included for illustrative purposes.
from lib.detection import *
from lib.cooling import *
from lib.raman import *
from lib.microwaves import *
from lib.analysis import *
from lib.loading import *


class HeatingRateScan(Scan1D, ReloadingScan, EnvExperiment):
    """Example Heating Rate Scan
    Scans the amount of time the ion is allowed to heat after being cooled
    to the ground state.  Both a RSB & BSB transition are performed at each scan point
    followed by a calculation of nbar.  A linear fit to nbar is performed after
    scan completes to give the heating rate.

    This example demonstrates how to:
        1. Define and use multiple measurements.
        2. Perform calculations.
        3. Define a list of scan points for the framework with the `get_scan_points` callback.
        4. Use the `ReloadingScan` class to detect and reload lost ions.
        5. Override a default scan argument in the dashboard.
        6. Use the `before_pass` callback.
        7. Perform manual calculations.
    """

    # `ReloadingScan` settings:
    # These settings control how lost ion detection and reloading is performed by the `ReloadingScan` class
    perc_of_dark = 98

    def build(self, **kwargs):
        super().build(**kwargs)

        # Create ARTIQ devices.
        self.setattr_device('ttl_rp')
        self.setattr_device('dds_rp')

        # Dashboard arguments specific to this scan.
        # (These appear before the scan arguments)
        self.setattr_argument('shelving_on', BooleanValue(default=True), group='Detection')
        self.setattr_argument('raman_readout_time', NumberValue(unit='us', scale=us, default=55*us), group='Raman')
        self.setattr_argument('mode', EnumerationValue(['mode_1', 'mode_2'], default='mode_1'))

        # Create the scan arguments.
        # (These are all dashboard arguments specific to/need by  the scan_framework)
        self.scan_arguments()

        # Override default scan arguments in the dashboard.
        self.setattr_argument('npasses', NumberValue(default=5, ndecimals=0, step=1), group='Scan Settings')
        self.setattr_argument('nrepeats', NumberValue(default=150, ndecimals=0, step=1), group='Scan Settings')

        # Dashboard arguments specific to this scan.
        # (These appear after the scan arguments)

        # Range of wait times.
        self.setattr_argument('times', Scannable(
            default=LinearScan(
                start=10 * us,
                stop=1000 * us,
                npoints=5
            ),
            unit='us',
            scale=1 * us
        ), group='Scan Range')

        # Define the measurements to perform at each scan point.
        # Here we will perform a red motional sideband measurement (rsb),
        # a blue motional sideband measurement (bsb), and a measurement of the background counts (bkg)
        self.measurements = ['rsb', 'bsb', 'bkgd']

    # Return the list of scan points to the scan framework.
    def get_scan_points(self):
        return self.times

    def prepare(self):
        # Lab specific:
        # Create the lab specific libraries.
        self.cooling = Cooling(self)
        self.raman = Raman(self)
        self.detection = Detection(self)
        self.microwaves = Microwaves(self)
        self.loading = Loading(self, detection=self.detection)

        # Create the scan models for each measurement.
        self.bsb_model = BsbModel(self)
        self.rsb_model = RsbModel(self)
        self.bkgd_model = BkgdModel(self)

        # Create the scan model for the calculation.
        self.nbar_model = NbarModel(self,
                                    rsb_model=self.rsb_model,
                                    bsb_model=self.bsb_model,
                                    bkgd_model=self.bkgd_model)

        # Register the measurement models with the scan framework.
        self.register_model(self.bsb_model, measurement='bsb')
        self.register_model(self.rsb_model, measurement='rsb')
        self.register_model(self.bkgd_model, measurement='bkgd')

        # Register the calculation model with the scan framework.
        self.register_model(self.nbar_model, calculation='nbar', fit='nbar')

    def prepare_scan(self):
        # Load data from the datasets when we are only fitting.
        # This is needed for the nbar calculation.
        if self.fit_only:
            self.nbar_model.load()

        # Lab specific:
        # Load lab specific datasets.
        self.raman.load_transitions()
        self.microwaves.load_transitions()

        # Lab specific:
        # Initialize Raman sideband cooling pulses.
        if self.mode == 'mode_1':
            self.raman.setup_cooling(measure_mode=1)
        if self.mode == 'mode_2':
            self.raman.setup_cooling(measure_mode=2)

    # (Optional)
    def before_pass(self, pass_index):
        # Let user know what pass they're currently on.
        print("Starting Pass %i" % (pass_index+1))

    @kernel
    def measure(self, time):
        self.core.break_realtime()        
        
        # Add additional slack for sideband cooling
        if not self.measurement == 'bkgd':
            self.cooling.contain()
            delay(3*ms)

        self.cooling.doppler()

        # Improve state prep by reducing population in |3,-2> state
        self.raman.repump()

        if not self.measurement == 'bkgd':
            self.raman.sideband_cool()

            # allow ion to heat
            delay(time)

        # BSB/RSB pulses
        if self.mode == 'mode_1':
            if self.measurement == 'bsb':
                self.raman.set_frequency(self.raman.m1_bsb_frequency)
                self.raman.pulse(self.raman_readout_time)
            if self.measurement == 'rsb':
                self.raman.set_frequency(self.raman.m1_rsb_frequency)
                self.raman.pulse(self.raman_readout_time)
            if self.measurement == 'bkgd':
                self.raman.set_frequency(self.raman.m1_bsb_frequency)
                self.raman.ttl_rr.pulse(self.raman_readout_time)
                delay(2*us)
                self.raman.ttl_br.pulse(self.raman_readout_time)
        elif self.mode == 'mode_2':
            if self.measurement == 'bsb':
                self.raman.set_frequency(self.raman.m2_bsb_frequency)
                self.raman.pulse(self.raman_readout_time)
            if self.measurement == 'rsb':
                self.raman.set_frequency(self.raman.m2_rsb_frequency)
                self.raman.pulse(self.raman_readout_time)
            if self.measurement == 'bkgd':
                self.raman.set_frequency(self.raman.m2_bsb_frequency)
                self.raman.ttl_rr.pulse(self.raman_readout_time)
                delay(2*us)
                self.raman.ttl_br.pulse(self.raman_readout_time)

        # State Detection.
        self.microwaves.transition_1()
        counts = self.detection.detect()

        # Return PMT counts.
        return counts

    # (Optional)
    def analyze(self):
        """Demonstrates how to perform manual calculates.

        This simply recalculates nbar at each scan point and displays it for quick feedback to the user
        on what nbar values have been calculated.
        """

        # Load the mean values for the RSB, BSB, and BKG measurements that were calculated by the
        # scan framework.
        self.rsb_model.load()
        self.bsb_model.load()
        self.bkgd_model.load()

        # Load the scan points. (i.e. the list of wait times)
        x = self.rsb_model.stat_model.get('x')

        # Calculate nbar at each scan point.
        nbar = []
        for i in range(len(x)):
            value, error = self.nbar_model.calculate(i)
            nbar.append(value)

        # Print the value of nbar at each scan point.
        print("----- Heating Rate Calculation -----")
        print('nbar:')
        print(nbar)
