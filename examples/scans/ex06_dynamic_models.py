# Example 6: Dynamic models
#
# Dynamically controlling how a model handles data.
#   In this example, namespace tokens are used to define where data is stored
#   and model attributes are used to determine which fit to perform.
#
# NOTE: Also create in the dashboard the applet for this experiment in scan_framework/examples/scans/ex06_applet.txt
from artiq.experiment import *
from scan_framework import *


class Example6Scan(Scan1D, EnvExperiment):

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
        # 1. Assign an attribute to the model
        m1_model = Example6Model(self,
            # Note: All arguments of the constructor are assigned to attributes of the model.
            mmnt_name='m1'
        )
        print('EXAMPLE 6: self.m1_model.mmnt_name = {}'.format(m1_model.mmnt_name))

        self.register_model(m1_model, measurement='m1', fit=True)
        self.register_model(Example6Model(self, mmnt_name='m2'), measurement='m2', fit=True)

    def get_scan_points(self):
        return self.frequencies

    @kernel
    def measure(self, frequency):
        if self.measurement == 'm1':
            return int(frequency ** 2)
        elif self.measurement == 'm2':
            return int(frequency ** .5)
        else:
            return 0
        return 0  # Prevents compilation error in ARTIQ V3


# Note: A single model can be used for both measurements
class Example6Model(ScanModel):
    # 2a. Reference the attribute using namespace tokens.
    #     `%mmnt_name` is a namespace token and will be replaced by the model's `mmnt_name` attribute.
    namespace = "example_6.%mmnt_name"
    broadcast = True
    persist = True
    save = True
    fit_function = curvefits.Power

    # 2b. Use @property to dynamically determine an attribute
    @property
    def guess(self):
        # Fit `sine` to the `m1` measurement means
        if self.mmnt_name == 'm1':
            return {
                'A': 1,
                'alpha': 2,
                'y0': 0
            }
        # Fit `cos` to the `m2` measurement means
        if self.mmnt_name == 'm2':
            return {
                'A': 1,
                'alpha': .5,
                'y0': 0
            }

    # Set the scale of each fit parameter by setting `man_scale` (see analysis/curvefits.py)
    man_scale = {
        'A': 1,
        'alpha': 1,
        'y0': 1
    }

    # Bound the allowed fit parameters by setting `man_bounds` (see analysis/curvefits.py)
    @property
    def man_bounds(self):
        if self.mmnt_name == 'm1':
            return {
                'A': [.9, 1.1],
                'alpha': [1.5, 2.5]
            }
        if self.mmnt_name == 'm2':
            return {
                'A': [.9, 1.1],
                'alpha': [0, 1.0]
            }