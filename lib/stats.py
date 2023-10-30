import numpy as np


def fock_states_nd(nstarts, nends):
    return np.array(list(map(np.arange, np.array(nstarts), np.array(nends) + 1)))


def fock_states(nstart, nend):
    return np.arange(nstart, nend+1)


def thermal_dist(nbar, ns):
    """Returns occupation probability of the specified Fock states assuming a thermal distribution of states.
    :param nbar : The mean Fock state of the thermal distribution
    :param ns : Fock states to consider
    """
    return np.exp(ns * np.log(nbar) - (ns + 1) * np.log(nbar + 1))


def thermal_dist_nd(nbars, ns):
    """Returns a thermal distribution for each of the specified modes.
    :param nbars : List containing the mean Fock state of each motional mode.
                nbars[0] = mean state for first mode
                nbars[1] = mean state for second mode,
                etc
    :param ns : List containing Fock states to consider for each motional mode.
                ns[0] = list of Fock states for first mode
                ns[1] = list of Fock states for second mode
                etc.
    :return : 2D array containing the probability distribution over fock state for each mode
            dists[0] = probability distribution for the first mode
            dists[1] = probability distribution for the second mode
            etc.


    """
    return np.array(list(map(thermal_dist, nbars, ns)))