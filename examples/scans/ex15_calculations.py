from artiq_scan_framework.scans import *
from artiq_scan_framework.models import *
import numpy as np


class CalculationScan(Scan1D, EnvExperiment):

    def build(self):
        super().build()
        self.scan_arguments()

    def get_scan_points(self):
        return np.array([1, 2, 3, 4, 5], dtype=np.float)

    def prepare(self):
        measurement_model = MeasurementScanModel(self)
        calculation_model = CalculationModel(self, measurement_model)
        self.register_model(measurement_model, measurement='my_measurement')
        self.register_model(calculation_model, calculation='my_calculation', mutate_plot=True)

    @kernel
    def measure(self, point):
        return np.int32(point)


class MeasurementScanModel(ScanModel):
    # datasets
    namespace = 'examples.calculations.measurement_1'  #: Dataset namespace
    mirror = False
    persist = True
    broadcast = True


class CalculationModel(TimeModel):

    # datasets
    namespace = 'examples.calculations.calculation_1'  #: Dataset namespace
    mirror = True
    persist = True
    broadcast = True

    def build(self, measurement_1_model, **kwargs):
        self.measurement_1_model = measurement_1_model
        super().build(**kwargs)

    def load_datasets(self):
        super().load_datasets()
        self.measurement_1_model.load_datasets()

    def calculate(self, i_point, calculation):
        measurement_1_mean = self.measurement_1_model.stat_model.means[i_point]
        measurement_1_error = self.measurement_1_model.stat_model.errors[i_point]
        calced_value = 10*measurement_1_mean
        calced_error = 10*measurement_1_error
        return calced_value, calced_error