from artiq.experiment import *


class Loop(HasEnvironment):

    def terminate(self):
        pass
        #self.scan.print('Loop::terminate()', 2)
        #self.scan.print('Loop::terminate()', -2)
