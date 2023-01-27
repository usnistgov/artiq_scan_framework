from artiq.experiment import *
import numpy as np
from ..iter import Iter


class IterCont(Iter):

    def build(self, looper):
        #looper.scan.print('IterCont.build(looper={})'.format(looper.__class__.__name__), 2)
        self.looper = looper
        self.points = np.array([i for i in range(self.looper.scan.continuous_points)], dtype=np.float64)  # 1D array of scan points (these are saved to the stats.points dataset)
        # indexes
        self.i = np.int32(0)  # unbounded index
        self.i_point = np.int32(0)  # unbounded index MOD self.nds -- index into stats datasets where values at the current iteration are stored
        self.i_plot = np.int32(0)  # unbounded index MOD self.nplot -- index into plot datasets where values at the current iteration are stored
        #self.looper.scan.print('IterCont.build()', -2)

    def __str__(self):
        return "".join([
            '{}: '.format(self.__class__.__name__),
            ', i: {}'.format(self.i),
            ', i_point: {}'.format(self.i_point),
            ', i_plot: {}'.format(self.i_plot)
        ])

    def offset_points(self, x_offset):
        if x_offset is not None:
            self.looper.scan.continuous_measure_point += x_offset

    @portable
    def done(self, ret):
        ret[0] = self.looper.scan.continuous_measure_point  # measure_point
        return False  # loop forever

    @portable
    def step(self):
        self.i += 1
        self.update_indexes()

    @portable
    def update_indexes(self):
        self.i_point = self.i %  self.looper.scan.continuous_points
        self.i_plot = self.i % self.looper.scan.continuous_plot

    @portable
    def at_wrap(self):
        """Returns True when the next iteration will "wrap around".  After a "wrap around", old dataset values are overwritten,
        therefore this method is used as a signal for when data should be logged to the hdf5 file so it isn't lost."""
        return self.i_point == self.looper.scan.continuous_points - 1

    @portable
    def rewind(self, num_points):
        """Rewind the cursor from the current continuous (i.e. unbounded) index by the specified number of points.
        The cursor cannot be rewound past the first point of the first pass.

          :param num_points: The current cursor will be moved to this number of scan points before its current value.
        """
        if num_points > 0:
            self.i -= num_points
            if self.i < 0:
                self.i = 0
            # Make sure to update self.i_plot and self.i_point!!! -- loop.py uses self.i_point not self.i!!!
            self.update_indexes()


