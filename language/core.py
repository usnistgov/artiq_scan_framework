from artiq.language.core import *
from .exceptions import Paused


def pause(self):
    try:
        self.core.comm.close()
        self.scheduler.pause()
        return True
    except TerminationRequested:
        return False


@portable
def check_pause(obj):
    # cost: 3.6 ms
    if obj.scheduler.check_pause():
        # yield
        raise Paused


@kernel
def trig_timestamp(ttl, rate):
    ttl.gate_rising(rate)
    _ = now_mu()
    mu_trig = now_mu()
    while _ > 0:
        mu_trig = _
        _ = ttl.timestamp_mu()
    return mu_trig