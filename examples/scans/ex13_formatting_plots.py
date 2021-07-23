# Example 13: Formatting plots
#
# How to format the plot axes and title
from artiq.experiment import *
from scan_framework import *


class Example13Scan(Scan1D, FreqScan, EnvExperiment):
    run_on_core = False

    def build(self):
        super().build()
        self.scan_arguments(
            # Turn off fit_options GUI argument
            fit_options=False
        )

    def prepare(self):
        self.register_model(Example13Model(self), measurement=True)

    #@kernel
    def measure(self, frequency):
        # Return some dummy data to be plotted.
        return int((frequency/(1*MHz))**2)


class Example13Model(ScanModel):
    namespace = "example_13"

    # 1. All formatting of plots is done through attributes of the registered model.
    plot_title = 'Example 13'
    x_label = 'Frequency'
    x_scale = MHz
    x_units = 'MHz'
    y_label = 'PMT Counts'
    y_scale = 10
    y_units = 'x10'

    # 2. Formatting colors, point symbols, axes sizes, etc. of the plot can be accomplished by creating your own applet.
    #    See `scan_framework/applets/plot_xy.py` as a template that easily be copied and modified.