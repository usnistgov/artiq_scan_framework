from artiq.experiment import *
import numpy as np
from artiq_scan_framework.beta.iter import Iter


class IterCont(Iter):

    def build(self, meas_point, nds, nplot):
        self.meas_point = meas_point
        self.nds = nds  # number of points in stat datasets
        self.nplot = nplot  # number of points in plot datasets

        # indexes
        self.i = np.int32(0)  # unbounded index
        self.i_ds = np.int32(0)  # unbounded index MOD self.nds
        self.i_plot = np.int32(0) # unbounded index MOD self.nplot

    def offset_points(self, x_offset):
        if x_offset is not None:
            self.meas_point += x_offset

    @portable
    def done(self, ret):
        ret[0] = self.meas_point  # measure_point
        # loop forever
        return False

    @portable
    def last_point(self):
        # never at last point since we run forever
        return False

    @portable
    def last_pass(self):
        # never at last pass since we run forever
        return False

    @portable
    def at_wrap(self):
        return self.i_ds == self.nds - 1

    @portable
    def step(self):
        self.i += 1
        self.i_ds += 1
        self.i_plot += 1
        if self.i_ds == self.nds:
            self.i_ds = 0
        if self.i_plot == self.nplot:
            self.i_plot = 0

    @portable
    def rewind(self, num_points):
        """Rewind the cursor from the current pass and point indices by the specified number of points.  The cursor can
          be rewound into a previous pass.  The cursor cannot be rewound past the first point of the first pass.

          :param num_points: The current cursor will be moved to this number of scan points before its current value.
        """
        if num_points > 0:
            self.i -= num_points
            self.i_ds -= num_points
            self.i_plot -= num_points
            if self.i < 0:
                self.i = 0
            if self.i_ds < 0:
                self.i_ds = self.nds - 1
            if self.i_plot < 0:
                self.i_plot = 0


