from artiq_scan_framework import *

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

    @portable
    def measure_dark_rate(self):
        return 1.0

    @portable
    def ion_present(self, repeats, threshold):
        """Returns true if an ion is present in the trap."""
        return True

    @portable
    def measure_bright_rate(self, repeats=100):
        return 20.0

