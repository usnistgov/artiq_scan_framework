from scan_framework import *


class ShimModel(Model):
    """Models ion interaction with shim voltages."""
    namespace = "shims.%type"  #: Dataset namespace

    def build_datasets(self):
        """Create missing shim datasets."""
        self.create('x.defaults.voltage', 0)
        self.create('y.defaults.voltage', 0)
        self.create('z.defaults.voltage', 0)


class ShimScanModel(ShimModel, ScanModel):
    x_units = 'V'
    fit_function = fitting.Gauss
    main_fit = 'voltage'
    fit_map = {
        'x0': 'voltage'
    }

    @property
    def simulation_args(self):
        if self.type == 'x':
            return {
                'A': 10,
                'sigma': 2,
                'x0': 0.5,
                'y0': 0
            }
        if self.type == 'y':
            return {
                'A': 10,
                'sigma': 2,
                'x0': -0.5,
                'y0': 0
            }
        if self.type == 'z':
            return {
                'A': 10,
                'sigma': 2,
                'x0': 0,
                'y0': 0
            }

    # plots
    @property
    def plot_title(self):
        return "{0} Shim".format(self.type.title())
