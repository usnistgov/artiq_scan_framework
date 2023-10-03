from artiq.experiment import *


class Iter(HasEnvironment):

    def build(self):
        pass

    def offset_points(self, x_offset):
        pass

    @portable
    def done(self, ret):
        pass

    @portable
    def step(self):
        pass

    @portable
    def last_itr(self):
        return self.i == self.niter - 1



