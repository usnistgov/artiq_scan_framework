from artiq.experiment import *


class Loop(HasEnvironment):

    def terminate(self):
        self.scan.print('Loop::terminate()', 2)
        self.scan.print('Loop::terminate()', -2)
