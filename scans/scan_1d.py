from .scan import *
from .loops.loop_1d.loop import *


class Scan1D(Scan):
    """Extension of the :class:`~artiq_scan_framework.scans.scan.Scan` class for 1D scans.  All 1D scans should inherit from
    this class."""

    def build(self, **kwargs):
        # legacy: backwards compatiblity for old method of inheriting from Scan1D.
        #         the new, preferred method is to add the calls below in the user's scan class.  e.g., in your build
        #         method call:
        #         self.scan_arguments(Loop1D, init_only=True)  # must be called first
        #         self.looper = Loop1D(self, scan=self)        # must be called second
        #self.print('Scan1D.build()', 2)
        self.scan_arguments(Loop1D, init_only=True)
        self.looper = Loop1D(self, scan=self, dtype=self.dtype)
        super().build(**kwargs)
        #self.print('Scan1D.build()', -2)
