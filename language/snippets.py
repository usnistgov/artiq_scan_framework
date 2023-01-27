from artiq.experiment import *
from .exceptions import Paused
import time
import numpy as np




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


def wait_for_action(self):
    """Block the caller until the user performs some action and manually sets the 'wait' dataset to 0"""
    self.set_dataset('wait', 1, broadcast=True, save=True, persist=True)
    time.sleep(2)
    while self.get_dataset('wait', archive=False) == 1:
        time.sleep(1)


def setattr_argument(self, key, processor=None, group=None, show='auto', tooltip=None):
    if show is 'auto' and hasattr(self, key) and getattr(self, key) is not None:
        return
    self.setattr_argument(key, processor, group, tooltip=tooltip)
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


@portable
def check_pause(obj):
    # cost: 3.6 ms
    if obj.scheduler.check_pause():
        # yield
        raise Paused


def get_registered_models(scan, **kwargs):
    entries = []
    for entry in scan._model_registry:
        append = True
        for k, v in kwargs.items():
            if k in entry:
                if isinstance(v, bool) and v:
                    pass
                elif isinstance(v, list):
                    if entry[k] not in v:
                        append = False
                        break
                elif entry[k] != v:
                    append = False
                    break
        if append:
            entries.append(entry)
    return entries


def get_scan_points(scan):
    if scan.scan_points is None:
        return scan.get_scan_points()
    else:
        return scan.scan_points
    return points


def get_warmup_points(scan):
    if scan.warmup_points is None:
        return scan.get_warmup_points()
    else:
        return scan.warmup_points


def load_warmup_points(obj):
    warmup_points = get_warmup_points(obj.scan)
    warmup_points = [p for p in warmup_points]
    warmup_points = np.array(warmup_points, dtype=np.float64)
    obj.warmup_points = warmup_points


def trigger_plot(model):
    model.set('plots.trigger', 1, which='mirror')
    model.set('plots.trigger', 0, which='mirror')


def mutate_plot(model, i_point, x, y, error):
    return model.mutate_plot(i_point=i_point, x=x, y=y, error=error)


def mutate_stats(model, i_point, i_pass, poffset, meas_point, data):
    mean, error = model.mutate_datasets(i_point=i_point, i_pass=i_pass, poffset=poffset, point=meas_point, counts=data)
    return mean, error


def mutate_datasets_calc(model, i_point, i_pass, meas_point, calculation):
    calced_value = model.mutate_datasets_calc(i_point=i_point, i_pass=i_pass, point=meas_point, calculation=calculation)
    return calced_value


def get_fit_data(model, use_mirror):
    x_data, y_data = model.get_fit_data(use_mirror)
    errors = get_errors(model, use_mirror)
    return x_data, y_data, errors


def get_errors(model, use_mirror):
    errors = model.get('stats.error', mirror=use_mirror)
    return errors




