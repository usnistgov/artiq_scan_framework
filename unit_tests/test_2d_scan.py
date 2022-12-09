from artiq_scan_framework.scans import *
from artiq_scan_framework.models import *
from artiq_scan_framework.analysis import fit_functions

class Test2DScan(Scan2D, EnvExperiment):

    def build(self):
        super().build()

        # arguments
        self.scan_arguments()

        # model (dimension 1)
        self.model1 = ScanModel(self,
                                namespace="model1",
                                fit_function=fit_functions.Line,
                                fit_use_yerr=False)

        self.register_model(self.model1,
                            dimension=1,
                            measurement=True,
                            fit=True,
                            validate=False,
                            set=True,
                            save=False)

        # model (dimension 0)
        self.model0 = ScanModel(self,
                                namespace="model0",
                                plot_title="Test 2D Scan",
                                x_label="Sub Scan Index",
                                y_label="",
                                fit_function=fit_functions.Line,
                                fit_use_yerr=False)
        self.register_model(self.model0,
                            dimension=0,
                            fit=True,
                            validate=True,
                            set=True,
                            save=False)

    def get_scan_points(self):
        return [
            [i for i in range(10)],
            [i for i in range(10)]
        ]

    @portable
    def measure(self, point):
        return int(point[0]*point[1])

    def calculate_dim0(self, dim1_model):
        param = dim1_model.fit.params.slope
        error = dim1_model.fit.errs.slope_err
        return param, error
