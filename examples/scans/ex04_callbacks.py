# Example 3: Callbacks
#
# How to set a device value at the start of each scan point using the
# `set_scan_point()` callback.
from artiq.experiment import *
from scan_framework import *


class Example3Scan(Scan1D, EnvExperiment):

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
        self.setattr_device('dds0')

    def prepare(self):
        self.model = Example3Model(self)
        self.register_model(self.model, measurement=True, fit=True)

    def get_scan_points(self):
        return self.frequencies

    # 1. Create a `set_scan_point()` method.
    #    The set_scan_point() callback is called once at the start of each scan point,
    #    before your measure() method is repeated multiple times.
    @kernel
    def set_scan_point(self, i_point, frequency):
        # `i_point` is set to the index of the current scan point.
        # `frequency` is set to the value of the current scan point.

        print("callback: set_scan_point")
        print(i_point)
        print(frequency)

        # Note: `set_scan_point()` is typically used to set a device to the value of the current
        #        scan point.
        self.dds0.set(frequency)

    @kernel
    def measure(self, frequency):
        # Note: The scan point index is always available at self._i_point when it is not passed in as
        #       an argument.
        print(self._i_point)
        return int(frequency ** 2.0)


class Example3Model(ScanModel):
    namespace = "example_3"
    fit_function = fitting.Power
