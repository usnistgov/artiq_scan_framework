from .scan import *
from .loops.loop_1d.loop import *


class Scan1D(BetaScan):

    def build(self, **kwargs):
        self.print('beta.Scan1D.build()', 2)
        self.scan_arguments(Loop1D, init_only=True)
        self.looper = Loop1D(self, scan=self)
        super().build(**kwargs)
        self.print('beta.Scan1D.build()', -2)

    @property
    def npasses(self):
        return self.looper.itr.npasses

    @npasses.setter
    def npasses(self, npasses):
        self.looper.itr.npasses = npasses

    @property
    def nrepeats(self):
        return self.looper.nrepeats

    @nrepeats.setter
    def nrepeats(self, nrepeats):
        self.looper.nrepeats = nrepeats
