import numpy as np
from math import pi
from scipy.special import factorial
from scipy.special import eval_genlaguerre
import operator as op
from functools import reduce

def ncr(n, r):
    r = min(r, n-r)
    numer = reduce(op.mul, range(n, n-r, -1), 1)
    denom = reduce(op.mul, range(1, r+1), 1)
    return numer // denom  # or / in Python 2


def debeyew(nbar, lambd):
    """Calculate Debeye Waller factor"""
    return np.exp(-lambd**2 * (nbar + 1/2))


def pi_time(omega):
    return np.pi/(2*omega)


def carrier_omega(pi_time):
    return np.pi/(2*pi_time)


# References:
# [1] Experimental Issues in Coherent Quantum-State Manipulation of Trapped
#     Atomic Ions, Wineland Et al. 1998
def rabi(ng, nl, lambd, carrier_omega=1, use_debeyew=False, spect_lambd=None, spect_nbar=()):
    """ Returns the average Rabi frequency for a transition between motional states
    n1 and n2 of a single mode optionally accounting for the reduction in Rabi
    frequency due to the Debye-Waller factors introduced by the other spectator modes.

    The relative frequency is returned by default, and the absolute frequency is
    returned if the carrier Rabi frequency is given.

    Eqns 18 and 124 in reference [1]

    Assumptions:
    1.  Vibrational states of spectator modes are independent and follow a thermal
        distribution.  See [1] Eqn 123.

    Notes:
    1.  Return value is symmetric wrt exchange of n1 and n2
    :param ng
        Larger motional state
    :param nl
        Smaller motional state
    :param lambd
        Lamb-Dicke parameter of the mode being addressed
    :param spect_lambd (array of floats)
        Array containing the Lamb-Dicke parameter of each spectator modes.
    :param spect_nbar (array of floats)
        Array containing the expected motional state of each spectator mode.
    :param use_debeyew (default = True)
        Set to false to not include Debye Waller factors
    :param carrier_omega (default = 1)
        The carrier rabi frequency in radians/s.  Set to 1 or omit to get the relative Rabi frequency.
    """

    # if hasattr(ng, '__iter__'):
    #     fact = np.full(ng.shape, 1)
    #     for i in range(len(ng)):
    #         _fact = 1
    #         for n in range(ng[i], nl[i], -1):
    #             _fact *= n
    #         fact[i] = _fact
    # else:
    #     fact = 1
    #     for n in range(int(ng), int(nl), -1):
    #         fact *= n
    # omega = abs(exp(-lambd ** 2 / 2) * carrier_omega * (1/fact) ** 0.5 * lambd ** (ng - nl)
    #             * genlag(nl, ng - nl, lambd ** 2))

    glag = 0
    for m in range(nl):
        glag += (-1)**m * ncr(nl, ng - nl) * (lambd**2)**m / factorial(m)
    omega = abs(exp(-lambd**2/2)*carrier_omega * (factorial(nl) / factorial(ng))**0.5 * lambd**(ng - nl)
                * glag
                # * genlag(nl, ng - nl, lambd**2)
    )


    if use_debeyew:
        for lambd, nbar in zip(spect_lambd, spect_nbar):
            omega *= debeyew(nbar, lambd)
    return omega


def rabi_rate_fast(omega, eta, n, alpha):
    """Returns the Rabi rate for the specified mode, Fock state, and transition.
    :param omega : Carrier rabi rate.
    :param eta : Lamb dickie parameter of the mode.
    :param n : The starting Fock state of the mode.
    :param alpha: Specifies the type of transition.
        alpha=0 for a carrier transition (n -> n)
        alpha=-1 for a first RSB transition (n -> n-1)
        alpha=1 for a first BSB transition (n -> n+1)
    """
    omega_nm = omega * np.exp(-eta ** 2 / 2)
    # 1st RSB
    if alpha == -1:
        omega_nm *= (1 / n) ** .5 * eta * eval_genlaguerre(n - 1, 1, eta ** 2)
    # Carrier
    elif alpha == 0:
        omega_nm *= eval_genlaguerre(n, 0, eta ** 2)
    # 1st BSB
    elif alpha == 1:
        omega_nm *= (1 / (n + 1)) ** .5 * eta * eval_genlaguerre(n, 1, eta ** 2)
    else:
        raise Exception('Unknown alpha')
    return np.abs(omega_nm)


def rabi_rate_fast_nd(omega, etas, ns, alphas):
    """Returns the Rabi rates for multiple modes in their specified Fock state and for the specified transitions.
    :param omega : Carrier rabi rate (float)
    :param etas : List of lamb dickie parameters for each mode.
    :param ns : List of initial Fock states for each mode.
    :param alphas : List containing the transition for each mode.  0 for a carrier, -1 for the first RSB, 1 for the first BSB.
    """
    return omega * np.array(list(map(rabi_rate_fast, [1, 1, 1], etas, ns, alphas)))