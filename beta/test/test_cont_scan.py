import artiq_scan_framework.beta.scan as beta_scan
from artiq_scan_framework.models import *
from artiq_scan_framework.beta.loops.loop_cont import *



class TestContScan(beta_scan.BetaScan, EnvExperiment):

    def build(self):
        super().build()
        self.run_on_core = False
        self.print_level = 0
        self.debug = True
        self.scan_arguments()
        self.looper = LoopCont(self,
                               scan=self,
                               nrepeats=self.nrepeats,
                               continuous_points=self.continuous_points,
                               continuous_plot=self.continuous_plot,
                               continuous_measure_point=self.continuous_measure_point,
                               continuous_save=self.continuous_save
                               )

    def prepare(self):
        self.model = ScanModel(self, namespace='beta')
        self.register_model(self.model, measurement=True, fit=True, bind=True)

    def get_scan_points(self):
        return [i for i in range(10)]

    @kernel
    def initialize_devices(self):
        self.core.reset()

    @portable
    def measure(self, point):
        return 0