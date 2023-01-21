from artiq.experiment import *
import numpy as np
from artiq_scan_framework.beta.iter import Iter


class Iter1D(Iter):
    kernel_invariants = {'npoints', 'niter'}

    def build(self, looper):
        self.looper = looper
        # indexes
        self.i = np.int32(0)
        self.i_point = np.int32(0)
        self.i_pass = np.int32(0)

    def __str__(self):
        return "".join([
            '{}: '.format(self.__class__.__name__),
            ', i: {}'.format(self.i),
            ', i_point: {}'.format(self.i_point),
            ', i_pass: {}'.format(self.i_pass)
        ])

    def load_points(self, points):
        """called by Loop1D::init to assign the scan points defined in the user's scan class to the iterator"""
        self.points = np.array([p for p in points], dtype=np.float64)
        self.npoints = np.int32(len(self.points))
        self.niter = self.npoints * self.looper.scan.npasses
        self.shape = self.npoints
        self.plot_shape = self.npoints

    def offset_points(self, x_offset):
        self.points += x_offset

    # @portable
    # def reset(self):
    #     self.i = 0
    #     self.i_point = 0
    #     self.i_pass = 0

    @portable
    def done(self, ret):
        """Returns True when all scan points have been iterated over"""
        done = self.i == self.niter
        if self.i_point < self.npoints:
            ret[0] = self.points[self.i_point]  # measure_point
        return done

    @portable
    def step(self):
        self.i += 1
        self.update_indexes()

    @portable
    def update_indexes(self):
        self.i_pass = int(self.i / self.npoints)
        self.i_point = self.i % self.npoints

    @portable
    def rewind(self, num_points):
        """Rewind the cursor from the current pass and point indices by the specified number of points.  The cursor can
                  be rewound into a previous pass.  The cursor cannot be rewound past the first point of the first pass.
                  :param num_points: The current cursor will be moved to this number of scan points before its current value.
        """
        if num_points > 0:
            self.i -= num_points
            if self.i < 0:
                self.i = 0
            # Make sure to update self.i_pass and self.i_point!!! -- loop.py uses self.i_point not self.i!!!
            self.update_indexes()
