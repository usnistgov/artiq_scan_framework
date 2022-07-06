from artiq.experiment import HasEnvironment
from artiq.language import *
from ..models.model import *


# TODO: needs commenting
class LoadingInterface(HasEnvironment):

    def build(self):
        pass

    def can_load(self):
        return True

    def schedule_load_ion(self, due_date):
        pass

    def wait(self):
        pass

    @kernel
    def measure_dark_rate(self):
        pass

    @kernel
    def ion_present(self, repeats, threshold):
        """Returns true if an ion is present in the trap."""
        return True
