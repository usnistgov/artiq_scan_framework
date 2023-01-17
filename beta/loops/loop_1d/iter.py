from artiq.experiment import *
import numpy as np
from artiq_scan_framework.beta.iter import Iter


class Iter1D(Iter):

    def build(self, npasses, nrepeats):
        self.npasses = npasses
        self.nrepeats = nrepeats

        # indexes
        self.i = np.int32(0)
        self.i_point = np.int32(0)
        self.i_pass = np.int32(0)

    def set_points(self, points):
        self.points = np.array([p for p in points], dtype=np.float64)
        self.npoints = np.int32(len(points))
        self.niter = self.npoints * self.npasses
        self.shape = self.npoints
        self.plot_shape = self.npoints

    def offset_points(self, x_offset):
        self.points += x_offset

    @portable
    def reset(self):
        self.i = 0
        self.i_point = 0
        self.i_pass = 0

    @portable
    def done(self, ret):
        done = self.i == self.niter
        if not done:
            ret[0] = self.points[self.i_point]  # measure_point
        return done

    @portable
    def step(self):
        self.i += 1
        self.i_pass = int(self.i / self.npoints)
        self.i_point = self.i % self.npoints