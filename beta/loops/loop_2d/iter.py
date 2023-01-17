from artiq.experiment import *
import numpy as np
from artiq_scan_framework.beta.iter import Iter


class Iter2D(Iter):

    def build(self, npasses, nrepeats):
        self.npasses = npasses
        self.nrepeats = nrepeats

        # indexes
        self.reset()

    @portable
    def reset(self):
        self.i = np.int32(0)
        self.i0 = np.int32(0)
        self.i1 = np.int32(0)
        self.i_point = np.array([0, 0], dtype=np.int64)
        self.i_pass = np.int32(0)

    def set_points(self, points):
        # this turn's ARTIQ scan arguments into lists
        points = [p for p in points[0]], [p for p in points[1]]
        self.points0, self.points1 = points
        self.points0 = np.array(self.points0, dtype=np.float64)
        self.points1 = np.array(self.points1, dtype=np.float64)

        # initialize shapes (these are the authority on data structure sizes)...
        self.shape = np.array([len(self.points0), len(self.points1)], dtype=np.int32)
        # shape of the current scan plot
        self.plot_shape = self.shape
        self.niter = self.npasses * self.shape[0] * self.shape[1]
        self.npoints = np.int32(self.shape[0] * self.shape[1])

    def points(self):
        return np.array([
            [[x1, x2] for x2 in self.points1] for x1 in self.points0
        ], dtype=np.float64)

    def offset_points(self, offset):
        self.points1 += offset

    @portable
    def done(self, ret):
        done = self.i == self.niter
        if not done:
            ret[0] = self.points0[self.i0]  # dim0 measure_point
            ret[1] = self.points1[self.i1]  # dim1 measure_point
        return done

    @portable
    def step(self):

        self.i += 1
        np = self.shape[0] * self.shape[1]
        self.i_pass = int(self.i / np)
        self.i0 = int((self.i % np) / self.shape[1])
        self.i1 = (self.i % np) % self.shape[1]
        self.i_point[0] = self.i0
        self.i_point[1] = self.i1




