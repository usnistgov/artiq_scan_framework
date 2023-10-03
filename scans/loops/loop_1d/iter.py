from artiq.experiment import *
import numpy as np
from ..iter import Iter


class Iter1D(Iter):
    """
    core variables:
        1. i
        2. i_point
        3. i_pass
        4. niter
        5. npoints
        6. points

    """

    #kernel_invariants = {'npoints', 'niter'}

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

    def reset(self):
        self.i = np.int32(0)
        self.i_point = np.int32(0)
        self.i_pass = np.int32(0)

    def load_points(self, points):
        """called by Loop1D::init to assign the scan points defined in the user's scan class to the iterator"""
        self.points = np.array([p for p in points], dtype=np.float64)
        self.npoints = np.int32(len(self.points))
        self.niter = np.int32(self.npoints * self.looper.scan.npasses)
        self.shape = self.npoints
        self.plot_shape = self.npoints
    @kernel
    def sync_with_host(self):
        """Sets all variables on the host device to their current values on the host.

        This is used when scans are being run multiple times on the core device (see the CoreScanRunner class in scans.util.py).
        In those cases, Scan::_initialize() is called on the core device after a scan completes on the core device.
        This initializes datasets and variables on the host device correctly for the scan to be run again.  However,
        variables on the core device will be equal to the values from the previous run of the scan.  Variables on the
        core, therefore, need to be set to their corresponding values on the host after Scan::_initialize() is called.
        That is the purpose of this method.
        """

        # first make an RPC call to get the current variable values from the host
        ints = self.get_host_ints()
        self.i = ints[0]
        self.i_point = ints[1]
        self.i_pass = ints[2]
        self.niter = ints[3]
        self.npoints = ints[4]
        points = self.get_host_points()
        # work around to avoid ARTIQ compiler errors.  RPC returns a list, but core variable is a numpy array.
        for i in range(self.npoints):
            self.points[i] = points[i]

    # RPC
    def get_host_ints(self) -> TList(TInt32):
        indexes = [self.i, self.i_point, self.i_pass, self.niter, self.npoints]
        return indexes

    # RPC
    def get_host_points(self) -> TList(TFloat):
        # work around to avoid ARITQ compiler errors.  Simply returning self.points throws an error.
        points = [p for p in self.points]
        return points

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
    def get_i_rewound(self, num_points):
        i_rewond = self.i
        if num_points > 0:
            i_rewond -= num_points
            if i_rewond < 0:
                i_rewond = 0
        return i_rewond

    @portable
    def rewind(self, num_points):
        """Rewind the cursor from the current pass and point indices by the specified number of points.  The cursor can
                  be rewound into a previous pass.  The cursor cannot be rewound past the first point of the first pass.
                  :param num_points: The current cursor will be moved to this number of scan points before its current value.
        """
        if num_points > 0:
            self.i = self.get_i_rewound(num_points)
            # Make sure to update self.i_pass and self.i_point!!! -- loop.py uses self.i_point not self.i!!!
            self.update_indexes()
