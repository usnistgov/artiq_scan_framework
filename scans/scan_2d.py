from .scan import *
from .loops.loop_2d.loop import *


class Scan2D(Scan):
    """Extension of the :class:`~artiq_scan_framework.scans.scan.Scan` class for 2D scans.  All 2D scans should inherit from
        this class."""
    #hold_plot = False

    def build(self, **kwargs):
        # legacy: backwards compatiblity for old method of inheriting from Scan1D.
        #         the new, preferred method is to add the calls below in the user's scan class.  e.g., in your build
        #         method call:
        #         self.scan_arguments(Loop1D, init_only=True)  # must be called first
        #         self.looper = Loop1D(self, scan=self)        # must be called second
        #self.print('Scan2D.build()', 2)
        self.scan_arguments(Loop2D, init_only=True)
        self.looper = Loop2D(self, scan=self)
        super().build(**kwargs)
        #self.print('Scan2D.build()', -2)

