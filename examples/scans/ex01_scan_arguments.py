# Example 1: Scan arguments
#
# How to create and use scan arguments.  The effect of scan loop arguments are printed to the Log window in the
# dashboard.
from artiq.experiment import *
from scan_framework import *


class Example1Scan(Scan1D, EnvExperiment):
    # We will run this example entirely on the host device.
    run_on_core = False

    # We instruct the framework to not perform fits by setting `enable_fitting = False`.
    # This also disables the `fit_options` GUI argument.
    enable_fitting = False

    def build(self):
        super().build()

        # 1. Scan arguments can be created manually instead of using self.scan_arguments() exclusively.
        #    This allows control over the placement of arguments.

        # Change the default number of passes to 2
        self.setattr_argument('npasses', NumberValue(default=2, ndecimals=0, step=1), group='Scan Settings')

        # 2. self.npasses will be set to its default argument value when no arguments have been submitted.
        #    Click "Recompute all arguments" and '2' will be printed
        print("self.npasses = {}".format(self.npasses))

        # 3a. By default, no GUI arguments are created for scan arguments that are set explicitly.
        # An `nrepeats` GUI argument will not be created because it is explicitly set here.
        self.nrepeats = 2

        # 3b. To force showing the GUI argument, set the 'show' argument to True
        #
        # uncomment to show the nrepeats argument
        #self.setattr_argument('nrepeats', NumberValue(default=1, ndecimals=0, step=1), group='Scan Settings', show=True)

        # 3c. To force never showing the GUI argument set the 'show' argument to False
        # Binning is not applicible to this scan, so we hide this argument.
        #
        # uncomment to hide the nbins argument
        #self.setattr_argument('nbins', show=False)

        print("self.nrepeats = {}".format(self.nrepeats))

        # 4. Any arguments not previously defined will be created by self.scan_arguments() when it is called.
        # In this case, the `nbins` arguments will be created by self.scan_arguments().
        # The `fit_options` GUI argument is not crated because `self.enable_fitting == False`
        self.scan_arguments()

    def get_scan_points(self):
        return [i for i in range(3)]

    # Note no @kernel, this scan runs entirely on the host device
    def measure(self, point):
        print('(i_pass, point) = ({}, {})'.format(self._i_pass, point))
        return int(point)