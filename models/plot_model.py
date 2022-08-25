from .model import *

## For future use in scan_model.py
class Plot(Model):

    def init_datasets(self, shape=None, title="", x_label="", x_scale=1, x_units="", y_label="", y_scale=1, y_units="", fit_legend="", data_legend="", subtitle=""):
        # data
        self.init('x', shape, varname='x', init_local=True)
        self.init('y', shape, varname='y', init_local=True)
        self.init('y2', shape, varname='y2', init_local=True)
        self.init('fitline', shape, varname='fitline', init_local=True)
        self.init('fitline_fine', shape, varname='fitline_fine', init_local=True)
        self.init('x_fine', shape, varname='x_fine', init_local=True)
        self.init('error', shape, init_local=False)

        # labels, etc.
        self.set('plot_title', title)
        self.set('y_label', y_label)
        self.set('x_label', x_label)
        self.set('x_scale', x_scale)
        self.set('y_scale', y_scale)
        self.set('x_units', x_units)
        self.set('y_units', y_units)
        self.set('fit_legend', fit_legend)
        self.set('data_legend', data_legend)
        self.set('subtitle', subtitle)
        self.set('fit_string', '')

    def mutate_datasets(self, i, x, y, error=None, which='both'):
        super().mutate('x', i, x, which=which, update_local=False)
        super().mutate('y', i, y, which=which, update_local=False)
        if error != None:
            super().mutate('error', i, error, which=which, update_local=False)