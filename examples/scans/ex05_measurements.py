# Example 5: Performing multiple measurements
#
# How to perform multiple measurements at each scan point.
#
# NOTE: Also create in the dashboard the applet for this experiment in scan_framework/examples/scans/ex05_applet.txt
from artiq.experiment import *
from scan_framework import *


class Example5Scan(Scan1D, EnvExperiment):

    def build(self):
        super().build()
        self.scan_arguments()
        self.setattr_argument('frequencies', Scannable(
            default=RangeScan(
                start=0,
                stop=7,
                npoints=8
            ),
            unit='Hz',
            scale=1
        ))

    def prepare(self):
        # 1. Register a model to calculate the means and SEMs of each measurement
        self.register_model(M1Model(self), measurement='m1', fit=True)
        self.register_model(M2Model(self), measurement='m2', fit=True)

        # NOTE: self.register_model automatically sets self.measurements
        #       If you are not using models, then you must manually set self.measurements
        #       e.g., for this example, self.measurements = ['m1', 'm2']

    def get_scan_points(self):
        return self.frequencies

    # Note: At each scan point the measure() method is repeated `self.nrepeats` times
    #       for each measurement in `self.measurements`.  Thus, `measure()` is repeated
    #       `len(self.measurements)*self.nrepeats` times at each scan point.
    @kernel
    def measure(self, frequency):
        # 3. Perform each measurement and return its value.
        #    `self.measurement` is always set to the current measurement name.
        if self.measurement == 'm1':
            return int(frequency ** 2)
        elif self.measurement == 'm2':
            return int(frequency ** 0.5)
        else:
            return 0
        return 0  # Prevents compilation error in ARTIQ V3


class M1Model(ScanModel):
    namespace = "example_5.m1"
    fit_function = curvefits.Power

    # Note: All datasets will be broadcast, saved, and persisted in this example
    broadcast = True
    persist = True
    save = True


class M2Model(ScanModel):
    namespace = "example_5.m2"
    fit_function = curvefits.Power

    broadcast = True
    persist = True
    save = True
