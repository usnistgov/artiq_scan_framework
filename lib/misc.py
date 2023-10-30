import numpy as np


def kron3_flat(a, b, c):
    return np.kron(np.kron(a, b.T), c.T)


def kron2_flat(a, b):
    return np.kron(a, b.T)