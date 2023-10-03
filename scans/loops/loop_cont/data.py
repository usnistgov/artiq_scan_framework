from artiq.experiment import *
import numpy as np


class Data:

    def __init__(self, shape, dtype):
        self.val = dtype(0)
        self.val_zero = dtype(0)
        self.data = np.zeros(shape, dtype=dtype)

    @portable
    def reset(self):
        self.val = self.val_zero

    @portable
    def store(self, i, val):
        self.data[i[0]][i[1]] = val
        self.val += val

    @portable
    def mean(self, n):
        return self.val / n