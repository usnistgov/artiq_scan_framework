from artiq.experiment import *
from .exceptions import Paused
import time
from .scans.scan import FitGuess


# for debugging purposes
def print_caller():
    import inspect
    frm = inspect.stack()[2]
    mod = inspect.getmodule(frm[0])
    print('Caller: {1}.{0}'.format(frm[3], mod.__name__))


@kernel
def trig_timestamp(ttl, rate):
    ttl.gate_rising(rate)
    _ = now_mu()
    mu_trig = now_mu()
    while _ > 0:
        mu_trig = _
        _ = ttl.timestamp_mu()
    return mu_trig


def pause(self):
    try:
        self.core.comm.close()
        self.scheduler.pause()
        return True
    except TerminationRequested:
        return False


@portable
def check_pause(self):
    if self.scheduler.check_pause():
        raise Paused


def wait_for_action(self):
    """Block the caller until the user performs some action and manually sets the 'wait' dataset to 0"""
    self.set_dataset('wait', 1, broadcast=True, save=True, persist=True)
    time.sleep(2)
    while self.get_dataset('wait', archive=False) == 1:
        time.sleep(1)


def setattr_argument(self, key, processor=None, group=None, show='auto'):
    if show is 'auto' and hasattr(self, key) and getattr(self, key) is not None:
        return
    self.setattr_argument(key, processor, group)
    # set attribute to default value when class is built but not submitted
    if hasattr(processor, 'default_value'):
        if not hasattr(self, key) or getattr(self, key) is None:
            setattr(self, key, processor.default_value)


def scan_arguments(self, npasses={}, nrepeats={}, nbins={}, fit_options={}, guesses=False):
    # assign default values for scan GUI arguments
    if npasses is not False:
        for k,v in {'default': 1, 'ndecimals': 0, 'step': 1}.items():
            npasses.setdefault(k, v)
    if nrepeats is not False:
        for k,v in {'default': 100, 'ndecimals': 0, 'step': 1}.items():
            nrepeats.setdefault(k, v)
    if nbins is not False:
        for k,v in {'default': 50, 'ndecimals': 0, 'step': 1}.items():
            nbins.setdefault(k, v)
    if fit_options is not False:
        for k,v in {'values': ['No Fits','Fit',"Fit and Save","Fit Only","Fit Only and Save"], 'default': 'Fit'}.items():
            fit_options.setdefault(k, v)

    if npasses is not False:
        setattr_argument(self, 'npasses', NumberValue(**npasses), group='Scan Settings')
    if nrepeats is not False:
        setattr_argument(self, 'nrepeats', NumberValue(**nrepeats), group='Scan Settings')
    if nbins is not False:
        setattr_argument(self, 'nbins', NumberValue(**nbins), group='Scan Settings')

    if fit_options is not False:
        fovals = fit_options.pop('values')
        setattr_argument(self, 'fit_options', EnumerationValue(fovals, **fit_options), group='Fit Settings')
        if guesses:
             if guesses is True:
                 for i in range(1, 6):
                     key = 'fit_guess_{0}'.format(i)
                     setattr_argument(self, key,
                                           FitGuess(default=1.0,
                                                    use_default=False,
                                                    ndecimals=6,
                                                    step=0.001,
                                                    fit_param=None,
                                                    param_index=i))
             else:
                 for fit_param in guesses:
                    key = 'fit_guess_{0}'.format(fit_param)
                    setattr_argument(self, key,
                                          FitGuess(default=1.0,
                                                   use_default=True,
                                                   ndecimals=1,
                                                   step=0.001,
                                                   fit_param=fit_param,
                                                   param_index=None))
