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

    def poffset(self):
        return self.i_pass * self.nrepeats

    @portable
    def last_itr(self):
        return self.i == self.niter - 1

    @portable
    def rewind(self, num_points):
        if num_points > 0:
            self.i -= 1
            if self.i < 0:
                self.i = 0


