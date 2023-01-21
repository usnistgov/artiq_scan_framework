from artiq_scan_framework.beta.loops.loop_1d import *
from artiq_scan_framework.beta.loops.loop_cont import *
from collections import OrderedDict


class Loop1DCont:

    @staticmethod
    def looper(scan):
        """Creates and returns the looper object for the scan.  Use this method in the scan build() method in place of creating
        a looper object directly.

        For example:
            self.looper = Loop1DCont.looper(scan=self)
            will set self.looper to either LoopCont, when continuous_scan is checked in the dashboard,
            or to Loop1D, when continuous_scan is not checked in the dashboard

        """
        if scan.continuous_scan:
            return LoopCont(scan, scan=scan)
        else:
            return Loop1D(scan, scan=scan)

    @staticmethod
    def argdef():
        argdef = OrderedDict()
        # show arguments needed for both Loop1D loops and LoopCont loops, since we can run either type of loop
        argdef['continuous_scan'] = {
            'processor': BooleanValue,
            'processor_args': {'default': False},
            'group': 'Continuous Scan',
            'tooltip': 'make this a continuous scan.'
        }
        argdef.update(LoopCont.argdef())
        argdef.update(Loop1D.argdef())
        return argdef

